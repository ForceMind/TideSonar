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
        history_path = os.getenv("HISTORY_DATA_PATH", "history_baseline.json")
        
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    self.baseline_volumes = json.load(f)
                print(f"[Monitor] Loaded historical baseline for {len(self.baseline_volumes)} stocks.")
                # Debug: Print first 3 keys to verify format
                sample_keys = list(self.baseline_volumes.keys())[:3]
                print(f"[Monitor] Sample Keys: {sample_keys}")
            except Exception as e:
                print(f"[Monitor] Failed to load history data: {e}")
        else:
            print(f"[Monitor] No history data found at {os.path.abspath(history_path)}. Volume Ratio will default to 1.0.")

    def _get_trading_minutes(self, dt: pd.Timestamp) -> int:
        """
        Calculate trading minutes elapsed since 9:30 today.
        Trading Hours: 9:30-11:30 (120m), 13:00-15:00 (120m).
        """
        # Parse simple hours
        # Normalize to today's date to avoid date diff issues
        t = dt.time()
        
        start_am = pd.Timestamp("09:30").time()
        end_am = pd.Timestamp("11:30").time()
        start_pm = pd.Timestamp("13:00").time()
        end_pm = pd.Timestamp("15:00").time()
        
        minutes = 0
        
        # Simple Logic: Convert to minutes from midnight
        current_min = t.hour * 60 + t.minute
        
        # AM Session
        am_start_min = 9 * 60 + 30
        am_end_min = 11 * 60 + 30
        
        # PM Session
        pm_start_min = 13 * 60
        pm_end_min = 15 * 60
        
        if current_min < am_start_min:
            return 1 # Just open
            
        if current_min <= am_end_min:
            return current_min - am_start_min
            
        if current_min < pm_start_min:
            return 120 # Lunch break (frozen at 120)
            
        if current_min <= pm_end_min:
            return 120 + (current_min - pm_start_min)
            
        return 240 # Closed

    def detect_anomalies(self, snapshot: List[StockData]) -> List[StockAlert]:
        alerts = []
        
        target_indices = {"HS300", "ZZ500", "ZZ1000", "ZZ2000"}
        
        # Get minutes elapsed for WR calculation
        # Use simple current time or timestamp from first stock
        if snapshot:
            ref_time = snapshot[0].timestamp
            minutes_elapsed = self._get_trading_minutes(ref_time)
            # Avoid division by zero
            minutes_elapsed = max(1, minutes_elapsed)
        else:
            minutes_elapsed = 240
            
        # Debug Log once per cycle
        # print(f"[Monitor] Calculation Cycle. Minutes Elapsed: {minutes_elapsed}")
        
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

            # Condition A: Volume Ratio (Check Raw Volume first)
            if stock.volume < 100:
                continue

            # Condition A: Volume Ratio Calculation
            # Formula: (Current Vol / Minutes) / (Baseline 5-Day Avg Vol / 240 mins) ? 
            # NO. Baseline is "Average 5-min Vol" from history_updater.
            # Avg_1min_Vol = Baseline / 5
            # Current_1min_Vol = Current_Vol / Minutes_Elapsed
            # VR = Current_1min_Vol / Avg_1min_Vol
            
            baseline_5min = self._get_baseline_volume(stock.code)
            
            volume_ratio = 1.0
            
            if baseline_5min > 0:
                avg_1min = baseline_5min / 5.0
                curr_1min = stock.volume / minutes_elapsed
                if avg_1min > 0:
                     volume_ratio = curr_1min / avg_1min
            else:
                # If no history, assume 1.0
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
