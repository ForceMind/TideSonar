import requests
import json
import os
import time
import logging
import urllib.parse
import concurrent.futures
from typing import List, Dict, Optional, TypedDict, Any
from datetime import datetime, date
from backend.app.models.stock import StockData
from backend.app.core.interfaces import BaseDataSource
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = "backend/data"
CACHE_FILE = os.path.join(CACHE_DIR, "index_constituents.json")

class StockMeta(TypedDict):
    index: str
    name: str 
    industry: str
    concept: str
    block: str # Deprecated

class BiyingDataSource(BaseDataSource):
    def __init__(self):
        self.license = settings.BIYING_LICENSE
        if not self.license or "YOUR" in self.license:
            logger.warning("Biying License not set correctly!")
            
        self.session = requests.Session()
        
        # Load Universe
        self.stock_index_map: Dict[str, StockMeta] = self._load_or_update_stock_list()
        
    def _load_or_update_stock_list(self) -> Dict[str, StockMeta]:
        """
        New V4 Logic:
        1. Fetch ALL Stocks from hslt/list (Since hslt/sectors is unstable).
        2. Fetch Concepts for ALL Stocks.
        3. Detect Index (HS300/ZZ500/etc) and Block from Concepts.
        4. Cache.
        """
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        if os.path.exists(CACHE_FILE):
             logger.info("✅ Loading stock list from local cache (Static).")
             try:
                 with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # V5 Schema Validation: Check if 'industry' exists in the first item
                    if cache_data and isinstance(cache_data, dict):
                        first_value = next(iter(cache_data.values()))
                        if "industry" not in first_value:
                            logger.warning("⚠️ Cache schema outdated (missing 'industry'). Triggering full re-fetch.")
                            # Do not return, let it fall through to fetch logic
                        else:
                            return cache_data
                    else:
                        # Empty or invalid -> refetch
                        pass
             except Exception:
                 logger.warning("Cache file corrupted, refetching...")
        
        logger.info("⚡ Initializing Stock Universe (Full Scan Strategy)...")
        
        # Step 1: Get Global List
        mapping = self._fetch_all_stocks()
        if not mapping:
            logger.error("Failed to fetch global stock list.")
            return {}

        # Step 2: Enrich with Concepts (Index + Block detection)
        self._enrich_details(mapping)
        
        # Step 3: Save
        if mapping:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False)
            logger.info(f"✅ Full Universe ({len(mapping)} stocks) saved to cache.")
            return mapping
        else:
            return {}

    def _fetch_all_stocks(self) -> Dict[str, StockMeta]:
        """Fetch all stocks from hslt/list."""
        mapping = {}
        url = f"http://api.biyingapi.com/hslt/list/{self.license}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for item in data:
                        code = item.get('dm', '')
                        name = item.get('mc', '')
                        if code:
                            clean_code = code.split('.')[0]
                            mapping[clean_code] = {
                                "index": "OTHER", # Default
                                "name": name,
                                "industry": "",
                                "concept": "",
                                "block": ""
                            }
                    logger.info(f"   -> Found {len(mapping)} total stocks.")
        except Exception as e:
            logger.error(f"   -> Failed to fetch list: {e}")
        return mapping

    def _enrich_details(self, mapping: Dict[str, StockMeta]):
        """Fetch concepts to find Index adherence and Sector block."""
        logger.info(f"   Fetching Metadata for {len(mapping)} stocks (50 Threads)...")
        
        all_codes = list(mapping.keys())
        total = len(all_codes)
        processed = 0
        
        # Priority rules for assigning index if multiple match
        # Lower index in this list = Higher Priority override
        # Actually logic: Only upgrade "OTHER" or specific order?
        # Let's simple check strict strings.
        
        def fetch_meta(code):
            url = f"http://api.biyingapi.com/hszg/zg/{code}/{self.license}"
            found_index = "OTHER"
            found_ind = ""
            found_con = ""
            try:
                resp = requests.get(url, timeout=10) # 10s per request
                if resp.status_code == 200:
                    tags = resp.json()
                    if isinstance(tags, list) and len(tags) > 0:
                        # 1. Parse Tags for Industry and Concept
                        # "sw_" or "sw2_" -> Industry
                        # "gn_" or "chgn_" -> Concept (excluding some noise)
                        
                        # Find First Industry
                        for t in tags:
                            t_code = t.get("code", "")
                            t_name = t.get("name", "")
                            
                            # Grab first Shenwan industry
                            if not found_ind and ("sw_" in t_code or "sw2_" in t_code):
                                found_ind = t_name.replace("A股-申万行业-", "").replace("A股-申万二级-", "")
                        
                        # Find First Concept (skip common noise like "融资融券")
                        skip_concepts = ["融资融券", "转融券", "沪股通", "深股通", "含可转债", "富时罗素"]
                        for t in tags:
                            t_code = t.get("code", "")
                            t_name = t.get("name", "").replace("A股-热门概念-", "").replace("A股-概念板块-", "")
                            
                            if ("gn_" in t_code or "chgn_" in t_code) and not found_con:
                                # Check blacklist
                                if not any(s in t_name for s in skip_concepts):
                                    found_con = t_name
                        
                        # Fallback for display if nothing found
                        if not found_ind and tags: found_ind = tags[0].get("name", "")
                        
                        # 2. Find Index Membership (Priority: HS300 > ZZ500 > ZZ1000 > ZZ2000)
                        temp_index = "OTHER"
                        
                        # Optimization: Check all tags
                        tag_codes = {t.get("code", "").lower() for t in tags}
                        tag_names = {t.get("name", "") for t in tags}
                        
                        if "hs300" in tag_codes:
                            temp_index = "HS300"
                        elif "zz500" in tag_codes or "zhishu_000905" in tag_codes or "chgn_700015" in tag_codes:
                            # 000905 is the official code for ZZ500 (CSI 500)
                            # chgn_700015 is "Middle Cap" (中盘)
                            temp_index = "ZZ500"
                        elif "chgn_700016" in tag_codes: # Small Cap Proxy
                            temp_index = "ZZ1000"
                        elif "chgn_701262" in tag_codes: # Micro Cap Proxy
                            temp_index = "ZZ2000"
                        
                        # Fallback for "OTHER":
                        # If it hasn't been assigned to HS300/ZZ500, but is in the list,
                        # treat remaining OTHER as ZZ2000 (Small/Micro tail map) so they aren't ignored
                        # unless we want to be strict. User wants them to show up.
                        if temp_index == "OTHER":
                             temp_index = "ZZ2000" 

                        found_index = temp_index

                        # Old loop logic removed for set lookup speed
                            
            except Exception:
                pass
            return code, found_index, found_ind, found_con

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            future_to_code = {executor.submit(fetch_meta, code): code for code in all_codes}
            
            for future in concurrent.futures.as_completed(future_to_code):
                code, idx, ind, con = future.result()
                processed += 1
                
                if idx != "OTHER":
                    mapping[code]["index"] = idx
                
                mapping[code]["industry"] = ind
                mapping[code]["concept"] = con
                # Keep block compat
                mapping[code]["block"] = ind 
                    
                if processed % 500 == 0:
                    logger.info(f"     -> Processed {processed}/{total}...")
                    
    def get_snapshot(self) -> List[StockData]:
        """
        Fetch real-time data using Batch API (High Speed).
        """
        all_codes = list(self.stock_index_map.keys())
        if not all_codes:
            return []

        result = []
        now = datetime.now()
        
        BATCH_SIZE = 20
        MAX_WORKERS = 20
        
        # Chunk the codes
        batches = [all_codes[i:i + BATCH_SIZE] for i in range(0, len(all_codes), BATCH_SIZE)]
        
        def fetch_batch(batch_codes):
            if not batch_codes: return []
            codes_str = ",".join(batch_codes)
            url = f"http://api.biyingapi.com/hsrl/ssjy_more/{self.license}"
            params = {"stock_codes": codes_str}
            res_items = []
            try:
                resp = requests.get(url, params=params, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        res_items = data
            except Exception:
                pass 
            return res_items

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_batch = {executor.submit(fetch_batch, b): b for b in batches}
            
            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    data_list = future.result()
                    
                    # 1. Validate Batch Result
                    if not data_list or not isinstance(data_list, list):
                        continue

                    for item in data_list:
                        try:
                            # 2. Validate Item
                            if not isinstance(item, dict):
                                continue

                            code = item.get('dm')
                            if not code: continue

                            # 3. Validate Metadata
                            meta = self.stock_index_map.get(str(code)) # Ensure code is string lookup
                            
                            # If meta is missing or corrupted, use defaults
                            if not meta or not isinstance(meta, dict):
                                meta = {"index": "OTHER", "name": str(code), "block": ""}

                            idx_code = meta.get("index", "OTHER")
                            final_name = meta.get("name") or item.get("mc") or str(code)
                            # final_block is kept for fallback, but industry override is preferred
                            final_block = meta.get("block") or ""
                            
                            # New Fields
                            final_ind = meta.get("industry") or final_block
                            final_con = meta.get("concept") or ""

                            # 4. Construct Object
                            stock_obj = StockData(
                                code=str(code),
                                name=str(final_name),
                                price=float(item.get('p', 0) or 0),
                                pct_chg=float(item.get('pc', 0) or item.get('zdf', 0) or 0),
                                volume=int(float(item.get('v', 0) or 0)),
                                amount=float(item.get('cje', 0) or 0),
                                timestamp=now,
                                index_code=idx_code,
                                block=final_block,
                                industry=final_ind,
                                concept=final_con
                            )
                            result.append(stock_obj)
                        except Exception:
                            # Silently skip individual bad items to preserve batch
                            continue
                            
                except Exception as e:
                    logger.warning(f"Batch fetch failed: {e}")
                    continue

        return result
