from pydantic_settings import BaseSettings
from functools import lru_cache
from pydantic import field_validator, model_validator


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

    @model_validator(mode='after')
    def fail_closed_on_default_secret(self):
        # A default JWT secret lets anyone forge admin tokens. In production
        # (force_https on, as set in render.yaml) refuse to boot until a real
        # APP_SECRET_KEY is set. Local dev/tests keep the placeholder.
        if self.force_https and self.app_secret_key in ("", "change-me"):
            raise ValueError(
                "APP_SECRET_KEY must be set to a strong random value in production. "
                "Generate one with: python scripts/generate_secret.py"
            )
        return self
    
    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]
    
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "ornith:9b"
    # Clave opcional para Ollama Cloud (https://api.ollama.com). Vacía = sin
    # cabecera Authorization (self-hosted / modelos locales).
    ollama_api_key: str = ""

    # OpenCode Go (secondary LLM provider — JSON / code / SQL tasks)
    opencode_host: str = "http://localhost:8080"
    opencode_model: str = "opencode-go"
    opencode_api_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    # CFDI / Facturación electrónica (Facturapi-compatible)
    facturapi_api_key: str = ""
    facturapi_base_url: str = "https://www.facturapi.io/v2"
    business_rfc: str = ""
    business_name: str = ""
    business_tax_regime: str = "601"  # 601 = General de Ley Personas Morales

    # CFDI 4.0 nativo con satcfdi + PAC (sin límite mensual)
    # satcfdi 4.4.7 NO trae conector Finkok; soporta: swsapien, comerciodigital,
    # diverza, prodigia, mysuite. Añadimos 'finkok' como conector SOAP manual.
    pac_provider: str = "finkok"  # finkok | swsapien | comerciodigital
    pac_username: str = ""
    pac_password: str = ""
    pac_environment: str = "production"  # production | test
    csd_cert_path: str = ""       # ruta al archivo .cer del CSD
    csd_key_path: str = ""        # ruta al archivo .key del CSD
    csd_password: str = ""        # contraseña del CSD
    business_zip_code: str = "62410"  # CP del emisor (Cuernavaca, Morelos)
    business_iva_rate: float = 0.16  # tasa de IVA trasladado (0 para exento)
    
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

    # Semantic Search (Meilisearch)
    meilisearch_url: str = "http://localhost:7700"
    meilisearch_api_key: str = ""
    semantic_search_enabled: bool = False

    # Background scheduler (disabled in tests by default)
    scheduler_enabled: bool = True

    # WhatsApp Business API (Cloud API via Meta)
    whatsapp_verify_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
