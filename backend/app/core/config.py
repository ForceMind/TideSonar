from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_CHANNEL: str = "stock_alerts"
    
    # Biying API
    BIYING_LICENSE: str = "YOUR_LICENSE_KEY_HERE"
    
    # App Config
    BACKEND_PORT: int = 8000
    
    class Config:
        env_file = ".env"
        extra = "ignore" # Allow extra env vars

settings = Settings()
