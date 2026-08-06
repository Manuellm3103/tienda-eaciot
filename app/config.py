from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Tienda Eaciot"
    app_secret_key: str = "change-me"
    frontend_url: str = "http://localhost:8000"
    debug: bool = False
    
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/tienda_eaciot"
    
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_mode: str = "sandbox"
    
    upload_dir: str = "./uploads"
    max_file_size: int = 104857600
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
