import redis
import json
import pandas as pd
import numpy as np
from typing import List
from backend.app.models.stock import StockData, StockAlert
from backend.app.core.config import settings

class MarketMonitor:
    def __init__(self):
        # Redis connection
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            self.redis_client.ping() # Check connection immediately
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}. Running in standalone mode.")
            self.redis_client = None

        # Cache for historical averages
        # Key: Stock Code, Value: Baseline Volume (e.g. 5-day average for current minute)
        self.baseline_volumes = {} 
        self._load_history_data()

    def _load_history_data(self):
        """
        Load historical minute-K baseline data from disk.
        Format: JSON { "000001": 150000, "600000": 2000000, ... }
        """
        import os
        import json
        
        # Try to load 'history_baseline.json' from root or config path
        # In a real system, this would query InfluxDB or a Data Service
        history_path = os.getenv("HISTORY_DATA_PATH", "history_baseline.json")
        
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    self.baseline_volumes = json.load(f)
                print(f"[Monitor] Loaded historical baseline for {len(self.baseline_volumes)} stocks.")
            except Exception as e:
                print(f"[Monitor] Failed to load history data: {e}")
        else:
            print("[Monitor] No history data found. Volume Ratio will default to 1.0 (Safe Mode).")

    def _get_baseline_volume(self, code: str) -> float:
        """
        Get the baseline volume for the current minute from history.
        """
        # 1. Try loaded history
        if code in self.baseline_volumes:
            return self.baseline_volumes[code]
            
        # 2. Fallback: Return -1 to indicate "Data Missing"
        # We DO NOT simulate random data anymore per user request.
        return -1.0

    def detect_anomalies(self, snapshot: List[StockData]) -> List[StockAlert]:
        alerts = []
        
        target_indices = {"HS300", "ZZ500", "ZZ1000", "ZZ2000"}
        
        for stock in snapshot:
            # 1. Filter Index
            if stock.index_code not in target_indices:
                continue

            # 2. Dynamic Filtering Logic based on Index
            min_amount = 20_000_000 # Default for HS300/ZZ500
            if stock.index_code == "ZZ1000":
                min_amount = 10_000_000
            elif stock.index_code == "ZZ2000":
                min_amount = 3_000_000 # Much lower for microcaps

            if stock.amount <= min_amount:
                continue
                
            # Condition C: Significant Move
            # V5 Update: User wants "Top Amount" stability. 
            # We REMOVE the price fluctuation filter (abs(pct_chg) > 1.0).
            # Why? Because a stock with huge amount but 0% change (battleground) is still important.
            # Filtering by 1% causes stocks to flicker in/out of the Top 30 list.
            # if abs(stock.pct_chg) <= 1.0: 
            #    continue

            # Condition A: Volume Ratio (Simplified)
            # Since we don't have real minute-level baseline, we'll just check if volume is decent
            if stock.volume < 100:
                continue

            # Condition A: Volume Ratio
            # Logic: volume_ratio = volume / baseline
            baseline = self._get_baseline_volume(stock.code)
            
            if baseline > 0:
                volume_ratio = stock.volume / baseline
            else:
                # If no history, we cannot calculate Volume Ratio.
                # Default to 1.0 (Neutral) so it doesn't affect sorting negatively,
                # or 0.0 if we want to penalize unknown stocks.
                # Given we prioritize Amount, 1.0 is safer to avoid burying new valid stocks.
                volume_ratio = 1.0

            # HIT!
            alert = StockAlert(
                code=stock.code,
                name=stock.name,
                price=stock.price,
                pct_chg=stock.pct_chg,
                amount=stock.amount,
                volume_ratio=round(volume_ratio, 2),
                index_code=stock.index_code,
                industry=stock.industry,
                concept=stock.concept,
                timestamp=stock.timestamp.isoformat(),
                reason=f"量比:{volume_ratio:.1f}|金额:{stock.amount/10000:.0f}万|涨幅:{stock.pct_chg}%"
            )
            alerts.append(alert)
            self._publish_alert(alert)

        return alerts

    def _publish_alert(self, alert: StockAlert):
        if self.redis_client:
            # Publish to Redis
            try:
                self.redis_client.publish(settings.REDIS_CHANNEL, alert.model_dump_json())
            except Exception as e:
                print(f"Redis Publish Error: {e}")
        else:
            # Fallback print if no Redis
            # print(f"Redis Unavailable. Alert: {alert.model_dump_json()}")
            pass
