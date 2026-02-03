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
            if len(manager.active_connections) == 0:
                 # No clients connected, save bandwidth/resources
                 # Check less frequently (e.g., every 2 seconds) just to stay ready
                 await asyncio.sleep(2)
                 continue

            if not MarketSchedule.is_market_open():
                 # Log once per minute?
                 # logger.info("Market Closed. Sleeping...")
                 await asyncio.sleep(60)
                 continue

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

                     for alert in final_selection:
                        try:
                            # Verify Index Code matches frontend keys
                            if alert.index_code in sent_counts:
                                sent_counts[alert.index_code] += 1
                                
                            await manager.broadcast(alert.model_dump_json())
                        except Exception as e:
                            logger.error(f"Broadcast error: {e}")
                    
                     logger.info(f"   -> Sent {len(final_selection)} alerts (Top Activity). Dist: {sent_counts}")
            
            # 3. Frequency
            # 0.5s is very fast. 200 msgs * 2 Hz = 400 msg/s. Acceptable.
            await asyncio.sleep(poll_interval)
            
    except asyncio.CancelledError:
        logger.info("Data Producer Task Cancelled.")
    except Exception as e:
        logger.error(f"Error in Producer: {e}")
