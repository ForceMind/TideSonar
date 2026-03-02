import asyncio
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, time as dt_time
from typing import Dict, List, Set, Tuple, TypedDict

from backend.app.models.stock import StockAlert, StockData
from backend.app.services.biying_source import BiyingDataSource
from backend.app.services.market_schedule import MarketSchedule
from backend.app.services.monitor import MarketMonitor
from backend.app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

INDEX_ORDER = ("HS300", "ZZ500", "ZZ1000", "ZZ2000")
MAX_ITEMS_PER_INDEX = 30
AUTO_PROFILE_SWITCH = os.getenv("AUTO_PROFILE_SWITCH", "true").lower() == "true"
OPENING_AGGRESSIVE_START = dt_time(9, 30)
OPENING_AGGRESSIVE_END = dt_time(10, 0)
SNAPSHOT_CACHE_TTL_SECONDS = float(os.getenv("SNAPSHOT_CACHE_TTL_SECONDS", "90.0"))


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


class PulseMetrics(TypedDict):
    sample_size: int
    total_amount: float
    limit_up_count: int
    strong_up_count: int
    explosive_up_count: int


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
_runtime_last_reason = "init"
_runtime_last_switch_time = datetime.now().isoformat(timespec="seconds")


class MarketRegimeController:
    """State machine for automatic profile switching."""

    def __init__(self):
        self.ema_turnover: float | None = None
        self.calm_counter = 0
        self.very_calm_counter = 0
        self.aggressive_hold_until = 0.0
        self.last_metrics: PulseMetrics = {
            "sample_size": 0,
            "total_amount": 0.0,
            "limit_up_count": 0,
            "strong_up_count": 0,
            "explosive_up_count": 0,
        }

    @staticmethod
    def _compute_metrics(snapshot: List[StockData]) -> PulseMetrics:
        if not snapshot:
            return {
                "sample_size": 0,
                "total_amount": 0.0,
                "limit_up_count": 0,
                "strong_up_count": 0,
                "explosive_up_count": 0,
            }

        total_amount = 0.0
        limit_up_count = 0
        strong_up_count = 0
        explosive_up_count = 0

        for item in snapshot:
            pct = float(item.pct_chg)
            amt = max(0.0, float(item.amount))
            total_amount += amt

            if pct >= 9.5:
                limit_up_count += 1
            if pct >= 5.0:
                strong_up_count += 1
            if pct >= 7.0:
                explosive_up_count += 1

        return {
            "sample_size": len(snapshot),
            "total_amount": total_amount,
            "limit_up_count": limit_up_count,
            "strong_up_count": strong_up_count,
            "explosive_up_count": explosive_up_count,
        }

    def decide(self, snapshot: List[StockData], current_profile: str) -> Tuple[str, str]:
        metrics = self._compute_metrics(snapshot)
        self.last_metrics = metrics

        sample_size = metrics["sample_size"]
        if sample_size < 30:
            return current_profile, "insufficient_sample"

        total_amount = metrics["total_amount"]

        if self.ema_turnover is None:
            self.ema_turnover = total_amount
        else:
            alpha = 0.18
            self.ema_turnover = alpha * total_amount + (1 - alpha) * self.ema_turnover

        ema_turnover = max(1.0, self.ema_turnover)

        limit_up_trigger = max(6, int(sample_size * 0.007))
        strong_up_trigger = max(24, int(sample_size * 0.03))
        explosive_trigger = max(10, int(sample_size * 0.015))

        turnover_surge = total_amount >= max(2e8, ema_turnover * 1.55)

        surge = (
            metrics["limit_up_count"] >= limit_up_trigger
            or metrics["strong_up_count"] >= strong_up_trigger
            or metrics["explosive_up_count"] >= explosive_trigger
            or turnover_surge
        )

        calm_limit_up = max(2, int(sample_size * 0.0025))
        calm_strong_up = max(9, int(sample_size * 0.012))
        calm = (
            metrics["limit_up_count"] <= calm_limit_up
            and metrics["strong_up_count"] <= calm_strong_up
            and total_amount <= ema_turnover * 1.08
        )

        very_calm_limit_up = max(1, int(sample_size * 0.0015))
        very_calm_strong_up = max(5, int(sample_size * 0.008))
        very_calm = (
            metrics["limit_up_count"] <= very_calm_limit_up
            and metrics["strong_up_count"] <= very_calm_strong_up
            and total_amount <= ema_turnover * 0.95
        )

        now_mono = time.monotonic()

        if surge:
            self.calm_counter = 0
            self.very_calm_counter = 0
            self.aggressive_hold_until = now_mono + 120.0
            return "aggressive", (
                f"surge lu={metrics['limit_up_count']} su={metrics['strong_up_count']} "
                f"ex={metrics['explosive_up_count']} amt={total_amount:.0f}"
            )

        if now_mono < self.aggressive_hold_until:
            return "aggressive", "surge_cooldown"

        if calm:
            self.calm_counter += 1
        else:
            self.calm_counter = 0

        if very_calm:
            self.very_calm_counter += 1
        else:
            self.very_calm_counter = 0

        rebound = (
            metrics["strong_up_count"] >= max(12, int(sample_size * 0.018))
            or total_amount >= ema_turnover * 1.18
        )

        if current_profile == "aggressive" and self.calm_counter >= 4:
            return "balanced", "calm_4_cycles"

        if current_profile == "balanced" and self.very_calm_counter >= 8:
            return "conservative", "very_calm_8_cycles"

        if current_profile == "conservative" and rebound:
            return "balanced", "activity_rebound"

        return current_profile, "no_change"


