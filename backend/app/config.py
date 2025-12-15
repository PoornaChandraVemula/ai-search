"""
Configuration settings for the Grok X Search application.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Grok X Search"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Keys
    XAI_API_KEY: str = ""
    
    # Grok API
    GROK_API_BASE_URL: str = "https://api.x.ai/v1"
    GROK_MODEL: str = "grok-3-latest"
    
    # Database
    DATABASE_URL: str = "sqlite:///./data/xsearch.db"
    
    # Scraping
    SCRAPE_RATE_LIMIT: int = 5  # requests per minute
    SCRAPE_DELAY: float = 2.0  # seconds between requests
    MAX_POSTS_PER_ACCOUNT: int = 100
    
    # Search
    MAX_SEARCH_RESULTS: int = 50
    DEFAULT_SEARCH_RESULTS: int = 20
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

