import asyncio
import logging
from backend.app.services.mock_source import MockDataSource
from backend.app.services.monitor import MarketMonitor
from backend.app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

async def run_mock_producer():
    """
    Background task to generate mock data and publish to Redis.
    """
    logger.info("Starting Mock Data Producer Task...")
    
    # Initialize
    source = MockDataSource(stock_count=4000)
    monitor = MarketMonitor()
    
    # Check if monitor has redis, otherwise this whole thing is local print only
    redis_available = monitor.redis_client is not None
    if not redis_available:
        logger.warning("Monitor has no Redis connection. Switching to IN-MEMORY DIRECT BROADCAST for Dev Mode.")

    try:
        while True:
            # 1. Get Data
            snapshot = source.get_snapshot()
            
            # 2. Process
            # Note: detect_anomalies is synchronous (CPU bound). 
            # In high-perf, run in threadpool. For mock, direct call is acceptable or use to_thread.
            alerts = await asyncio.to_thread(monitor.detect_anomalies, snapshot)
            
            if alerts:
                logger.info(f"Generated {len(alerts)} alerts")
                
                # FALLBACK: If Redis is down, inject directly to WS Manager so frontend works
                if not redis_available:
                    for alert in alerts:
                        await manager.broadcast(alert.model_dump_json())
            
            # 3. Frequency (3 seconds)
            await asyncio.sleep(3)
            
    except asyncio.CancelledError:
        logger.info("Mock Producer Task Cancelled.")
    except Exception as e:
        logger.error(f"Error in Mock Producer: {e}")
