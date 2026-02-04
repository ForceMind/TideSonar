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

        # Cache for historical averages (Mock: In real app, load from DB)
        self.baseline_volumes = {} 

    def _get_baseline_volume(self, code: str) -> float:
        """
        Mocking the '5-day average volume for this minute'.
        For Real Data testing without DB, we'll set a higher baseline 
        so we don't flag everything as specific 'Volume Anomaly'.
        """
        if code not in self.baseline_volumes:
            # Random baseline between 5 Million and 50 Million for testing
            # This makes "Volume Ratio" less trivial to hit.
            import random
            random.seed(code)
            self.baseline_volumes[code] = random.randint(5_000_000, 50_000_000)
        return self.baseline_volumes[code]

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
            if stock.volume < 100 
                continue

            # Calculate a mock volume ratio or set to 1.0 if missing
            # In real logic: volume_ratio = volume / baseline
            baseline = self._get_baseline_volume(stock.code)
            volume_ratio = stock.volume / baseline if baseline > 0 else 1.0

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
