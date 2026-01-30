import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import ws
from backend.app.services.redis_listener import redis_listener
from backend.app.services.producer_task import run_mock_producer

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TideSonar")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background tasks
    redis_task = asyncio.create_task(redis_listener())
    producer_task = asyncio.create_task(run_mock_producer())
    
    yield
    
    # Shutdown: Clean up
    producer_task.cancel()
    redis_task.cancel()
    try:
        await producer_task
        await redis_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="GuanChao TideSonar", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ws.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "GuanChao Backend"}

if __name__ == "__main__":
    # Ensure License Key is present
    import os
    env_key = os.getenv("BIYING_LICENSE")
    if not env_key or "YOUR_LICENSE" in env_key:
        print("----------------------------------------------------------------")
        print("SECURITY NOTICE: License Key not found in .env (or is default).")
        print("Please enter your Biying License Key temporarily for this session.")
        print("----------------------------------------------------------------")
        manual_key = input("Enter License Key: ").strip()
        if manual_key:
            os.environ["BIYING_LICENSE"] = manual_key
            # IMPORTANT: Reload settings to pick up the new env var
            from backend.app.core import config
            from importlib import reload
            reload(config)
            # Re-import dependencies that might have cached the old settings
            from backend.app.services import biying_source
            reload(biying_source)
            from backend.app.services import producer_task
            reload(producer_task)
            
            print(f"✅ License Key set temporarily: {manual_key[:8]}******")
        else:
            print("❌ No key entered. Using default (MOCK MODE might be active).")
    
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
    import os
    from backend.app.core.config import settings
    
    # Allow Port override via Env Var (e.g. for Server deployment)
    port = int(os.getenv("BACKEND_PORT", settings.BACKEND_PORT))
    logger.info(f"Starting Backend on Port {port}")
    
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
