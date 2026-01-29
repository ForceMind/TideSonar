import random
import time
from typing import List, Dict
from datetime import datetime
from backend.app.models.stock import StockData, StockAlert
from backend.app.core.interfaces import BaseDataSource

# Mock Universe Constants
INDICES = ["HS300", "ZZ500", "ZZ1000", "ZZ2000"]
SECTORS = ["Technology", "Finance", "Healthcare", "Consumer", "Energy", "Materials"]

class MockDataSource(BaseDataSource):
    def __init__(self, stock_count: int = 4000):
        self.stock_count = stock_count
        self.stocks_meta = self._init_universe()
        
    def _init_universe(self) -> List[Dict]:
        """Initialize static metadata for stocks"""
        universe = []
        for i in range(self.stock_count):
            index_code = random.choice(INDICES)
            universe.append({
                "code": f"{600000+i:06d}" if i % 2 == 0 else f"{1+i:06d}",
                "name": f"Stock-{i}",
                "index_code": index_code,
                "sector": random.choice(SECTORS),
                "base_price": round(random.uniform(5, 100), 2)
            })
        return universe

    def get_snapshot(self) -> List[StockData]:
        """Generate a real-time snapshot of the market"""
        snapshot = []
        timestamp = datetime.now()
        
        for meta in self.stocks_meta:
            # Simulate random fluctuation
            change_factor = random.gauss(0, 0.02) # Normal distribution centered at 0
            
            # Occasionally inject an anomaly (Fat Tail)
            if random.random() < 0.005: # 0.5% chance of anomaly
                change_factor = random.choice([random.uniform(0.015, 0.05), random.uniform(-0.05, -0.015)])
                
            current_price = round(meta["base_price"] * (1 + change_factor), 2)
            pct_chg = round(change_factor * 100, 2)
            
            # Simulate Volume & Amount
            # Normal volume
            base_vol = random.randint(1000, 50000) 
            
            # If large change, higher volume prob
            if abs(pct_chg) > 1.5:
                base_vol = base_vol * random.uniform(2, 5)
            
            current_volume = int(base_vol)
            current_amount = current_volume * current_price * 100 # Assuming 1 lot = 100 shares approx for calculation logic check
            
            data = StockData(
                code=meta["code"],
                name=meta["name"],
                price=current_price,
                pct_chg=pct_chg,
                volume=current_volume,
                amount=current_amount,
                timestamp=timestamp,
                index_code=meta["index_code"]
            )
            snapshot.append(data)
            
        return snapshot
