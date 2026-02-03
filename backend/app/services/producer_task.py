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
            # 0. Check Market Hours
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
                     # Strategy: Shuffle to ensure all columns get data
                    import random
                    random.shuffle(alerts)

                    # Send up to 500 alerts (Browser can handle this if spread out, but we loop tight)
                    # To prevent lag, we can send them in chunks or just safe limit.
                    limit = 200 
                    count = 0 
                    
                    # Track distribution for debug
                    sent_counts = {"HS300": 0, "ZZ500": 0, "ZZ1000": 0, "ZZ2000": 0}

                    for alert in alerts:
                        try:
                            # Verify Index Code matches frontend keys
                            if alert.index_code in sent_counts:
                                sent_counts[alert.index_code] += 1
                                
                            await manager.broadcast(alert.model_dump_json())
                            count += 1
                            if count >= limit:
                                 break
                        except Exception as e:
                            logger.error(f"Broadcast error: {e}")
                    
                    logger.info(f"   -> Sent {count} alerts. Distribution: {sent_counts}")
            
            # 3. Frequency
            # 0.5s is very fast. 200 msgs * 2 Hz = 400 msg/s. Acceptable.
            await asyncio.sleep(poll_interval)
            
    except asyncio.CancelledError:
        logger.info("Data Producer Task Cancelled.")
    except Exception as e:
        logger.error(f"Error in Producer: {e}")
