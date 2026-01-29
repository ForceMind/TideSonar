from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StockData(BaseModel):
    code: str
    name: str
    price: float
    pct_chg: float  # Percentage change (e.g., 1.5 for 1.5%)
    volume: int     # Current minute volume (mocked as total volume for simplicity in snapshot)
    amount: float   # Transaction amount
    timestamp: datetime = datetime.now()
    
    # Optional field to identify index membership roughly for mock
    index_code: Optional[str] = None # HS300, ZZ500, ZZ1000, ZZ2000

class StockAlert(BaseModel):
    code: str
    name: str
    price: float
    pct_chg: float
    amount: float
    volume_ratio: float
    index_code: str
    timestamp: str  # ISO Serialized string
    reason: str     # Why it triggered
