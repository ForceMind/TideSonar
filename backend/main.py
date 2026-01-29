import time
import asyncio
from backend.app.services.mock_source import MockDataSource
from backend.app.services.monitor import MarketMonitor

def main():
    print("Initializing GuanChao System (Step 1 Backend Test)...")
    
    # 1. Init Data Source (Simulate 4000 stocks)
    source = MockDataSource(stock_count=4000)
    print(f"Mock Data Source initialized with {source.stock_count} stocks.")

    # 2. Init Monitor Engine
    monitor = MarketMonitor()
    print("MarketMonitor Engine initialized.")
    if monitor.redis_client:
        print("Redis Connection: OK")
    else:
        print("Redis Connection: Failed (Using Standalone Mode)")

    print("\nStarting Event Loop (Press Ctrl+C to stop)...")
    print("-" * 50)

    try:
        while True:
            start_time = time.time()
            
            # 1. Get Data
            snapshot = source.get_snapshot()
            
            # 2. Process Data
            alerts = monitor.detect_anomalies(snapshot)
            
            # 3. Output Results
            if alerts:
                print(f"[{time.strftime('%H:%M:%S')}] Detected {len(alerts)} Anomalies:")
                for alert in alerts:
                    # Color coding for terminal output (Red for Up, Green for Down in China, but let's stick to text)
                    direction = "▲" if alert.pct_chg > 0 else "▼"
                    print(f"  {direction} {alert.code} {alert.name} | {alert.index_code} | "
                          f"Chg: {alert.pct_chg:>5.2f}% | VolRatio: {alert.volume_ratio:>4.1f} | "
                          f"Amt: {alert.amount/100000000:>6.2f}亿")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] No anomalies detected in this tick.")

            # Wait for next tick (3 seconds)
            elapsed = time.time() - start_time
            sleep_time = max(0, 3.0 - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopping Monitor...")

if __name__ == "__main__":
    main()
