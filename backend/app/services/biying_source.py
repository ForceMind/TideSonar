import requests
import json
import os
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, date
from backend.app.models.stock import StockData
from backend.app.core.interfaces import BaseDataSource
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = "backend/data"
CACHE_FILE = os.path.join(CACHE_DIR, "index_constituents.json")

# Map our internal Index Codes to Biying/Standard Index codes
# HS300/ZZ500: Use 'hszg/gg' standard index API
# ZZ1000/ZZ2000: Use 'hslt/sectors' sector API
INDEX_MAP = {
    "HS300": "hs300",
    "ZZ500": "zhishu_000905",
    "ZZ1000": "中证1000",
    "ZZ2000": "中证2000"
}

class BiyingDataSource(BaseDataSource):
    def __init__(self):
        self.license = settings.BIYING_LICENSE
        if self.license == "YOUR_LICENSE_KEY_HERE":
            logger.warning("Biying License not set! Please set BIYING_LICENSE in .env")
            
        self.stock_index_map = self._load_or_update_stock_list()
        # Session for connection pooling
        self.session = requests.Session()
        
    def _load_or_update_stock_list(self) -> Dict[str, str]:
        """
        Load stock->index mapping from cache. 
        If cache missing or stale (older than today), update it.
        """
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        should_update = True
        if os.path.exists(CACHE_FILE):
            mod_time = os.path.getmtime(CACHE_FILE)
            file_date = date.fromtimestamp(mod_time)
            if file_date == date.today():
                should_update = False
                logger.info("Loading stock list from local cache.")
        
        if should_update:
            try:
                mapping = self._fetch_indices_from_api()
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(mapping, f, ensure_ascii=False)
                logger.info("Stock list updated from Biying API.")
                return mapping
            except Exception as e:
                logger.error(f"Failed to update stock list from API: {e}")
                if os.path.exists(CACHE_FILE):
                    logger.warning("Falling back to stale cache.")
                    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    return {}
        else:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

    def _fetch_indices_from_api(self) -> Dict[str, str]:
        """
        Fetch constituents for all tracked indices.
        Returns: Dict[stock_code, index_code]
        """
        mapping = {}
        for internal_name, index_code in INDEX_MAP.items():
            stocks_list = []
            
            # Decide which API to use based on the code format
            # Chinese characters -> Sector API (hslt/sectors)
            # Alphanumeric -> Standard Index API (hszg/gg)
            is_sector_api = any(u'\u4e00' <= char <= u'\u9fff' for char in index_code)
            
            try:
                if is_sector_api:
                    # Sector API: http://api.biyingapi.com/hslt/sectors/NAME/LICENSE
                    url = f"http://api.biyingapi.com/hslt/sectors/{index_code}/{self.license}"
                    logger.info(f"Fetching SECTOR constituents for {internal_name} ({index_code})...")
                    # Increased timeout for large sectors (3000+ total requests sometimes slow)
                    resp = requests.get(url, timeout=60)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Sector API returns dict: {'stocks': [...], ...}
                        if isinstance(data, dict):
                            stocks_list = data.get('stocks', [])
                        else:
                            logger.error(f"Unexpected sector format for {internal_name}: {type(data)}")
                    else:
                        logger.error(f"Sector API Error {resp.status_code} for {internal_name}")
                
                else:
                    # Index API: http://api.biyingapi.com/hszg/gg/CODE/LICENSE
                    url = f"http://api.biyingapi.com/hszg/gg/{index_code}/{self.license}"
                    logger.info(f"Fetching INDEX constituents for {internal_name} ({index_code})...")
                    resp = requests.get(url, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json() 
                        # Index API returns list: [...]
                        if isinstance(data, list):
                            stocks_list = data
                        else:
                            logger.error(f"Unexpected index format for {internal_name}: {type(data)}")
                    else:
                        logger.error(f"Index API Error {resp.status_code} for {internal_name}")

                # Process the stock list (works for both formats if stocks_list is populated)
                count = 0
                for item in stocks_list:
                    # 'dm' is code (daima)
                    code = item.get('dm', '')
                    # Clean the code: Remove .SH, .SZ, or other suffixes just in case
                    if code:
                        clean_code = code.split('.')[0]
                        mapping[clean_code] = internal_name
                        count += 1
                logger.info(f"   -> Loaded {count} stocks for {internal_name}")
                
            except Exception as e:
                logger.error(f"Request failed for {internal_name}: {e}")

                
        return mapping

    def get_snapshot(self) -> List[StockData]:
        """
        Alias for get_real_time_data to satisfy BaseDataSource interface.
        """
        return self.get_real_time_data()

    def get_real_time_data(self) -> List[StockData]:
        """
        Fetch real-time data using Batch API (up to 20 stocks per request).
        URL: http://api.biyingapi.com/hsrl/ssjy_more/...
        This avoids the strict 1/min limit of the global snapshot API.
        """
        all_codes = list(self.stock_index_map.keys())
        if not all_codes:
            return []

        # Helper to chunk list
        def chunker(seq, size):
            return (seq[pos:pos + size] for pos in range(0, len(seq), size))

        result = []
        now = datetime.now()
        
        # We'll log the first batch success only to avoid spam
        first_batch = True
        
        # Use session for existing TCP connection reuse
        # if not hasattr(self, 'session'):
        #     self.session = requests.Session()
        #     self.session.headers.update({
        #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        #     })

        batch_count = 0
        BATCH_SIZE = 15 # Reduced from 20 to be safer
        total_batches = (len(all_codes) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch in chunker(all_codes, BATCH_SIZE):
            batch_count += 1
            codes_str = ",".join(batch)
            url = f"http://api.biyingapi.com/hsrl/ssjy_more/{self.license}"
            params = {"stock_codes": codes_str}

            try:
                # Use simple requests.get to match working test scripts (avoid Session/Cookie issues)
                resp = requests.get(url, params=params, timeout=5)

                if resp.status_code == 200:
                    data_list = resp.json()
                    # data_list is typically a list of dicts
                    if isinstance(data_list, list):
                        for item in data_list:
                            # Map fields based on user doc / observation
                            # p: price, o: open, h: high, l: low
                            # pc: pct_chg (?), zdf: zhang die fu
                            # v: volume, cje: amount (cheng jiao e)
                            # dm: code, mc: name (maybe)

                            code = item.get('dm')
                            if not code: continue

                            idx_code = self.stock_index_map.get(code)

                            try:
                                # Safe float conversion
                                price = float(item.get('p', 0) or 0)
                                # Try 'pc' (percent change) or 'zdf'
                                pct_chg = float(item.get('pc', 0) or item.get('zdf', 0) or 0)
                                volume = int(float(item.get('v', 0) or 0))
                                amount = float(item.get('cje', 0) or 0)
                                name = item.get('mc') or item.get('name') or code # Fallback

                                stock_obj = StockData(
                                    code=code,
                                    name=str(name),
                                    price=price,
                                    pct_chg=pct_chg,
                                    volume=volume,
                                    amount=amount,
                                    timestamp=now,
                                    index_code=idx_code or "UNKNOWN"
                                )
                                result.append(stock_obj)
                            except Exception:
                                continue

                    if first_batch:
                        # logger.info(f"Batch fetched successfully. Items: {len(data_list)}")
                        first_batch = False
                else:
                    logger.warning(f"Batch API error: {resp.status_code}")

            except Exception as e:
                logger.error(f"Batch Fetch Error: {e}")
            
            # Rate Limiting: Sleep slightly between batches to avoid 429
            # 190 batches * 0.05s = ~9.5s delay added total
            # This is safer than bursting 190 requests instantly
            time.sleep(0.05)
            
            # Optional: Log progress every 50 batches
            if batch_count % 50 == 0:
                logger.info(f"   Fetched {batch_count}/{total_batches} batches...")

        return result
