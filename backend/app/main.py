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
    from backend.app.core.config import settings
    masked_key = settings.BIYING_LICENSE[:5] + "***" if settings.BIYING_LICENSE and "YOUR_LICENSE" not in settings.BIYING_LICENSE else "DEFAULT/MOCK"
    logger.info(f"🚀 Server Starting. License Status: {masked_key}")

    # NEW: Schedule Daily History Update (After Market Close)
    # We create a simple loop that checks time, or trigger it manually via API.
    # For now, we will add a trivial check loop or just expose an endpoint.
    # A background loop checking for 15:30 is best.
    from backend.app.services.history_scheduler import start_scheduler
    scheduler_task = asyncio.create_task(start_scheduler())

    redis_task = asyncio.create_task(redis_listener())
    producer_task = asyncio.create_task(run_mock_producer())
    
    yield
    
    # Shutdown: Clean up
    scheduler_task.cancel()
    producer_task.cancel()
    redis_task.cancel()
    try:
        await producer_task
        await scheduler_task
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
    import os
    import uvicorn
    from backend.app.core.config import settings

    # 1. Interactive License Input (Security Best Practice)
    # Check if key is missing or is the default placeholder
    env_key = os.getenv("BIYING_LICENSE")
    if not env_key or "YOUR_LICENSE" in env_key:
        print("----------------------------------------------------------------")
        print("SECURITY NOTICE: License Key not found in .env (or is default).")
        print("Please enter your Biying License Key temporarily for this session.")
        print("----------------------------------------------------------------")
        try:
            manual_key = input("Enter License Key: ").strip()
            if manual_key:
                # Set in environment so child processes (spawned by uvicorn) inherit it
                os.environ["BIYING_LICENSE"] = manual_key
                print(f"✅ License Key set temporarily for subprocesses.")
            else:
                print("❌ No key entered. Using default (MOCK MODE might be active).")
        except (EOFError, OSError):
            print("⚠️  Non-interactive mode detected. Skipping input.")

    # 2. Port Configuration
    # Allow Port override via Env Var (e.g. for Server deployment)
    port = int(os.getenv("BACKEND_PORT", settings.BACKEND_PORT))
    logger.info(f"Starting Backend on Port {port}")
    
    # 3. Start Uvicorn
    # Use reload=True for development. Spawned process will inherit os.environ["BIYING_LICENSE"]
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)


