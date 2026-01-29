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
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
