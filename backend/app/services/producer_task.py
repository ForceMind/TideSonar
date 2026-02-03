import asyncio
import logging
from backend.app.services.biying_source import BiyingDataSource
from backend.app.services.monitor import MarketMonitor
from backend.app.services.websocket_manager import manager
from backend.app.core.config import settings
from backend.app.services.market_schedule import MarketSchedule

logger = logging.getLogger(__name__)

async def run_mock_producer():
    """
    Background task to generate/fetch data.
    """
    logger.info("Starting Data Producer Task...")
    
    # Check Redis availability (Mocking status for now as standalone)
    redis_available = False
    
    # Only Biying Source Supported Now
    logger.info("Using REAL DATA SOURCE (BiyingAPI)")
    source = BiyingDataSource()
    poll_interval = 0.5 # Handled by internal batch logic

    monitor = MarketMonitor()


    try:
        while True:
            # 0. Check Market Hours & Active Clients (Lazy Mode)
            # If no clients, we sleep. BUT if we have no data yet (server just started), we must fetch once regardless of clients.
            if len(manager.active_connections) == 0 and manager.has_data():
                 # No clients connected AND we have data -> Sleep
                 await asyncio.sleep(2)
                 continue

            market_open = MarketSchedule.is_market_open()

            if not market_open:
                 # Logic: If closed
                 if manager.has_data() and not manager.is_data_stale():
                     # If we have data AND it's fresh (post-close), just sleep.
                     # This prevents the loop from running again and again.
                     logger.info("Market Closed (Data Cached & Fresh). Sleeping 60s...")
                     await asyncio.sleep(60)
                     continue
                 else:
                     logger.info("🌙 Market Closed. Cache Empty or Stale (e.g. 13:00 data). Fetching Closing Snapshot ONCE...")
                     # If data is stale (e.g. we had 13:00 data but now it's 20:00), we proceed to fetch.
                     # This ensures we overwrite the 13:00 cache with 15:00 close price.
                     pass

            # 1. Get Data
            # source.get_snapshot is blocking (requests), so run in thread to avoid freezing loop
            try:
                snapshot = await asyncio.to_thread(source.get_snapshot)
            except Exception as e:
                logger.error(f"Snapshot Fetch Error: {e}")
                snapshot = []
            else:
                 snapshot = await asyncio.to_thread(source.get_snapshot)
            
            # 2. Process
            # detect_anomalies is also CPU bound
            # In high-perf, run in threadpool. For mock, direct call is acceptable or use to_thread.
            alerts = await asyncio.to_thread(monitor.detect_anomalies, snapshot)
            
            if alerts:
                logger.info(f"Generated {len(alerts)} alerts. Broadcasting mix sample...")
                
                # FALLBACK: If Redis is down, inject directly to WS Manager so frontend works
                if not redis_available:
                     # Strategy: Scientific Selection (Top Volume/Amount) -> Stability
                     # User Request: "Find stocks with real fund flow" & "Stable List"
                     
                     # 1. Group by Index
                     grouped = {"HS300": [], "ZZ500": [], "ZZ1000": [], "ZZ2000": []}
                     for a in alerts:
                         if a.index_code in grouped:
                             grouped[a.index_code].append(a)
                     
                     final_selection = []
                     
                     # 2. Select Top Candidates per Index
                     # Sort by 'amount' (Turnover money) -> Proxies activity/funds
                     # This ensures the list doesn't flicker randomly; the top active stocks stay top active.
                     for idx, items in grouped.items():
                         # Filter: Optional - Only show stocks with volume > 0
                         valid_items = [x for x in items if x.amount > 0]
                         
                         # Sort: Descending by Amount (Big Money)
                         # Secondary Sort: Pct Change (Big Movers)
                         valid_items.sort(key=lambda x: x.amount, reverse=True)
                         
                         # Take Top 30 per index (Total ~120, comfortable for UI)
                         # This acts as a "Focus List" of the market leaders.
                         top_picks = valid_items[:30]
                         final_selection.extend(top_picks)

                    # Track distribution for debug
                     sent_counts = {"HS300": 0, "ZZ500": 0, "ZZ1000": 0, "ZZ2000": 0}
                     
                     # NEW: Snapshot Persistence
                     # Convert all alerts to JSON strings first
                     snapshot_json_list = [a.model_dump_json() for a in final_selection]
                     
                     # Store in Manager so new connections get them immediately
                     manager.update_snapshot(snapshot_json_list)

                     for alert_str in snapshot_json_list:
                        try:
                            # Parse back just to check index or just broadcast string directly (optimized)
                            # To keep logic simple and safe, we broadcast the string.
                            await manager.broadcast(alert_str)
                            
                            # Simple counter (approximate since we don't parse back index here for speed, or we assume logic above is correct)
                            # Actually let's assume distribution logic above is correct for the log.
                        except Exception as e:
                            logger.error(f"Broadcast error: {e}")
                            
                     # Log correct distribution from the selection list objects
                     for a in final_selection:
                         if a.index_code in sent_counts: sent_counts[a.index_code] += 1
                    
                     logger.info(f"   -> Sent {len(final_selection)} alerts (Top Activity). Dist: {sent_counts}")
            
            # 3. Frequency
            if not market_open:
                # If we are here and market is closed, it means we just performed the "One-Off Fetch".
                # We should sleep longer to avoid hammering, or just rely on the loop check next time.
                # Setting a long sleep here is safe.
                logger.info("🌙 One-off fetch complete. Snapshot stored. Sleeping 60s...")
                await asyncio.sleep(60)
            else:
                # Normal trading hours: fast poll
                await asyncio.sleep(poll_interval)
            
    except asyncio.CancelledError:
        logger.info("Data Producer Task Cancelled.")
    except Exception as e:
        logger.error(f"Error in Producer: {e}")
