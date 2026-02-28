import asyncio
import logging
import os
import threading
import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple, TypedDict

from backend.app.models.stock import StockAlert
from backend.app.services.biying_source import BiyingDataSource
from backend.app.services.market_schedule import MarketSchedule
from backend.app.services.monitor import MarketMonitor
from backend.app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

INDEX_ORDER = ("HS300", "ZZ500", "ZZ1000", "ZZ2000")
MAX_ITEMS_PER_INDEX = 30


class RuntimePolicy(TypedDict):
    hot_per_index: int
    warm_per_index: int
    hot_interval_seconds: float
    warm_interval_seconds: float
    cold_interval_seconds: float
    alert_ttl_seconds: float
    loop_sleep_seconds: float
    max_requests_per_minute: int
    pct_weight: float
    volume_weight: float


DEFAULT_POLICY: RuntimePolicy = {
    "hot_per_index": int(os.getenv("HOT_PER_INDEX", "10")),
    "warm_per_index": int(os.getenv("WARM_PER_INDEX", "30")),
    "hot_interval_seconds": float(os.getenv("HOT_INTERVAL_SECONDS", "1.0")),
    "warm_interval_seconds": float(os.getenv("WARM_INTERVAL_SECONDS", "10.0")),
    "cold_interval_seconds": float(os.getenv("COLD_INTERVAL_SECONDS", "60.0")),
    "alert_ttl_seconds": float(os.getenv("ALERT_TTL_SECONDS", "120.0")),
    "loop_sleep_seconds": float(os.getenv("PRODUCER_LOOP_SLEEP_SECONDS", "0.5")),
    "max_requests_per_minute": int(os.getenv("BIYING_MAX_REQUESTS_PER_MINUTE", "2400")),
    "pct_weight": float(os.getenv("SORT_PCT_WEIGHT", "0.55")),
    "volume_weight": float(os.getenv("SORT_VOLUME_WEIGHT", "0.18")),
}

PROFILE_PRESETS: Dict[str, RuntimePolicy] = {
    "conservative": {
        **DEFAULT_POLICY,
        "hot_per_index": 8,
        "warm_per_index": 24,
        "hot_interval_seconds": 1.2,
        "warm_interval_seconds": 12.0,
        "cold_interval_seconds": 60.0,
        "max_requests_per_minute": 1800,
        "pct_weight": 0.45,
        "volume_weight": 0.15,
    },
    "balanced": {
        **DEFAULT_POLICY,
        "hot_per_index": 10,
        "warm_per_index": 30,
        "hot_interval_seconds": 1.0,
        "warm_interval_seconds": 10.0,
        "cold_interval_seconds": 60.0,
        "max_requests_per_minute": 2400,
        "pct_weight": 0.55,
        "volume_weight": 0.18,
    },
    "aggressive": {
        **DEFAULT_POLICY,
        "hot_per_index": 12,
        "warm_per_index": 40,
        "hot_interval_seconds": 0.8,
        "warm_interval_seconds": 6.0,
        "cold_interval_seconds": 45.0,
        "max_requests_per_minute": 2700,
        "pct_weight": 0.72,
        "volume_weight": 0.22,
    },
}

_profile_env = os.getenv("POLLING_PROFILE", "balanced").lower()
_runtime_profile = _profile_env if _profile_env in PROFILE_PRESETS else "balanced"
_runtime_policy: RuntimePolicy = {**PROFILE_PRESETS[_runtime_profile]}
_runtime_lock = threading.Lock()


def get_available_profiles() -> List[Dict[str, str]]:
    return [
        {"key": "conservative", "label": "Conservative"},
        {"key": "balanced", "label": "Balanced"},
        {"key": "aggressive", "label": "Aggressive"},
    ]


def get_runtime_policy() -> Dict[str, float | int | str]:
    with _runtime_lock:
        return {"profile": _runtime_profile, **_runtime_policy}


def set_runtime_profile(profile: str) -> Dict[str, float | int | str]:
    normalized = (profile or "").strip().lower()
    if normalized not in PROFILE_PRESETS:
        raise ValueError(f"Unknown profile: {profile}")

    with _runtime_lock:
        global _runtime_profile, _runtime_policy
        _runtime_profile = normalized
        _runtime_policy = {**PROFILE_PRESETS[normalized]}

    logger.info("Runtime polling profile switched to: %s", normalized)
    return get_runtime_policy()


