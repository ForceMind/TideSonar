# TideSonar Runtime Tuning Guide

This document explains the runtime polling profiles, request rate limiting, and weighted ranking logic added in the latest backend/frontend update.

## 1. Current Default Runtime Config

The producer starts with `profile=balanced` by default.

```json
{
  "profile": "balanced",
  "hot_per_index": 10,
  "warm_per_index": 30,
  "hot_interval_seconds": 1.0,
  "warm_interval_seconds": 10.0,
  "cold_interval_seconds": 60.0,
  "alert_ttl_seconds": 120.0,
  "loop_sleep_seconds": 0.5,
  "max_requests_per_minute": 2400,
  "pct_weight": 0.55,
  "volume_weight": 0.18
}
```

## 2. Rate Limit Implementation

Rate limiting is now enforced by a hard rolling-window limiter in `backend/app/services/biying_source.py`.

- A thread-safe `RollingRateLimiter` gates every batch API request.
- Default request cap is `2400 req/min`.
- Provider hard cap is enforced at `3000 req/min` even if a higher value is configured.

Runtime update support:

- `BiyingDataSource.update_rate_limit(max_requests_per_minute)` updates cap immediately.
- This is used when switching runtime profiles.

## 3. Tiered Polling Strategy

Instead of full-market polling every cycle, the producer uses Hot/Warm/Cold tiers:

- `Hot`: top N symbols per index, fast refresh.
- `Warm`: next symbols per index, medium refresh.
- `Cold`: remaining universe, slow refresh.

Built-in profiles:

- `conservative`
- `balanced`
- `aggressive`

Selection tiers and final ranking are computed per index (`HS300`, `ZZ500`, `ZZ1000`, `ZZ2000`).

## 4. Runtime APIs

New API routes:

- `GET /api/runtime/polling-profiles`
- `GET /api/runtime/polling-config`
- `POST /api/runtime/polling-profile/{profile}`

Examples:

```bash
curl http://localhost:8000/api/runtime/polling-profiles
curl http://localhost:8000/api/runtime/polling-config
curl -X POST http://localhost:8000/api/runtime/polling-profile/aggressive
```

## 5. Frontend Profile Switch

In the Heat modal (`frontend/src/App.vue`), a new profile selector is added:

- Conservative
- Balanced
- Aggressive

The selected profile updates backend polling behavior at runtime (no restart required).

## 6. Weighted Ranking (Backend + Frontend)

Ranking is no longer pure `amount` sorting.

Both backend producer and frontend list sorting now use weighted score:

```text
score = amount * max(0.1, 1 + pct_weight * pct_factor + volume_weight * volume_factor)
```

Where:

- `pct_factor = clamp(pct_chg / 10, -0.5, 2.0)`
- `volume_factor = clamp(volume_ratio - 1.0, 0.0, 3.0)`

Momentum bonuses:

- `pct_chg >= 8.5`: `x1.6`
- `pct_chg >= 5.0`: `x1.25`
- `pct_chg <= -3.0`: `x0.8`

This pushes strong gainers forward while preserving amount as the base signal.

## 7. Environment Variables

You can override defaults with env vars:

- `POLLING_PROFILE` (`balanced` by default)
- `HOT_PER_INDEX`
- `WARM_PER_INDEX`
- `HOT_INTERVAL_SECONDS`
- `WARM_INTERVAL_SECONDS`
- `COLD_INTERVAL_SECONDS`
- `ALERT_TTL_SECONDS`
- `PRODUCER_LOOP_SLEEP_SECONDS`
- `BIYING_MAX_REQUESTS_PER_MINUTE`
- `SORT_PCT_WEIGHT`
- `SORT_VOLUME_WEIGHT`

Notes:

- Runtime profile switch applies immediately.
- Env var changes still require process restart.
