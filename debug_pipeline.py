import os
import sys
import asyncio
from backend.app.services.biying_source import BiyingDataSource
from backend.app.services.monitor import MarketMonitor

async def test_pipeline():
    print("--- 1. Initializing Source ---")
    source = BiyingDataSource()
    print(f"Source loaded map size: {len(source.stock_index_map)}")
    
    # Check map sample
    sample_items = list(source.stock_index_map.items())[:5]
    print(f"Map Sample: {sample_items}")

    print("\n--- 2. Fetching Snapshot ---")
    # Run in thread as per producer
    snapshot = await asyncio.to_thread(source.get_snapshot)
    print(f"Snapshot received: {len(snapshot)} items")
    
    if len(snapshot) > 0:
        print(f"First item: {snapshot[0]}")
    else:
        print("!! SNAPSHOT IS EMPTY !!")
        return

    print("\n--- 3. Running Monitor Logic (Simulation) ---")
    monitor = MarketMonitor()
    
    target_indices = {"HS300", "ZZ500", "ZZ1000", "ZZ2000"}
    
    passed_index = 0
    passed_amount = 0
    passed_change = 0
    
    alerts = []
    
    for stock in snapshot:
        # Filter 1: Index
        if stock.index_code not in target_indices:
            continue
        passed_index += 1
        
        # Filter 2: Amount
        min_amount = 20_000_000
        if stock.index_code == "ZZ1000":
            min_amount = 10_000_000
        elif stock.index_code == "ZZ2000":
            min_amount = 3_000_000
            
        if stock.amount <= min_amount:
            continue
        passed_amount += 1
        
        # Filter 3: Change
        if abs(stock.pct_chg) <= 1.0:
            continue
        passed_change += 1
        
        # Logic 4: Volume Ratio (ignored for count, but monitored)
        alerts.append(stock)

    print(f"Total Snapshot: {len(snapshot)}")
    print(f"Passed Index Filter ({target_indices}): {passed_index}")
    print(f"Passed Amount Filter: {passed_amount}")
    print(f"Passed PctChg Filter (>1%): {passed_change}")
    print(f"Final Alerts Generated: {len(alerts)}")
    
    if len(alerts) == 0:
        print("\n!!! NO ALERTS GENERATED - ALL FILTERED OUT !!!")
        print("Reason Analysis:")
        if passed_index == 0:
            print(" -> Index Code mismatches. Check cached map.")
        elif passed_amount == 0:
            print(" -> Turnover (Amount) too low. Check min_amount thresholds.")
        elif passed_change == 0:
            print(" -> Volatility too low. Check pct_chg threshold.")

if __name__ == "__main__":
    # Mock settings
    os.environ["BIYING_LICENSE"] = "7E1A1BA6-0402-4505-82B1-ECCAA7281B26"
    asyncio.run(test_pipeline())