def _calculate_score(stock: StockAlert, policy: Dict[str, float | int | str]) -> float:
    base_amount = max(0.0, float(stock.amount))
    pct_weight = float(policy["pct_weight"])
    volume_weight = float(policy["volume_weight"])

    pct_factor = max(-0.5, min(float(stock.pct_chg) / 10.0, 2.0))
    volume_factor = max(0.0, min(float(stock.volume_ratio) - 1.0, 3.0))

    score = base_amount * max(0.1, 1.0 + pct_weight * pct_factor + volume_weight * volume_factor)

    # Momentum bonus: explicitly push strong gainers forward.
    if stock.pct_chg >= 8.5:
        score *= 1.6
    elif stock.pct_chg >= 5.0:
        score *= 1.25
    elif stock.pct_chg <= -3.0:
        score *= 0.8

    return score


def _build_final_selection(alert_cache: Dict[str, StockAlert], policy: Dict[str, float | int | str]) -> List[StockAlert]:
    grouped: Dict[str, List[StockAlert]] = {k: [] for k in INDEX_ORDER}
    for alert in alert_cache.values():
        if alert.index_code in grouped and alert.amount > 0:
            grouped[alert.index_code].append(alert)

    final_selection: List[StockAlert] = []
    for index_code in INDEX_ORDER:
        ranked = sorted(grouped[index_code], key=lambda x: _calculate_score(x, policy), reverse=True)
        final_selection.extend(ranked[:MAX_ITEMS_PER_INDEX])
    return final_selection


def _select_hot_warm_codes(
    alert_cache: Dict[str, StockAlert],
    policy: Dict[str, float | int | str],
) -> Tuple[Set[str], Set[str]]:
    grouped: Dict[str, List[StockAlert]] = {k: [] for k in INDEX_ORDER}
    for alert in alert_cache.values():
        if alert.index_code in grouped:
            grouped[alert.index_code].append(alert)

    hot_codes: Set[str] = set()
    warm_codes: Set[str] = set()

    hot_per_index = int(policy["hot_per_index"])
    warm_per_index = int(policy["warm_per_index"])
    warm_limit = max(hot_per_index, warm_per_index)

    for index_code in INDEX_ORDER:
        ranked = sorted(grouped[index_code], key=lambda x: _calculate_score(x, policy), reverse=True)
        hot_slice = ranked[:hot_per_index]
        warm_slice = ranked[hot_per_index:warm_limit]
        hot_codes.update(a.code for a in hot_slice)
        warm_codes.update(a.code for a in warm_slice)

    return hot_codes, warm_codes


async def _broadcast_selection(selection: List[StockAlert]) -> None:
    snapshot_json_list = [alert.model_dump_json() for alert in selection]
    manager.update_snapshot(snapshot_json_list)
    for payload in snapshot_json_list:
        try:
            await manager.broadcast(payload)
        except Exception as exc:
            logger.error("Broadcast error: %s", exc)


