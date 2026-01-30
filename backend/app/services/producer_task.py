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
            # source.get_real_time_data handles the batching logic internally
            if hasattr(source, 'get_real_time_data'):
                 snapshot = source.get_real_time_data()
            else:
                 snapshot = source.get_snapshot() # Fallback for Mock source
            
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
            
            # 3. Frequency
            await asyncio.sleep(poll_interval)
            
    except asyncio.CancelledError:
        logger.info("Data Producer Task Cancelled.")
    except Exception as e:
        logger.error(f"Error in Producer: {e}")
