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
        In a real system, this would query a pre-calculated DataFrame or DB.
        """
        if code not in self.baseline_volumes:
            # Deterministic pseudo-random based on code
            seed = int(code) if code.isdigit() else hash(code)
            np.random.seed(seed % 2**32)
            self.baseline_volumes[code] = np.random.randint(1000, 20000)
        return self.baseline_volumes[code]

    def detect_anomalies(self, snapshot: List[StockData]) -> List[StockAlert]:
        alerts = []
        
        # Convert to DataFrame for vectorized operations (faster for 4000 stocks)
        # But for clarity in this step, I'll iterate. 
        # Requirement: "only specific indices"
        
        target_indices = {"HS300", "ZZ500", "ZZ1000", "ZZ2000"}
        
        for stock in snapshot:
            # 1. Filter Index
            if stock.index_code not in target_indices:
                continue

            # 2. Filtering Logic
            # Condition B: Amount > 10,000,000 (10 Million)
            if stock.amount <= 10_000_000:
                continue
                
            # Condition C: Abs(Pct_Chg) > 1.0%
            if abs(stock.pct_chg) <= 1.0:
                continue

            # Condition A: Volume Ratio > 2.5
            baseline = self._get_baseline_volume(stock.code)
            # Avoid division by zero
            if baseline == 0:
                baseline = 100
                
            volume_ratio = stock.volume / baseline
            
            if volume_ratio > 2.5:
                # HIT!
                alert = StockAlert(
                    code=stock.code,
                    name=stock.name,
                    price=stock.price,
                    pct_chg=stock.pct_chg,
                    amount=stock.amount,
                    volume_ratio=round(volume_ratio, 2),
                    index_code=stock.index_code,
                    timestamp=stock.timestamp.isoformat(),
                    reason=f"VolRatio:{volume_ratio:.1f}|Amt:{stock.amount/10000:.0f}W|Chg:{stock.pct_chg}%"
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