async def run_mock_producer():
    """
    Background task:
    - Uses tiered refresh during trading hours.
    - Keeps hard request limiting inside data source.
    - Keeps one-off post-close refresh behavior.
    """
    logger.info("Starting Data Producer Task...")
    logger.info("Using REAL DATA SOURCE (BiyingAPI)")

    source = BiyingDataSource()
    monitor = MarketMonitor()

    all_codes = source.get_all_codes()
    all_codes_set = set(all_codes)
    if not all_codes_set:
        logger.error("No stocks loaded from data source, producer will idle.")

    policy = get_runtime_policy()
    source.update_rate_limit(int(policy["max_requests_per_minute"]))

    logger.info(
        "Adaptive polling config: profile=%s hot=%ss warm=%ss cold=%ss hot_top=%s warm_top=%s universe=%s",
        policy["profile"],
        policy["hot_interval_seconds"],
        policy["warm_interval_seconds"],
        policy["cold_interval_seconds"],
        policy["hot_per_index"],
        policy["warm_per_index"],
        len(all_codes_set),
    )

    alert_cache: Dict[str, StockAlert] = {}
    alert_last_seen: Dict[str, float] = {}

    next_hot_fetch = 0.0
    next_warm_fetch = 0.0
    next_cold_fetch = 0.0
    loop_count = 0

    try:
        while True:
            loop_count += 1
            policy = get_runtime_policy()

            max_rpm = int(policy["max_requests_per_minute"])
            if source.max_requests_per_minute != max_rpm:
                source.update_rate_limit(max_rpm)

            hot_interval_seconds = float(policy["hot_interval_seconds"])
            warm_interval_seconds = float(policy["warm_interval_seconds"])
            cold_interval_seconds = float(policy["cold_interval_seconds"])
            alert_ttl_seconds = float(policy["alert_ttl_seconds"])
            loop_sleep_seconds = float(policy["loop_sleep_seconds"])

            # No active client and already has cache, keep backend lightweight.
            if len(manager.active_connections) == 0 and manager.has_data():
                await asyncio.sleep(2)
                continue

            market_open = MarketSchedule.is_market_open()

            if not market_open:
                if manager.has_data() and not manager.is_data_stale():
                    logger.info("Market closed (fresh cache). Sleeping 60s...")
                    await asyncio.sleep(60)
                    continue
                due_codes = list(all_codes_set)
            else:
                now_mono = time.monotonic()
                hot_codes, warm_codes = _select_hot_warm_codes(alert_cache, policy)
                cold_codes = all_codes_set - hot_codes - warm_codes
                due_set: Set[str] = set()

                if hot_codes and now_mono >= next_hot_fetch:
                    due_set.update(hot_codes)
                    next_hot_fetch = now_mono + hot_interval_seconds

                if warm_codes and now_mono >= next_warm_fetch:
                    due_set.update(warm_codes)
                    next_warm_fetch = now_mono + warm_interval_seconds

                if now_mono >= next_cold_fetch:
                    due_set.update(cold_codes if cold_codes else all_codes_set)
                    next_cold_fetch = now_mono + cold_interval_seconds

                if not due_set:
                    await asyncio.sleep(loop_sleep_seconds)
                    continue

                due_codes = list(due_set)

                if loop_count % 30 == 0:
                    logger.info(
                        "Adaptive cycle: profile=%s fetch=%s hot=%s warm=%s cold=%s cache=%s",
                        policy["profile"],
                        len(due_codes),
                        len(hot_codes),
                        len(warm_codes),
                        len(cold_codes),
                        len(alert_cache),
                    )

            try:
                snapshot = await asyncio.to_thread(source.get_snapshot_for_codes, due_codes)
            except Exception as exc:
                logger.error("Snapshot fetch error: %s", exc)
                snapshot = []

            updated_codes = {item.code for item in snapshot}

            try:
                alerts = await asyncio.to_thread(monitor.detect_anomalies, snapshot)
            except Exception as exc:
                logger.error("Monitor error: %s", exc)
                alerts = []

            now_mono = time.monotonic()
            fresh_alert_map = {alert.code: alert for alert in alerts}

            # Updated code leaves cache immediately if it no longer matches filters.
            for code in updated_codes:
                fresh_alert = fresh_alert_map.get(code)
                if fresh_alert:
                    alert_cache[code] = fresh_alert
                    alert_last_seen[code] = now_mono
                else:
                    alert_cache.pop(code, None)
                    alert_last_seen.pop(code, None)

            # Defensive cleanup for stale alerts that stop being updated.
            stale_codes = [
                code
                for code, seen_at in alert_last_seen.items()
                if (now_mono - seen_at) > alert_ttl_seconds
            ]
            for code in stale_codes:
                alert_cache.pop(code, None)
                alert_last_seen.pop(code, None)

            final_selection = _build_final_selection(alert_cache, policy)
            if final_selection:
                await _broadcast_selection(final_selection)
                if loop_count % 30 == 0:
                    sent_counts = defaultdict(int)
                    for alert in final_selection:
                        sent_counts[alert.index_code] += 1
                    logger.info("Sent %s alerts. Dist=%s", len(final_selection), dict(sent_counts))
            elif not market_open:
                # Closed-market fallback: keep empty snapshot explicit if no valid alerts.
                manager.update_snapshot([])

            if not market_open:
                logger.info("Market closed one-off fetch complete. Sleeping 60s...")
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(loop_sleep_seconds)

    except asyncio.CancelledError:
        logger.info("Data Producer Task Cancelled.")
    except Exception as exc:
        logger.error("Error in Producer: %s", exc)