def get_available_profiles() -> List[Dict[str, str]]:
    return [
        {"key": "conservative", "label": "Conservative"},
        {"key": "balanced", "label": "Balanced"},
        {"key": "aggressive", "label": "Aggressive"},
    ]


def get_runtime_policy() -> Dict[str, float | int | str | bool]:
    with _runtime_lock:
        return {
            "profile": _runtime_profile,
            "auto_profile_switch": AUTO_PROFILE_SWITCH,
            "last_switch_reason": _runtime_last_reason,
            "last_switch_time": _runtime_last_switch_time,
            **_runtime_policy,
        }


def set_runtime_profile(profile: str, reason: str = "manual") -> Dict[str, float | int | str | bool]:
    normalized = (profile or "").strip().lower()
    if normalized not in PROFILE_PRESETS:
        raise ValueError(f"Unknown profile: {profile}")

    with _runtime_lock:
        global _runtime_profile, _runtime_policy, _runtime_last_reason, _runtime_last_switch_time
        if normalized == _runtime_profile:
            return {
                "profile": _runtime_profile,
                "auto_profile_switch": AUTO_PROFILE_SWITCH,
                "last_switch_reason": _runtime_last_reason,
                "last_switch_time": _runtime_last_switch_time,
                **_runtime_policy,
            }

        _runtime_profile = normalized
        _runtime_policy = {**PROFILE_PRESETS[normalized]}
        _runtime_last_reason = reason
        _runtime_last_switch_time = datetime.now().isoformat(timespec="seconds")

    logger.info("Runtime polling profile switched to: %s (reason=%s)", normalized, reason)
    return get_runtime_policy()


def _calculate_score(stock: StockAlert, policy: Dict[str, float | int | str | bool]) -> float:
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


def _build_final_selection(
    alert_cache: Dict[str, StockAlert],
    policy: Dict[str, float | int | str | bool],
) -> List[StockAlert]:
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
    policy: Dict[str, float | int | str | bool],
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
    - Supports optional automatic profile switching.
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
        "Adaptive polling config: profile=%s hot=%ss warm=%ss cold=%ss hot_top=%s warm_top=%s universe=%s auto=%s",
        policy["profile"],
        policy["hot_interval_seconds"],
        policy["warm_interval_seconds"],
        policy["cold_interval_seconds"],
        policy["hot_per_index"],
        policy["warm_per_index"],
        len(all_codes_set),
        AUTO_PROFILE_SWITCH,
    )

    alert_cache: Dict[str, StockAlert] = {}
    alert_last_seen: Dict[str, float] = {}

    # Cache recent market snapshots to avoid profile decisions on tiny samples.
    market_snapshot_cache: Dict[str, StockData] = {}
    market_snapshot_seen: Dict[str, float] = {}

    regime_controller = MarketRegimeController()

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

            now_mono = time.monotonic()

            # Update market snapshot cache for profile auto-switch decisions.
            for stock in snapshot:
                market_snapshot_cache[stock.code] = stock
                market_snapshot_seen[stock.code] = now_mono

            stale_market_codes = [
                code
                for code, seen_at in market_snapshot_seen.items()
                if (now_mono - seen_at) > SNAPSHOT_CACHE_TTL_SECONDS
            ]
            for code in stale_market_codes:
                market_snapshot_cache.pop(code, None)
                market_snapshot_seen.pop(code, None)

            market_view = list(market_snapshot_cache.values())

            if AUTO_PROFILE_SWITCH and market_open:
                now_dt = datetime.now()
                current_profile = str(policy["profile"])

                if OPENING_AGGRESSIVE_START <= now_dt.time() < OPENING_AGGRESSIVE_END:
                    target_profile = "aggressive"
                    switch_reason = "auto:opening_window_0930_1000"
                else:
                    target_profile, reason = regime_controller.decide(market_view, current_profile)
                    switch_reason = f"auto:{reason}"

                if target_profile != current_profile:
                    policy = set_runtime_profile(target_profile, reason=switch_reason)
                    source.update_rate_limit(int(policy["max_requests_per_minute"]))

                if loop_count % 30 == 0 and regime_controller.last_metrics["sample_size"] > 0:
                    m = regime_controller.last_metrics
                    logger.info(
                        "Market pulse sample=%s lu=%s su=%s ex=%s amount=%.0f profile=%s",
                        m["sample_size"],
                        m["limit_up_count"],
                        m["strong_up_count"],
                        m["explosive_up_count"],
                        m["total_amount"],
                        policy["profile"],
                    )

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
