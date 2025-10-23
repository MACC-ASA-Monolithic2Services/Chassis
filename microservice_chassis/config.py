"""Configuration settings for microservices."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    PRIVATE_KEY_PATH: str
    PUBLIC_KEY_PATH: str
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


settings = Settings()