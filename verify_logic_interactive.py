import os
import sys
import asyncio
import logging
from collections import Counter

# Configure logging to show info
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure path is set
sys.path.append(os.getcwd())

async def run_verification():
    print("========================================================")
    print("   TideSonar Logic Verification (Interactive Mode)")
    print("========================================================")
    
    # 1. Secure Input
    key = input("Please enter your Biying License Key: ").strip()
    if not key:
        print("❌ Error: Key is required.")
        return
    
    os.environ["BIYING_LICENSE"] = key
    
    # Lazy imports to ensure env var is set before config reads it (if it reads eagerly)
    # Ideally config reads env var on access or init.
    # Let's clean sys.modules to force reload config if needed, or just hope config uses os.getenv
    try:
        from backend.app.services.biying_source import BiyingDataSource
        from backend.app.services.monitor import MarketMonitor
        from backend.app.core.config import settings
    except ImportError as e:
        print(f"❌ Import Error: {e}. Make sure you are running from project root (e.g. E:\\Privy\\TideSonar)")
        return

    # Update settings manually just in case
    settings.BIYING_LICENSE = key

    # 2. Source Initialization
    print("\n[Step 1] Initializing Data Source...")
    print("   -> Loading stock universe (this might trigger API calls if cache is missing)...")
    source = BiyingDataSource()
    
    total_stocks = len(source.stock_index_map)
    print(f"   ✅ Loaded {total_stocks} stocks.")
    
    if total_stocks == 0:
        print("   ❌ FAILED: Stock list is empty. Check License or API connectivity.")
        return

    # Analyze Universe
    index_counts = Counter(s['index'] for s in source.stock_index_map.values())
    print(f"   -> Index Distribution: {dict(index_counts)}")
    
    if sum(index_counts.values()) < 100:
        print("   ⚠️ WARNING: Too few stocks. Verify API returned full list.")

    # 3. Snapshot Fetch
    print("\n[Step 2] Fetching Real-time Snapshot...")
    try:
        snapshot = await asyncio.to_thread(source.get_snapshot)
    except Exception as e:
        print(f"   ❌ FAILED: Fetch error: {e}")
        return

    print(f"   ✅ Snapshot received: {len(snapshot)} records.")
    
    if len(snapshot) == 0:
        print("   ❌ FAILED: API returned 0 records.")
        return

    # Check Validity
    valid_prices = sum(1 for s in snapshot if s.price > 0)
    print(f"   -> Stocks with Price > 0: {valid_prices}")
    
    # 4. Monitor Logic (Filtering)
    print("\n[Step 3] Testing Filter Monitor Logic...")
    monitor = MarketMonitor()
    
    # We want to see WHY alerts are generated or not
    # Let's copy-paste logic simulation for transparency
    
    alerts = []
    
    stats = {
        "HS300": {"total": 0, "pass_amount": 0, "pass_pct": 0},
        "ZZ500": {"total": 0, "pass_amount": 0, "pass_pct": 0},
        "ZZ1000": {"total": 0, "pass_amount": 0, "pass_pct": 0},
        "ZZ2000": {"total": 0, "pass_amount": 0, "pass_pct": 0},
    }
    
    monitor_indices = set(stats.keys())
    
    for stock in snapshot:
        idx = stock.index_code
        if idx not in monitor_indices:
            continue
            
        stats[idx]["total"] += 1
        
        # 4.a Amount Filter
        min_amount = 20_000_000
        if idx == "ZZ1000": min_amount = 10_000_000
        elif idx == "ZZ2000": min_amount = 3_000_000
        
        if stock.amount > min_amount:
            stats[idx]["pass_amount"] += 1
            
            # 4.b Change Filter (>1.0%)
            # NOTE: Monitor uses 1.0 now
            if abs(stock.pct_chg) > 1.0:
                 stats[idx]["pass_pct"] += 1
                 # Add to alerts
                 alerts.append(stock)

    print("\n   [Filter Statistics]")
    print(f"   {'Index':<10} | {'Total':<8} | {'Pass Amount':<12} | {'Pass >1%':<10} | {'Min Amt Config'}")
    print("   " + "-"*60)
    for idx, d in stats.items():
        min_amt = "2000w"
        if idx == "ZZ1000": min_amt = "1000w"
        if idx == "ZZ2000": min_amt = "300w"
        print(f"   {idx:<10} | {d['total']:<8} | {d['pass_amount']:<12} | {d['pass_pct']:<10} | {min_amt}")

    print(f"\n   ✅ Total Candidate Alerts: {len(alerts)}")

    # 5. Output Preview
    print("\n[Step 4] Previewing Top Alerts (Proof of Data)...")
    if alerts:
        # Group by index for preview
        preview_map = {"HS300": [], "ZZ500": [], "ZZ1000": [], "ZZ2000": []}
        for a in alerts:
            if a.index_code in preview_map:
                preview_map[a.index_code].append(a)
        
        for idx, items in preview_map.items():
            print(f"\n   --- {idx} Sample (Top 3) ---")
            if not items:
                print("      (No alerts for this index)")
                continue
            for item in items[:3]:
                print(f"      [{item.code}] {item.name:<8} : +{item.pct_chg}%  Vol:{int(item.amount/10000)}w")
    else:
        print("   ⚠️ No alerts generated. The market might be flat or closed, or thresholds are too high.")

    print("\n========================================================")
    print("   Verification Complete.")
    print("========================================================")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_verification())
