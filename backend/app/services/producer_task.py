import asyncio
import logging
from backend.app.services.mock_source import MockDataSource
from backend.app.services.biying_source import BiyingDataSource
from backend.app.services.monitor import MarketMonitor
from backend.app.services.websocket_manager import manager
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

async def run_mock_producer():
    """
    Background task to generate/fetch data and publish to Redis.
    """
    logger.info("Starting Data Producer Task...")
    
    # Check Redis availability (Mocking status for now as standalone)
    redis_available = False
    
    # Switch between Mock and Real based on Config/License
    if settings.BIYING_LICENSE and settings.BIYING_LICENSE != "YOUR_LICENSE_KEY_HERE" and settings.BIYING_LICENSE != "YOUR_LICENSE_KEY":
        logger.info("Using REAL DATA SOURCE (BiyingAPI)")
        source = BiyingDataSource()
        # Frequency for Real API
        # We use batch API which is efficient.
        # Running every 5 seconds is good balance for "RealTime" vs "Resource Usage"
        poll_interval = 5
    else:
        logger.info("Using MOCK DATA SOURCE")
        source = MockDataSource(stock_count=4000)
        poll_interval = 3

    monitor = MarketMonitor()

    try:
        while True:
            # 1. Get Data
            # source.get_real_time_data is blocking (requests), so run in thread to avoid freezing loop
            if hasattr(source, 'get_real_time_data'):
                 snapshot = await asyncio.to_thread(source.get_real_time_data)
            else:
                 snapshot = await asyncio.to_thread(source.get_snapshot)
            
            # 2. Process
            # detect_anomalies is also CPU bound
            # In high-perf, run in threadpool. For mock, direct call is acceptable or use to_thread.
            alerts = await asyncio.to_thread(monitor.detect_anomalies, snapshot)
            
            if alerts:
                logger.info(f"Generated {len(alerts)} alerts")
                
                # FALLBACK: If Redis is down, inject directly to WS Manager so frontend works
                if not redis_available:
                     # Optimization: Sending 2000 messages individually will crash the browser/network loop.
                     # Broadcst only top 50 alerts or switch to sending a list if frontend supports it.
                     # For now, let's limit to top 50 to see if it fixes "frontend empty"
                     
                    limit = 50
                    count = 0 
                    for alert in alerts:
                        await manager.broadcast(alert.model_dump_json())
                        count += 1
                        if count >= limit:
                             break
                    
                    if len(alerts) > limit:
                        logger.info(f"   (Broadcasted top {limit} alerts to frontend)")
            
            # 3. Frequency
            await asyncio.sleep(poll_interval)
            
    except asyncio.CancelledError:
        logger.info("Data Producer Task Cancelled.")
    except Exception as e:
        logger.error(f"Error in Producer: {e}")
