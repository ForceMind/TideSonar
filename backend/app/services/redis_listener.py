import asyncio
import json
import logging
import redis.asyncio as redis
from backend.app.core.config import settings
from backend.app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

async def redis_listener():
    """
    Connect to Redis Pub/Sub and broadcast messages to WebSockets.
    """
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        async with r.pubsub() as pubsub:
            await pubsub.subscribe(settings.REDIS_CHANNEL)
            logger.info(f"Subscribed to Redis channel: {settings.REDIS_CHANNEL}")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    # Log for debug
                    # logger.info(f"Received from Redis: {data[:50]}...") 
                    await manager.broadcast(data)
                    
    except Exception as e:
        logger.error(f"Redis Listener Error: {e}")
        # Retry logic could go here, but for now we just log
        await asyncio.sleep(5)
