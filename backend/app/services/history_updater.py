import aiohttp
import asyncio
import logging
import os
import json
from typing import List, Dict, Optional
import sys

# Add project root to path for imports when running as script
sys.path.append(os.getcwd())

# Import Source to get universe
try:
    from backend.app.services.biying_source import BiyingDataSource
except ImportError:
    # If running as script from root
    from services.biying_source import BiyingDataSource

# Settings
BIYINAPI_BASE_URL = "https://api.biyingapi.com/hsstock/history"
LICENSE = os.getenv("BIYING_LICENSE", "YOUR_LICENSE_HERE") 
HISTORY_DATA_FILE = "history_baseline.json"

logger = logging.getLogger(__name__)

async def fetch_history_data(stock_code: str, session: aiohttp.ClientSession) -> List[Dict]:
    """
    Fetch historical K-line data (5-minute).
    """
    # API: /hsstock/history/{code}/5/n/{license}?lt=200
    # lt=200 covers ~4 days (48 bars * 4 = 192)
    url = f"{BIYINAPI_BASE_URL}/{stock_code}/5/n/{LICENSE}?lt=200"
    
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.json()
            if response.status != 200:
                logger.warning(f"API Error {stock_code}: {response.status}")
            return []
    except Exception as e:
        logger.error(f"Network Error {stock_code}: {e}")
        return []

def calculate_baseline_volumes(history_data: List[Dict]) -> float:
    """
    Calculate average volume from history list.
    """
    if not history_data:
        return -1.0
        
    total_vol = 0
    count = 0
    
    for kline in history_data:
        v = 0
        try:
            # Biying API returns a list of dictionaries or list of lists
            # Example: {"d":"2023-10-27 14:55:00", "o":..., "v": "100", ...}
            if isinstance(kline, dict):
                v = float(kline.get('v', kline.get('vol', 0)))
            elif isinstance(kline, list) and len(kline) > 5:
                v = float(kline[5]) # Assumption for list format
                
            if v > 0:
                total_vol += v
                count += 1
        except:
            pass
            
    return total_vol / count if count > 0 else -1.0

def format_stock_code(code: str) -> str:
    # Biying format: 000001.SZ
    if "." in code: return code 
    if code.startswith('6'): return f"{code}.SH"
    if code.startswith('4') or code.startswith('8'): return f"{code}.BJ"
    return f"{code}.SZ"

async def update_history_baseline_task(stock_list: Optional[List[str]] = None):
    """
    Orchestrator:
    1. If stock_list is None, fetch Universe (HS300/ZZ500/ZZ1000/ZZ2000) from Source.
    2. Fetch History.
    3. Save based on simple average.
    """
    print("🚀 Starting History Baseline Update...")
    
    target_codes = stock_list
    
    # 1. Get Universe if not provided
    if not target_codes:
        try:
            print(" -> Loading Stock Universe from DataSource...")
            ds = BiyingDataSource()
            # Ensure index map is loaded
            if not ds.stock_index_map:
                await ds.fetch_universe()
                
            universe_map = ds.stock_index_map
            
            # Filter for target indices
            target_indices = {"HS300", "ZZ500", "ZZ1000", "ZZ2000"}
            target_codes = [
                code for code, meta in universe_map.items() 
                if meta.get('index') in target_indices
            ]
            
            # If still empty (e.g. fetch failed), try fetching common indices directly
            if not target_codes:
                 print(" -> Warning: Universe map empty. Attempting direct fallback...")
                 # Minimal fallback or retry logic could go here
                 pass
            
            print(f" -> Found {len(target_codes)} target stocks in indices: {target_indices}")
            
        except Exception as e:
            logger.error(f"Failed to load universe: {e}")
            print(f"❌ Error loading universe: {e}")
            return

    if not target_codes:
        print("❌ No stocks to update.")
        return

    # 2. Fetch Loop
    baselines = {}
    total = len(target_codes)
    
    # Setup connection limit
    connector = aiohttp.TCPConnector(limit=20) 
    
    async with aiohttp.ClientSession(connector=connector) as session:
        chunk_size = 50
        for i in range(0, total, chunk_size):
            chunk = target_codes[i:i+chunk_size]
            
            tasks = []
            for code in chunk:
                full_code = format_stock_code(code)
                tasks.append(fetch_history_data(full_code, session))
                
            results = await asyncio.gather(*tasks)
            
            # Process results
            for idx, r in enumerate(results):
                input_code = chunk[idx]
                mean_vol = calculate_baseline_volumes(r)
                if mean_vol > 0:
                    baselines[input_code] = int(mean_vol)
            
            print(f"    Progress: {min(i+chunk_size, total)}/{total} done. (Saved: {len(baselines)})")
            # Rate limit
            await asyncio.sleep(0.5) 

    # 3. Save
    try:
        with open(HISTORY_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(baselines, f)
        print(f"✅ Success! Baseline data saved to {HISTORY_DATA_FILE} ({len(baselines)} records).")
    except Exception as e:
        print(f"❌ Failed to write file: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Windows Selector Event Loop Policy fix
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(update_history_baseline_task())

