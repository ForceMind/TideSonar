from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
from backend.app.models.stock import StockData

class BaseDataSource(ABC):
    """
    Abstract Base Class for Data Sources.
    Implement this interface to connect to real market data APIs (e.g., XtQuant, TqSdk, Sina, etc.)
    """

    @abstractmethod
    def __init__(self, **kwargs):
        """Initialize connection to data source"""
        pass

    @abstractmethod
    def get_snapshot(self) -> List[StockData]:
        """
        Fetch the latest snapshot of the entire market (or subscribed list).
        Returns a list of normalized StockData objects.
        """
        pass
        
    def validate_data(self, data: StockData) -> bool:
        """Optional: Validate data integrity"""
        if data.price <= 0:
            return False
        return True
