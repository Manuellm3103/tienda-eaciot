from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "Tienda Eaciot"
    app_secret_key: str = "change-me"
    frontend_url: str = "http://localhost:8000"
    debug: bool = False
    force_https: bool = False
    allowed_hosts: str = "*"
    
    database_url: str = "sqlite+aiosqlite:///./app.db"
    
    @field_validator('database_url', mode='before')
    def force_sqlite_in_production(cls, v):
        # Forzar SQLite para evitar problemas de conexión con PostgreSQL en Render/Supabase
        if v and isinstance(v, str) and ('postgresql' in v or 'postgres' in v):
            return "sqlite+aiosqlite:///./app.db"
        return v
    
    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]
    
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    
    # SMTP Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@eaciot.com"
    smtp_tls: bool = True
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    # Microsoft OAuth
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/auth/microsoft/callback"
    
    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    
    # Upload
    upload_dir: str = "./uploads"
    max_file_size: int = 104857600
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
