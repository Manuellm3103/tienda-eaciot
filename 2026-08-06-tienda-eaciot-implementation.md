# Tienda eaciot - Plan de Implementación

> **Para agentes agenticos:** SUB-SKILL REQUERIDO: Usa superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan tarea por tarea. Los pasos usan sint checkbox (`- [ ]`) para seguimiento.

**Goal:** Construir la tienda online completa para tienda.eaciot.com con autenticación Auth0, pagos Stripe/PayPal, fidelización con niveles, y sistema de IA con Ollama para sugerencias.

**Architecture:** Backend FastAPI con SQLAlchemy async, PostgreSQL, Jinja2 templates con Tailwind CSS y HTMX. Auth0 para autenticación, Ollama para IA local.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL 15+, Auth0, Stripe, PayPal, Ollama, Jinja2, Tailwind CSS, HTMX

## Global Constraints

- Python 3.11+ requerido
- PostgreSQL 15+ como base de datos
- Auth0 como proveedor de autenticación (no OAuth directo)
- Ollama corriendo localmente para IA
- Todas las rutas admin requieren rol `is_admin=True`
- IDs como UUIDs en todas las tablas
- Timestamps en UTC
- Respuestas API en formato JSON
- Templates con Jinja2 + Tailwind CSS

---

## Fase 1: Setup del Proyecto

### Task 1: Inicializar proyecto Python y dependencias

**Files:**
- Create: `tienda-eaciot/requirements.txt`
- Create: `tienda-eaciot/.env.example`
- Create: `tienda-eaciot/.gitignore`
- Create: `tienda-eaciot/README.md`

**Interfaces:**
- Produces: Estructura base del proyecto

- [ ] **Step 1: Crear directorio del proyecto**

```bash
mkdir -p C:\Users\Manu\tienda-eaciot
cd C:\Users\Manu\tienda-eaciot
```

- [ ] **Step 2: Crear requirements.txt**

```txt
fastapi==0.110.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.29
asyncpg==0.29.0
alembic==1.13.1
auth0-python==4.7.1
python-jose[cryptography]==3.3.0
httpx==0.27.0
ollama==0.1.8
stripe==8.11.0
paypalhttp==1.0.1
jinja2==3.1.3
python-multipart==0.0.9
pydantic[email]==2.6.4
python-dotenv==1.0.1
pytest==8.1.1
pytest-asyncio==0.23.5
```

- [ ] **Step 3: Crear .env.example**

```env
APP_NAME=Tienda Eaciot
APP_SECRET_KEY=change-me-to-random-secret
FRONTEND_URL=https://tienda.eaciot.com
DEBUG=true

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tienda_eaciot

AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_CALLBACK_URL=https://tienda.eaciot.com/auth/callback
AUTH0_AUDIENCE=https://api.eaciot.com

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3

STRIPE_SECRET_KEY=sk_test_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret
STRIPE_PUBLISHABLE_KEY=pk_test_your-key

PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_MODE=sandbox

UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600
```

- [ ] **Step 4: Crear .gitignore**

```gitignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
.eggs/
*.egg-info/
dist/
build/
uploads/
*.db
.pytest_cache/
.mypy_cache/
```

- [ ] **Step 5: Commit**

```bash
git init
git add .
git commit -m "feat: initialize project with requirements and config"
```

---

### Task 2: Configurar FastAPI y base de datos

**Files:**
- Create: `tienda-eaciot/app/__init__.py`
- Create: `tienda-eaciot/app/config.py`
- Create: `tienda-eaciot/app/database.py`
- Create: `tienda-eaciot/app/main.py`

**Interfaces:**
- Produces: `get_db()` async generator, `settings` object

- [ ] **Step 1: Crear estructura de directorios**

```bash
mkdir -p app/models app/schemas app/routers app/services app/ai app/templates app/static
```

- [ ] **Step 2: Crear app/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Tienda Eaciot"
    app_secret_key: str = "change-me"
    frontend_url: str = "http://localhost:8000"
    debug: bool = False
    
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/tienda_eaciot"
    
    auth0_domain: str = ""
    auth0_client_id: str = ""
    auth0_client_secret: str = ""
    auth0_callback_url: str = ""
    auth0_audience: str = ""
    
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
```

- [ ] **Step 3: Crear app/database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 4: Crear app/main.py**

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import settings
from app.database import init_db


app = FastAPI(title=settings.app_name)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
```

- [ ] **Step 5: Crear app/__init__.py**

```python
```

- [ ] **Step 6: Verificar que la app arranca**

```bash
cd C:\Users\Manu\tienda-eaciot
pip install -r requirements.txt
uvicorn app.main:app --reload
# Debe mostrar: Uvicorn running on http://127.0.0.1:8000
```

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "feat: add FastAPI setup with database config"
```

---

### Task 3: Configurar Docker Compose (PostgreSQL + Ollama)

**Files:**
- Create: `tienda-eaciot/docker-compose.yml`
- Create: `tienda-eaciot/Dockerfile`

**Interfaces:**
- Produces: Servicios PostgreSQL y Ollama corriendo

- [ ] **Step 1: Crear docker-compose.yml**

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: tienda_eaciot
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d tienda_eaciot"]
      interval: 5s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:11434/api/tags || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  postgres_data:
  ollama_data:
```

- [ ] **Step 2: Crear Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Iniciar servicios**

```bash
docker-compose up -d
docker-compose ps  # Verificar que db y ollama están corriendo
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: add Docker Compose for PostgreSQL and Ollama"
```

---

## Fase 2: Modelos de Datos

### Task 4: Crear modelos SQLAlchemy

**Files:**
- Create: `tienda-eaciot/app/models/__init__.py`
- Create: `tienda-eaciot/app/models/user.py`
- Create: `tienda-eaciot/app/models/product.py`
- Create: `tienda-eaciot/app/models/order.py`
- Create: `tienda-eaciot/app/models/loyalty.py`
- Create: `tienda-eaciot/app/models/promotion.py`
- Create: `tienda-eaciot/app/models/congratulation.py`

**Interfaces:**
- Produces: Todos los modelos SQLAlchemy para las tablas de la DB

- [ ] **Step 1: Crear app/models/user.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth0_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(String)
    
    # Fidelización
    loyalty_level = Column(String(20), default="bronce")
    loyalty_points = Column(Integer, default=0)
    total_spent = Column(Numeric(10, 2), default=0.00)
    purchase_count = Column(Integer, default=0)
    last_purchase_at = Column(DateTime)
    
    # IA
    is_fidel = Column(Boolean, default=False)
    fidel_score = Column(Integer, default=0)
    
    # Admin
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Crear app/models/product.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    image_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    
    product_type = Column(String(20), nullable=False)  # ebook, curso, software, template, fisico
    
    image_url = Column(String)
    file_path = Column(String)
    weight = Column(Numeric(8, 2))
    
    is_active = Column(Boolean, default=True)
    stock = Column(Integer, default=-1)
    
    meta_title = Column(String(255))
    meta_description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 3: Crear app/models/order.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    shipping_amount = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    status = Column(String(20), default="pending")
    
    payment_method = Column(String(20))
    payment_id = Column(String(255))
    
    shipping_address = Column(JSON)
    tracking_number = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price_at_purchase = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Crear app/models/loyalty.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class LoyaltyHistory(Base):
    __tablename__ = "loyalty_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    points_change = Column(Integer, nullable=False)
    reason = Column(String(255))
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 5: Crear app/models/promotion.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Promotion(Base):
    __tablename__ = "promotions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    
    conditions = Column(JSON)
    
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    coupon_code = Column(String(50), unique=True)
    auto_generate_coupons = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    
    ai_suggestion = Column(JSON)
    
    usage_count = Column(Integer, default=0)
    max_uses = Column(Integer, default=-1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Coupon(Base):
    __tablename__ = "coupons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    
    promotion_id = Column(UUID(as_uuid=True), ForeignKey("promotions.id"))
    congratulation_rule_id = Column(UUID(as_uuid=True), ForeignKey("congratulation_rules.id"))
    
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    used_in_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 6: Crear app/models/congratulation.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class CongratulationRule(Base):
    __tablename__ = "congratulation_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    event_type = Column(String(50), nullable=False)
    event_value = Column(Numeric(10, 2))
    event_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    reward_type = Column(String(30), nullable=False)
    reward_value = Column(Numeric(10, 2))
    reward_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    
    message_template = Column(Text, nullable=False)
    email_subject = Column(String(255))
    
    is_active = Column(Boolean, default=True)
    max_uses = Column(Integer, default=-1)
    current_uses = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CongratulationHistory(Base):
    __tablename__ = "congratulation_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("congratulation_rules.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    
    message_sent = Column(Text)
    reward_sent = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 7: Crear app/models/__init__.py**

```python
from app.models.user import User
from app.models.product import Category, Product
from app.models.order import Order, OrderItem
from app.models.loyalty import LoyaltyHistory
from app.models.promotion import Promotion, Coupon
from app.models.congratulation import CongratulationRule, CongratulationHistory

__all__ = [
    "User",
    "Category",
    "Product",
    "Order",
    "OrderItem",
    "LoyaltyHistory",
    "Promotion",
    "Coupon",
    "CongratulationRule",
    "CongratulationHistory",
]
```

- [ ] **Step 8: Verificar que los modelos se crean**

```bash
python -c "from app.models import *; print('Models imported successfully')"
```

- [ ] **Step 9: Commit**

```bash
git add .
git commit -m "feat: add all SQLAlchemy models"
```

---

### Task 5: Configurar Alembic para migraciones

**Files:**
- Create: `tienda-eaciot/alembic.ini`
- Create: `tienda-eaciot/alembic/env.py`
- Create: `tienda-eaciot/alembic/script.py.mako`

**Interfaces:**
- Produces: Sistema de migraciones funcionando

- [ ] **Step 1: Inicializar Alembic**

```bash
cd C:\Users\Manu\tienda-eaciot
alembic init alembic
```

- [ ] **Step 2: Actualizar alembic/env.py**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.database import Base
from app.models import *  # Import all models
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Crear migración inicial**

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: configure Alembic migrations"
```

---

## Fase 3: Autenticación Auth0

### Task 6: Implementar servicio Auth0

**Files:**
- Create: `tienda-eaciot/app/services/auth0_service.py`
- Create: `tienda-eaciot/app/routers/auth.py`

**Interfaces:**
- Produces: `auth0_service` con métodos `get_login_url()`, `callback()`, `get_user_info()`

- [ ] **Step 1: Crear app/services/auth0_service.py**

```python
from auth0.authentication import GetToken
from auth0.authentication import Users
from auth0.management import Auth0 as Auth0Management
from app.config import settings
import httpx


class Auth0Service:
    def __init__(self):
        self.domain = settings.auth0_domain
        self.client_id = settings.auth0_client_id
        self.client_secret = settings.auth0_client_secret
        self.callback_url = settings.auth0_callback_url
        self.audience = settings.auth0_audience
    
    def get_login_url(self, state: str = "/") -> str:
        return (
            f"https://{self.domain}/authorize?"
            f"response_type=code&"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.callback_url}&"
            f"scope=openid profile email&"
            f"audience={self.audience}&"
            f"state={state}"
        )
    
    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{self.domain}/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.callback_url,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{self.domain}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    def get_logout_url(self, return_to: str = "/") -> str:
        return (
            f"https://{self.domain}/v2/logout?"
            f"client_id={self.client_id}&"
            f"returnTo={return_to}"
        )


auth0_service = Auth0Service()
```

- [ ] **Step 2: Crear app/routers/auth.py**

```python
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.services.auth0_service import auth0_service
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    state = request.query_params.get("next", "/")
    return RedirectResponse(auth0_service.get_login_url(state))


@router.get("/callback")
async def callback(code: str, state: str = "/", db: AsyncSession = Depends(get_db)):
    try:
        token_data = await auth0_service.exchange_code(code)
        user_info = await auth0_service.get_user_info(token_data["access_token"])
        
        # Find or create user
        result = await db.execute(select(User).where(User.auth0_id == user_info["sub"]))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                auth0_id=user_info["sub"],
                email=user_info["email"],
                name=user_info.get("name"),
                picture=user_info.get("picture"),
            )
            db.add(user)
            await db.flush()
        
        # Set cookie with user ID (simplified - use JWT in production)
        response = RedirectResponse(state)
        response.set_cookie("user_id", str(user.id), httponly=True, secure=True)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logout")
async def logout():
    response = RedirectResponse(auth0_service.get_logout_url())
    response.delete_cookie("user_id")
    return response


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "loyalty_level": user.loyalty_level,
        "loyalty_points": user.loyalty_points,
        "total_spent": float(user.total_spent),
    }
```

- [ ] **Step 3: Registrar router en main.py**

```python
from app.routers import auth

app.include_router(auth.router)
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: implement Auth0 authentication"
```

---

## Fase 4: Productos y Catálogo

### Task 7: Implementar CRUD de productos

**Files:**
- Create: `tienda-eaciot/app/schemas/product.py`
- Create: `tienda-eaciot/app/services/product_service.py`
- Create: `tienda-eaciot/app/routers/products.py`
- Create: `tienda-eaciot/app/routers/admin_products.py`

**Interfaces:**
- Produces: `product_service` con métodos CRUD
- Produces: Rutas `/products` y `/admin/products`

- [ ] **Step 1: Crear app/schemas/product.py**

```python
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID
    is_active: bool
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: Decimal = Field(gt=0)
    category_id: Optional[UUID] = None
    product_type: str = Field(pattern="^(ebook|curso|software|template|fisico)$")
    image_url: Optional[str] = None
    stock: int = -1


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    category_id: Optional[UUID] = None
    product_type: Optional[str] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: UUID
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: Crear app/services/product_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.models.product import Product, Category
from app.schemas.product import ProductCreate, ProductUpdate, CategoryCreate


class ProductService:
    async def get_products(
        self, db: AsyncSession, category_id: Optional[UUID] = None, active_only: bool = True
    ) -> List[Product]:
        query = select(Product)
        if active_only:
            query = query.where(Product.is_active == True)
        if category_id:
            query = query.where(Product.category_id == category_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_product(self, db: AsyncSession, product_id: UUID) -> Optional[Product]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()
    
    async def create_product(self, db: AsyncSession, data: ProductCreate) -> Product:
        product = Product(**data.model_dump())
        db.add(product)
        await db.flush()
        return product
    
    async def update_product(self, db: AsyncSession, product_id: UUID, data: ProductUpdate) -> Optional[Product]:
        product = await self.get_product(db, product_id)
        if not product:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        await db.flush()
        return product
    
    async def delete_product(self, db: AsyncSession, product_id: UUID) -> bool:
        product = await self.get_product(db, product_id)
        if not product:
            return False
        product.is_active = False
        await db.flush()
        return True
    
    async def get_categories(self, db: AsyncSession) -> List[Category]:
        result = await db.execute(select(Category).where(Category.is_active == True))
        return result.scalars().all()
    
    async def create_category(self, db: AsyncSession, data: CategoryCreate) -> Category:
        category = Category(**data.model_dump())
        db.add(category)
        await db.flush()
        return category


product_service = ProductService()
```

- [ ] **Step 3: Crear app/routers/products.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.schemas.product import ProductResponse, CategoryResponse
from app.services.product_service import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductResponse])
async def list_products(category_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await product_service.get_products(db, category_id)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/categories/", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await product_service.get_categories(db)
```

- [ ] **Step 4: Crear app/routers/admin_products.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, CategoryCreate, CategoryResponse
from app.services.product_service import product_service

router = APIRouter(prefix="/admin/products", tags=["admin-products"])


@router.post("/", response_model=ProductResponse)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    return await product_service.create_product(db, data)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await product_service.update_product(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}")
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    success = await product_service.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}


@router.post("/categories/", response_model=CategoryResponse)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return await product_service.create_category(db, data)
```

- [ ] **Step 5: Registrar routers en main.py**

```python
from app.routers import auth, products, admin_products

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin_products.router)
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: implement product CRUD with categories"
```

---

## Fase 5: Órdenes y Carrito

### Task 8: Implementar sistema de órdenes

**Files:**
- Create: `tienda-eaciot/app/schemas/order.py`
- Create: `tienda-eaciot/app/services/order_service.py`
- Create: `tienda-eaciot/app/routers/orders.py`

**Interfaces:**
- Produces: `order_service` con métodos para crear y gestionar órdenes
- Produces: Rutas `/orders`

- [ ] **Step 1: Crear app/schemas/order.py**

```python
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = 1


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    coupon_code: Optional[str] = None
    shipping_address: Optional[dict] = None


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    price_at_purchase: Decimal
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    status: str
    payment_method: Optional[str]
    items: List[OrderItemResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: Crear app/services/order_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate


class OrderService:
    async def create_order(self, db: AsyncSession, user_id: UUID, data: OrderCreate) -> Order:
        # Get products and calculate totals
        items_data = []
        subtotal = Decimal("0")
        
        for item in data.items:
            product = await db.get(Product, item.product_id)
            if not product or not product.is_active:
                raise ValueError(f"Product {item.product_id} not found or inactive")
            
            item_total = product.price * item.quantity
            subtotal += item_total
            items_data.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "price_at_purchase": product.price,
            })
        
        # Create order
        order = Order(
            user_id=user_id,
            subtotal=subtotal,
            total_amount=subtotal,  # Will be updated with discounts/shipping
            shipping_address=data.shipping_address,
        )
        db.add(order)
        await db.flush()
        
        # Create order items
        for item_data in items_data:
            order_item = OrderItem(order_id=order.id, **item_data)
            db.add(order_item)
        
        await db.flush()
        return order
    
    async def get_user_orders(self, db: AsyncSession, user_id: UUID) -> List[Order]:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_order(self, db: AsyncSession, order_id: UUID) -> Optional[Order]:
        result = await db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()
    
    async def update_order_status(self, db: AsyncSession, order_id: UUID, status: str) -> Optional[Order]:
        order = await self.get_order(db, order_id)
        if not order:
            return None
        order.status = status
        await db.flush()
        return order


order_service = OrderService()
```

- [ ] **Step 3: Crear app/routers/orders.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse)
async def create_order(data: OrderCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        return await order_service.create_order(db, UUID(user_id), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[OrderResponse])
async def list_orders(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await order_service.get_user_orders(db, UUID(user_id))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    order = await order_service.get_order(db, order_id)
    if not order or str(order.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order
```

- [ ] **Step 4: Registrar router en main.py**

```python
from app.routers import auth, products, admin_products, orders

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin_products.router)
app.include_router(orders.router)
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat: implement order system"
```

---

## Fase 6: Pagos

### Task 9: Implementar pagos con Stripe

**Files:**
- Create: `tienda-eaciot/app/services/stripe_service.py`
- Create: `tienda-eaciot/app/routers/payments.py`

**Interfaces:**
- Produces: `stripe_service` con métodos para crear sesiones y procesar webhooks
- Produces: Rutas `/payments`

- [ ] **Step 1: Crear app/services/stripe_service.py**

```python
import stripe
from app.config import settings
from app.models.order import Order

stripe.api_key = settings.stripe_secret_key


class StripeService:
    async def create_checkout_session(self, order: Order, success_url: str, cancel_url: str) -> dict:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "mxn",
                        "product_data": {
                            "name": f"Orden #{str(order.id)[:8]}",
                        },
                        "unit_amount": int(order.total_amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"order_id": str(order.id)},
        )
        return {"session_id": session.id, "url": session.url}
    
    def verify_webhook(self, payload: bytes, sig_header: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")


stripe_service = StripeService()
```

- [ ] **Step 2: Crear app/routers/payments.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.stripe_service import stripe_service
from app.services.order_service import order_service
from app.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/stripe/create")
async def create_stripe_session(order_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    success_url = f"{settings.frontend_url}/checkout/success?order_id={order_id}"
    cancel_url = f"{settings.frontend_url}/checkout/cancel"
    
    result = await stripe_service.create_checkout_session(order, success_url, cancel_url)
    return result


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe_service.verify_webhook(payload, sig_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"]["order_id"]
        await order_service.update_order_status(db, order_id, "paid")
    
    return {"status": "success"}
```

- [ ] **Step 3: Registrar router en main.py**

```python
from app.routers import auth, products, admin_products, orders, payments

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin_products.router)
app.include_router(orders.router)
app.include_router(payments.router)
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: implement Stripe payment integration"
```

---

## Fase 7: Fidelización

### Task 10: Implementar sistema de fidelización

**Files:**
- Create: `tienda-eaciot/app/services/loyalty_service.py`
- Create: `tienda-eaciot/app/routers/loyalty.py`

**Interfaces:**
- Produces: `loyalty_service` con métodos para calcular niveles y puntos
- Produces: Rutas `/loyalty`

- [ ] **Step 1: Crear app/services/loyalty_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from decimal import Decimal
from app.models.user import User
from app.models.loyalty import LoyaltyHistory


class LoyaltyService:
    LEVELS = {
        "bronce": {"min": 0, "max": 499, "discount": 5},
        "plata": {"min": 500, "max": 1499, "discount": 10},
        "oro": {"min": 1500, "max": 4999, "discount": 15},
        "diamante": {"min": 5000, "max": float("inf"), "discount": 20},
    }
    
    def calculate_level(self, total_spent: Decimal) -> str:
        spent = float(total_spent)
        if spent >= 5000:
            return "diamante"
        elif spent >= 1500:
            return "oro"
        elif spent >= 500:
            return "plata"
        return "bronce"
    
    def get_discount(self, level: str) -> int:
        return self.LEVELS.get(level, {}).get("discount", 0)
    
    async def update_user_loyalty(
        self, db: AsyncSession, user_id: UUID, order_total: Decimal, order_id: UUID
    ) -> dict:
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        old_level = user.loyalty_level
        user.total_spent += order_total
        user.purchase_count += 1
        user.loyalty_points += int(order_total)
        user.last_purchase_at = func.now()
        
        new_level = self.calculate_level(user.total_spent)
        user.loyalty_level = new_level
        
        # Record history
        history = LoyaltyHistory(
            user_id=user_id,
            points_change=int(order_total),
            reason=f"Purchase order #{str(order_id)[:8]}",
            order_id=order_id,
        )
        db.add(history)
        
        await db.flush()
        
        return {
            "old_level": old_level,
            "new_level": new_level,
            "level_up": old_level != new_level,
            "points_earned": int(order_total),
            "total_points": user.loyalty_points,
        }
    
    async def get_user_loyalty(self, db: AsyncSession, user_id: UUID) -> dict:
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        return {
            "level": user.loyalty_level,
            "points": user.loyalty_points,
            "total_spent": float(user.total_spent),
            "purchase_count": user.purchase_count,
            "discount": self.get_discount(user.loyalty_level),
            "next_level": self._get_next_level(user.loyalty_level),
            "points_to_next": self._get_points_to_next(user.loyalty_level, user.total_spent),
        }
    
    def _get_next_level(self, current: str) -> str:
        levels = ["bronce", "plata", "oro", "diamante"]
        idx = levels.index(current)
        return levels[min(idx + 1, len(levels) - 1)]
    
    def _get_points_to_next(self, current: str, total_spent: Decimal) -> int:
        thresholds = {"bronce": 500, "plata": 1500, "oro": 5000}
        next_threshold = thresholds.get(current)
        if not next_threshold:
            return 0
        return max(0, next_threshold - int(total_spent))
    
    async def get_loyalty_history(self, db: AsyncSession, user_id: UUID) -> List[LoyaltyHistory]:
        result = await db.execute(
            select(LoyaltyHistory)
            .where(LoyaltyHistory.user_id == user_id)
            .order_by(LoyaltyHistory.created_at.desc())
        )
        return result.scalars().all()


loyalty_service = LoyaltyService()
```

- [ ] **Step 2: Crear app/routers/loyalty.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.services.loyalty_service import loyalty_service

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/status")
async def get_loyalty_status(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        return await loyalty_service.get_user_loyalty(db, UUID(user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
async def get_loyalty_history(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await loyalty_service.get_loyalty_history(db, UUID(user_id))
```

- [ ] **Step 3: Registrar router en main.py**

```python
from app.routers import auth, products, admin_products, orders, payments, loyalty

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin_products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(loyalty.router)
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: implement loyalty system with levels"
```

---

## Fase 8: Promociones y Felicitaciones

### Task 11: Implementar sistema de promociones

**Files:**
- Create: `tienda-eaciot/app/schemas/promotion.py`
- Create: `tienda-eaciot/app/services/promotion_service.py`
- Create: `tienda-eaciot/app/routers/promotions.py`
- Create: `tienda-eaciot/app/routers/admin_promotions.py`

**Interfaces:**
- Produces: `promotion_service` con métodos CRUD y aplicación de cupones
- Produces: Rutas `/promotions` y `/admin/promotions`

- [ ] **Step 1: Crear app/schemas/promotion.py**

```python
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class PromotionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    discount_type: str  # percentage, fixed, free_shipping
    discount_value: Decimal
    conditions: Optional[dict] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    coupon_code: Optional[str] = None


class PromotionResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    discount_type: str
    discount_value: Decimal
    is_active: bool
    is_approved: bool
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CongratulationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str  # total_spent, purchase_count, specific_product, loyalty_level_up
    event_value: Optional[Decimal] = None
    event_product_id: Optional[UUID] = None
    reward_type: str  # coupon, free_product, points, free_shipping
    reward_value: Optional[Decimal] = None
    reward_product_id: Optional[UUID] = None
    message_template: str
    email_subject: Optional[str] = None


class CongratulationRuleResponse(BaseModel):
    id: UUID
    name: str
    event_type: str
    reward_type: str
    is_active: bool
    current_uses: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: Crear app/services/promotion_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.models.promotion import Promotion, Coupon
from app.models.congratulation import CongratulationRule, CongratulationHistory
from app.models.user import User
from app.schemas.promotion import PromotionCreate, CongratulationRuleCreate
import secrets


class PromotionService:
    async def create_promotion(self, db: AsyncSession, data: PromotionCreate) -> Promotion:
        promotion = Promotion(**data.model_dump())
        db.add(promotion)
        await db.flush()
        return promotion
    
    async def get_promotions(self, db: AsyncSession, active_only: bool = True) -> List[Promotion]:
        query = select(Promotion)
        if active_only:
            query = query.where(Promotion.is_active == True, Promotion.is_approved == True)
        result = await db.execute(query.order_by(Promotion.created_at.desc()))
        return result.scalars().all()
    
    async def approve_promotion(self, db: AsyncSession, promotion_id: UUID) -> Optional[Promotion]:
        result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
        promotion = result.scalar_one_or_none()
        if not promotion:
            return None
        promotion.is_approved = True
        await db.flush()
        return promotion
    
    async def apply_coupon(self, db: AsyncSession, code: str, user_id: UUID, order_total: float) -> dict:
        result = await db.execute(select(Coupon).where(Coupon.code == code, Coupon.is_used == False))
        coupon = result.scalar_one_or_none()
        
        if not coupon:
            return {"valid": False, "error": "Coupon not found or already used"}
        
        if coupon.user_id and coupon.user_id != user_id:
            return {"valid": False, "error": "Coupon not valid for this user"}
        
        if coupon.expires_at and coupon.expires_at < datetime.utcnow():
            return {"valid": False, "error": "Coupon expired"}
        
        # Get promotion details
        promo = await db.get(Promotion, coupon.promotion_id)
        if not promo or not promo.is_active:
            return {"valid": False, "error": "Promotion no longer active"}
        
        # Calculate discount
        if promo.discount_type == "percentage":
            discount = order_total * (float(promo.discount_value) / 100)
        elif promo.discount_type == "fixed":
            discount = min(float(promo.discount_value), order_total)
        else:
            discount = 0
        
        return {
            "valid": True,
            "discount": discount,
            "coupon_id": str(coupon.id),
            "promotion_id": str(promo.id),
        }
    
    async def create_congratulation_rule(self, db: AsyncSession, data: CongratulationRuleCreate) -> CongratulationRule:
        rule = CongratulationRule(**data.model_dump())
        db.add(rule)
        await db.flush()
        return rule
    
    async def get_congratulation_rules(self, db: AsyncSession) -> List[CongratulationRule]:
        result = await db.execute(
            select(CongratulationRule).where(CongratulationRule.is_active == True)
        )
        return result.scalars().all()
    
    async def check_congratulation_rules(self, db: AsyncSession, user: User, order_id: UUID) -> List[dict]:
        triggered = []
        rules = await self.get_congratulation_rules(db)
        
        for rule in rules:
            should_trigger = False
            
            if rule.event_type == "total_spent" and float(user.total_spent) >= float(rule.event_value):
                should_trigger = True
            elif rule.event_type == "purchase_count" and user.purchase_count >= int(rule.event_value):
                should_trigger = True
            elif rule.event_type == "loyalty_level_up" and user.loyalty_level == rule.event_value:
                should_trigger = True
            
            if should_trigger:
                triggered.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "message": rule.message_template,
                    "reward_type": rule.reward_type,
                    "reward_value": float(rule.reward_value) if rule.reward_value else None,
                })
                
                # Record history
                history = CongratulationHistory(
                    user_id=user.id,
                    rule_id=rule.id,
                    order_id=order_id,
                    message_sent=rule.message_template,
                    reward_sent=f"{rule.reward_type}: {rule.reward_value}",
                )
                db.add(history)
                rule.current_uses += 1
        
        await db.flush()
        return triggered


promotion_service = PromotionService()
```

- [ ] **Step 3: Crear app/routers/promotions.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.services.promotion_service import promotion_service

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("/")
async def list_promotions(db: AsyncSession = Depends(get_db)):
    return await promotion_service.get_promotions(db)


@router.post("/apply")
async def apply_coupon(code: str, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # TODO: Get order total from cart/session
    order_total = 100.0  # Placeholder
    
    result = await promotion_service.apply_coupon(db, code, UUID(user_id), order_total)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
```

- [ ] **Step 4: Crear app/routers/admin_promotions.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.schemas.promotion import PromotionCreate, PromotionResponse, CongratulationRuleCreate, CongratulationRuleResponse
from app.services.promotion_service import promotion_service

router = APIRouter(prefix="/admin/promotions", tags=["admin-promotions"])


@router.post("/", response_model=PromotionResponse)
async def create_promotion(data: PromotionCreate, db: AsyncSession = Depends(get_db)):
    return await promotion_service.create_promotion(db, data)


@router.post("/{promotion_id}/approve", response_model=PromotionResponse)
async def approve_promotion(promotion_id: UUID, db: AsyncSession = Depends(get_db)):
    promotion = await promotion_service.approve_promotion(db, promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promotion


@router.post("/congratulations/rules/", response_model=CongratulationRuleResponse)
async def create_congratulation_rule(data: CongratulationRuleCreate, db: AsyncSession = Depends(get_db)):
    return await promotion_service.create_congratulation_rule(db, data)


@router.get("/congratulations/rules/")
async def list_congratulation_rules(db: AsyncSession = Depends(get_db)):
    return await promotion_service.get_congratulation_rules(db)
```

- [ ] **Step 5: Registrar routers en main.py**

```python
from app.routers import auth, products, admin_products, orders, payments, loyalty, promotions, admin_promotions

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin_products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(loyalty.router)
app.include_router(promotions.router)
app.include_router(admin_promotions.router)
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: implement promotions and congratulation rules"
```

---

## Fase 9: Motor de IA (Ollama)

### Task 12: Implementar integración con Ollama

**Files:**
- Create: `tienda-eaciot/app/ai/__init__.py`
- Create: `tienda-eaciot/app/ai/ollama_client.py`
- Create: `tienda-eaciot/app/ai/customer_analyzer.py`
- Create: `tienda-eaciot/app/ai/promotion_generator.py`
- Create: `tienda-eaciot/app/ai/welcome_generator.py`

**Interfaces:**
- Produces: `customer_analyzer`, `promotion_generator`, `welcome_generator`
- Consumes: Ollama API en `http://localhost:11434`

- [ ] **Step 1: Crear app/ai/ollama_client.py**

```python
import httpx
from app.config import settings


class OllamaClient:
    def __init__(self):
        self.host = settings.ollama_host
        self.model = settings.ollama_model
    
    async def generate(self, prompt: str, system: str = "") -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]
    
    async def chat(self, messages: list) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]


ollama_client = OllamaClient()
```

- [ ] **Step 2: Crear app/ai/customer_analyzer.py**

```python
from app.ai.ollama_client import ollama_client
from typing import List, Dict
import json


class CustomerAnalyzer:
    async def analyze_customer(self, customer_data: dict) -> dict:
        system = """Eres un analista de clientes de e-commerce. 
Analiza los datos del cliente y proporciona:
1. Score RFM (Recency, Frequency, Monetary) del 0-100
2. Segmento (nuevo, frecuente, fiel, en riesgo, perdido)
3. Recomendación de acción
Responde en JSON."""
        
        prompt = f"""Datos del cliente:
- Total gastado: ${customer_data['total_spent']}
- Compras realizadas: {customer_data['purchase_count']}
- Última compra: {customer_data.get('last_purchase', 'N/A')}
- Nivel actual: {customer_data['loyalty_level']}
- Productos comprados: {customer_data.get('products', [])}

Analiza este cliente y responde en JSON con:
{{
    "fidel_score": <0-100>,
    "segment": "<segmento>",
    "recommendation": "<acción sugerida>",
    "risk_level": "<bajo/medio/alto>"
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {
                "fidel_score": 50,
                "segment": "unknown",
                "recommendation": "Manual review needed",
                "risk_level": "medium",
            }
    
    async def identify_fidel_customers(self, customers: List[dict]) -> List[dict]:
        system = """Identifica los clientes más fieles de esta lista.
Criterios: frecuencia de compra, monto total, recencia.
Devuelve los top 10 con justificación."""
        
        prompt = f"""Clientes:
{json.dumps(customers[:50], indent=2)}

Identifica los top 10 clientes más fieles y responde en JSON:
{{
    "fidel_customers": [
        {{"user_id": "<id>", "reason": "<por qué es fiel>", "suggested_reward": "<recompensa sugerida>"}}
    ]
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response).get("fidel_customers", [])
        except Exception:
            return []


customer_analyzer = CustomerAnalyzer()
```

- [ ] **Step 3: Crear app/ai/promotion_generator.py**

```python
from app.ai.ollama_client import ollama_client
import json


class PromotionGenerator:
    async def suggest_promotion(self, sales_data: dict, customer_segments: dict) -> dict:
        system = """Eres un experto en marketing de e-commerce.
Sugiere promociones basadas en datos de ventas y segmentos de clientes.
Responde en JSON."""
        
        prompt = f"""Datos de ventas:
{json.dumps(sales_data, indent=2)}

Segmentos de clientes:
{json.dumps(customer_segments, indent=2)}

Sugiere 3 promociones efectivas y responde en JSON:
{{
    "suggestions": [
        {{
            "title": "<título>",
            "description": "<descripción>",
            "discount_type": "<percentage/fixed>",
            "discount_value": <valor>,
            "target_segment": "<segmento>",
            "estimated_redemption": "<% estimado>",
            "reasoning": "<por qué funcionaría>"
        }}
    ]
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {"suggestions": []}
    
    async def generate_promo_text(self, promotion_data: dict) -> dict:
        system = """Genera textos de marketing atractivos para una promoción."""
        
        prompt = f"""Promoción:
- Título: {promotion_data['title']}
- Descuento: {promotion_data['discount_value']}%
- Productos: {promotion_data.get('products', 'todos')}

Genera:
1. Asunto de email atractivo
2. Cuerpo de email corto
3. Texto de banner

Responde en JSON:
{{
    "email_subject": "<asunto>",
    "email_body": "<cuerpo>",
    "banner_text": "<banner>"
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {
                "email_subject": f"¡{promotion_data['discount_value']}% de descuento!",
                "email_body": "Aprovecha esta oferta especial.",
                "banner_text": f"¡{promotion_data['discount_value']}% OFF!",
            }


promotion_generator = PromotionGenerator()
```

- [ ] **Step 4: Crear app/ai/welcome_generator.py**

```python
from app.ai.ollama_client import ollama_client
import json


class WelcomeGenerator:
    async def generate_welcome_message(self, customer_data: dict, event_type: str) -> dict:
        system = """Genera mensajes de felicitación personalizados y cálidos para clientes fieles.
El tono debe ser cercano y agradecido."""
        
        prompt = f"""Cliente:
- Nombre: {customer_data.get('name', 'Cliente')}
- Nivel: {customer_data['loyalty_level']}
- Total gastado: ${customer_data['total_spent']}
- Compras realizadas: {customer_data['purchase_count']}
- Evento: {event_type}

Genera un mensaje de felicitación personalizado y responde en JSON:
{{
    "subject": "<asunto del email>",
    "greeting": "<saludo personalizado>",
    "body": "<cuerpo del mensaje>",
    "call_to_action": "<texto del botón>",
    "ps": "<post data opcional>"
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {
                "subject": "¡Felicidades por tu logro!",
                "greeting": f"¡Hola {customer_data.get('name', '')}!",
                "body": "Gracias por ser un cliente tan valioso para nosotros.",
                "call_to_action": "Ver tu recompensa",
                "ps": "",
            }
    
    async def suggest_congratulation_rule(self, customer_data: dict) -> dict:
        system = """Basado en datos de clientes, sugiere reglas de felicitación efectivas."""
        
        prompt = f"""Datos de clientes:
{json.dumps(customer_data, indent=2)}

Sugiere 3 reglas de felicitación y responde en JSON:
{{
    "rules": [
        {{
            "name": "<nombre>",
            "event_type": "<total_spent/purchase_count/loyalty_level_up>",
            "event_value": <valor>,
            "reward_type": "<coupon/points>",
            "reward_value": <valor>,
            "reasoning": "<por qué>"
        }}
    ]
}}"""
        
        try:
            response = await ollama_client.generate(prompt, system)
            return json.loads(response)
        except Exception:
            return {"rules": []}


welcome_generator = WelcomeGenerator()
```

- [ ] **Step 5: Crear app/ai/__init__.py**

```python
from app.ai.customer_analyzer import customer_analyzer
from app.ai.promotion_generator import promotion_generator
from app.ai.welcome_generator import welcome_generator

__all__ = ["customer_analyzer", "promotion_generator", "welcome_generator"]
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: implement Ollama AI integration"
```

---

## Fase 10: Dashboard Admin

### Task 13: Implementar dashboard admin con IA

**Files:**
- Create: `tienda-eaciot/app/schemas/dashboard.py`
- Create: `tienda-eaciot/app/services/dashboard_service.py`
- Create: `tienda-eaciot/app/routers/admin_dashboard.py`

**Interfaces:**
- Produces: `dashboard_service` con métricas y sugerencias IA
- Produces: Rutas `/admin/dashboard` y `/admin/ai`

- [ ] **Step 1: Crear app/services/dashboard_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Dict, List
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.promotion import Promotion
from app.ai.customer_analyzer import customer_analyzer
from app.ai.promotion_generator import promotion_generator
from app.ai.welcome_generator import welcome_generator


class DashboardService:
    async def get_dashboard_metrics(self, db: AsyncSession) -> dict:
        # Sales metrics
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        total_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(Order.status == "paid")
        )
        today_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(
                and_(Order.status == "paid", func.date(Order.created_at) == today)
            )
        )
        week_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(
                and_(Order.status == "paid", Order.created_at >= week_ago)
            )
        )
        
        # Customer metrics
        total_customers = await db.execute(select(func.count(User.id)))
        new_today = await db.execute(
            select(func.count(User.id)).where(func.date(User.created_at) == today)
        )
        
        # Loyalty distribution
        loyalty_dist = await db.execute(
            select(User.loyalty_level, func.count(User.id)).group_by(User.loyalty_level)
        )
        
        # Top products
        top_products = await db.execute(
            select(Product.title, func.sum(OrderItem.quantity).label("total_sold"))
            .join(OrderItem, Product.id == OrderItem.product_id)
            .group_by(Product.title)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
        )
        
        return {
            "sales": {
                "total": float(total_sales.scalar() or 0),
                "today": float(today_sales.scalar() or 0),
                "this_week": float(week_sales.scalar() or 0),
            },
            "customers": {
                "total": total_customers.scalar() or 0,
                "new_today": new_today.scalar() or 0,
                "loyalty_distribution": {row[0]: row[1] for row in loyalty_dist.all()},
            },
            "top_products": [
                {"title": row[0], "sold": row[1]} for row in top_products.all()
            ],
        }
    
    async def get_ai_suggestions(self, db: AsyncSession) -> dict:
        # Get customer data for analysis
        customers = await db.execute(
            select(User).where(User.purchase_count > 0).limit(100)
        )
        customer_list = [
            {
                "id": str(c.id),
                "name": c.name,
                "total_spent": float(c.total_spent),
                "purchase_count": c.purchase_count,
                "loyalty_level": c.loyalty_level,
                "last_purchase": str(c.last_purchase_at) if c.last_purchase_at else None,
            }
            for c in customers.scalars().all()
        ]
        
        # Get sales data
        sales_data = await self.get_dashboard_metrics(db)
        
        # Get AI suggestions
        fidel_customers = await customer_analyzer.identify_fidel_customers(customer_list)
        promo_suggestions = await promotion_generator.suggest_promotion(
            sales_data["sales"],
            sales_data["customers"]["loyalty_distribution"],
        )
        
        return {
            "fidel_customers": fidel_customers,
            "promotion_suggestions": promo_suggestions.get("suggestions", []),
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }
    
    async def approve_suggestion(self, db: AsyncSession, suggestion_type: str, suggestion_data: dict) -> dict:
        if suggestion_type == "promotion":
            promotion = Promotion(
                title=suggestion_data["title"],
                description=suggestion_data.get("description"),
                discount_type=suggestion_data["discount_type"],
                discount_value=suggestion_data["discount_value"],
                is_approved=True,
                ai_suggestion=suggestion_data,
            )
            db.add(promotion)
            await db.flush()
            return {"status": "approved", "id": str(promotion.id)}
        
        return {"status": "unknown_type"}


dashboard_service = DashboardService()
```

- [ ] **Step 2: Crear app/routers/admin_dashboard.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_dashboard_metrics(db)


@router.get("/ai/suggestions")
async def get_ai_suggestions(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_ai_suggestions(db)


@router.post("/ai/suggestions/approve")
async def approve_suggestion(
    suggestion_type: str, 
    suggestion_data: dict,
    db: AsyncSession = Depends(get_db)
):
    return await dashboard_service.approve_suggestion(db, suggestion_type, suggestion_data)
```

- [ ] **Step 3: Registrar router en main.py**

```python
from app.routers import auth, products, admin_products, orders, payments, loyalty, promotions, admin_promotions, admin_dashboard

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(admin_products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(loyalty.router)
app.include_router(promotions.router)
app.include_router(admin_promotions.router)
app.include_router(admin_dashboard.router)
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: implement admin dashboard with AI suggestions"
```

---

## Fase 11: Templates y Frontend

### Task 14: Crear templates Jinja2 con Tailwind CSS

**Files:**
- Create: `tienda-eaciot/app/templates/base.html`
- Create: `tienda-eaciot/app/templates/index.html`
- Create: `tienda-eaciot/app/templates/products/list.html`
- Create: `tienda-eaciot/app/templates/admin/dashboard.html`

**Interfaces:**
- Produces: Templates HTML con Tailwind CSS y HTMX

- [ ] **Step 1: Crear app/templates/base.html**

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Tienda Eaciot{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <a href="/" class="text-xl font-bold">Tienda Eaciot</a>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="/products" class="hover:text-blue-600">Productos</a>
                    <a href="/cart" class="hover:text-blue-600">Carrito</a>
                    {% if user %}
                        <a href="/account" class="hover:text-blue-600">Mi Cuenta</a>
                        <a href="/auth/logout" class="hover:text-red-600">Salir</a>
                    {% else %}
                        <a href="/auth/login" class="bg-blue-600 text-white px-4 py-2 rounded">Iniciar Sesión</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-gray-800 text-white py-8 mt-16">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p>&copy; 2026 Tienda Eaciot. Todos los derechos reservados.</p>
        </div>
    </footer>
</body>
</html>
```

- [ ] **Step 2: Crear app/templates/index.html**

```html
{% extends "base.html" %}

{% block content %}
<div class="text-center py-16">
    <h1 class="text-4xl font-bold mb-4">Bienvenido a Tienda Eaciot</h1>
    <p class="text-xl text-gray-600 mb-8">Productos digitales y físicos de alta calidad</p>
    <a href="/products" class="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg hover:bg-blue-700">
        Ver Productos
    </a>
</div>

{% if featured_products %}
<div class="mt-16">
    <h2 class="text-2xl font-bold mb-8">Productos Destacados</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        {% for product in featured_products %}
        <div class="bg-white rounded-lg shadow p-6">
            <h3 class="font-bold text-lg mb-2">{{ product.title }}</h3>
            <p class="text-gray-600 mb-4">{{ product.description[:100] }}...</p>
            <div class="flex justify-between items-center">
                <span class="text-2xl font-bold">${{ product.price }}</span>
                <a href="/products/{{ product.id }}" class="bg-blue-600 text-white px-4 py-2 rounded">
                    Ver más
                </a>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Crear app/templates/products/list.html**

```html
{% extends "base.html" %}

{% block content %}
<h1 class="text-3xl font-bold mb-8">Productos</h1>

<div class="grid grid-cols-1 md:grid-cols-4 gap-8">
    <!-- Sidebar categorías -->
    <aside>
        <h3 class="font-bold mb-4">Categorías</h3>
        <ul class="space-y-2">
            {% for category in categories %}
            <li>
                <a href="/products?category={{ category.slug }}" 
                   class="hover:text-blue-600 {% if current_category == category.slug %}text-blue-600 font-bold{% endif %}">
                    {{ category.name }}
                </a>
            </li>
            {% endfor %}
        </ul>
    </aside>

    <!-- Grid productos -->
    <div class="col-span-3 grid grid-cols-1 md:grid-cols-3 gap-6">
        {% for product in products %}
        <div class="bg-white rounded-lg shadow p-6">
            {% if product.image_url %}
            <img src="{{ product.image_url }}" alt="{{ product.title }}" class="w-full h-48 object-cover rounded mb-4">
            {% endif %}
            <h3 class="font-bold text-lg mb-2">{{ product.title }}</h3>
            <p class="text-gray-600 mb-4">{{ product.description[:100] }}...</p>
            <div class="flex justify-between items-center">
                <span class="text-xl font-bold">${{ product.price }}</span>
                <button hx-post="/cart/add/{{ product.id }}" 
                        hx-target="#cart-count"
                        class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                    Agregar
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Crear app/templates/admin/dashboard.html**

```html
{% extends "base.html" %}

{% block title %}Dashboard Admin - Tienda Eaciot{% endblock %}

{% block content %}
<div class="flex justify-between items-center mb-8">
    <h1 class="text-3xl font-bold">Dashboard</h1>
    <a href="/admin/ai/suggestions" class="bg-purple-600 text-white px-4 py-2 rounded">
        Ver Sugerencias IA
    </a>
</div>

<!-- Métricas -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
    <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-gray-500 text-sm">Ventas Totales</h3>
        <p class="text-3xl font-bold">${{ metrics.sales.total }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-gray-500 text-sm">Ventas Hoy</h3>
        <p class="text-3xl font-bold">${{ metrics.sales.today }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-gray-500 text-sm">Clientes Totales</h3>
        <p class="text-3xl font-bold">{{ metrics.customers.total }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-6">
        <h3 class="text-gray-500 text-sm">Nuevos Hoy</h3>
        <p class="text-3xl font-bold">{{ metrics.customers.new_today }}</p>
    </div>
</div>

<!-- Sugerencias IA -->
<div class="bg-white rounded-lg shadow p-6 mb-8">
    <h2 class="text-xl font-bold mb-4">Sugerencias de IA</h2>
    <div id="ai-suggestions" hx-get="/admin/ai/suggestions/partial" hx-trigger="load">
        Cargando sugerencias...
    </div>
</div>

<!-- Top Productos -->
<div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-xl font-bold mb-4">Top Productos</h2>
    <table class="w-full">
        <thead>
            <tr class="border-b">
                <th class="text-left py-2">Producto</th>
                <th class="text-right py-2">Vendidos</th>
            </tr>
        </thead>
        <tbody>
            {% for product in metrics.top_products %}
            <tr class="border-b">
                <td class="py-2">{{ product.title }}</td>
                <td class="text-right py-2">{{ product.sold }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

- [ ] **Step 5: Agregar rutas para templates en main.py**

```python
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    products = await product_service.get_products(db, active_only=True)
    user_id = request.cookies.get("user_id")
    user = None
    if user_id:
        user = await db.get(User, user_id)
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "featured_products": products[:6]})


@app.get("/products")
async def products_page(request: Request, category: str = None, db: AsyncSession = Depends(get_db)):
    products = await product_service.get_products(db)
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse("products/list.html", {
        "request": request,
        "products": products,
        "categories": categories,
        "current_category": category,
    })
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: add Jinja2 templates with Tailwind CSS"
```

---

## Fase 12: Testing

### Task 15: Escribir tests unitarios

**Files:**
- Create: `tienda-eaciot/tests/conftest.py`
- Create: `tienda-eaciot/tests/test_products.py`
- Create: `tienda-eaciot/tests/test_orders.py`
- Create: `tienda-eaciot/tests/test_loyalty.py`

**Interfaces:**
- Produces: Tests que pasan con >80% cobertura

- [ ] **Step 1: Crear tests/conftest.py**

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database import Base, get_db
from app.main import app
from httpx import AsyncClient

TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/tienda_eaciot_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db):
    async def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Crear tests/test_products.py**

```python
import pytest
from app.services.product_service import product_service
from app.schemas.product import ProductCreate


@pytest.mark.asyncio
async def test_create_product(db):
    data = ProductCreate(
        title="Test Product",
        description="A test product",
        price=29.99,
        product_type="ebook",
    )
    product = await product_service.create_product(db, data)
    assert product.title == "Test Product"
    assert float(product.price) == 29.99


@pytest.mark.asyncio
async def test_get_products(db):
    products = await product_service.get_products(db)
    assert isinstance(products, list)


@pytest.mark.asyncio
async def test_get_product_not_found(db):
    import uuid
    product = await product_service.get_product(db, uuid.uuid4())
    assert product is None
```

- [ ] **Step 3: Crear tests/test_loyalty.py**

```python
import pytest
from app.services.loyalty_service import loyalty_service
from decimal import Decimal


def test_calculate_level():
    assert loyalty_service.calculate_level(Decimal("0")) == "bronce"
    assert loyalty_service.calculate_level(Decimal("500")) == "plata"
    assert loyalty_service.calculate_level(Decimal("1500")) == "oro"
    assert loyalty_service.calculate_level(Decimal("5000")) == "diamante"


def test_get_discount():
    assert loyalty_service.get_discount("bronce") == 5
    assert loyalty_service.get_discount("plata") == 10
    assert loyalty_service.get_discount("oro") == 15
    assert loyalty_service.get_discount("diamante") == 20
```

- [ ] **Step 4: Ejecutar tests**

```bash
cd C:\Users\Manu\tienda-eaciot
pytest tests/ -v --cov=app
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "test: add unit tests for products and loyalty"
```

---

## Resumen de Entregables

### Archivos Creados
- 30+ archivos Python (models, schemas, services, routers, AI)
- 5+ templates HTML
- Docker Compose y Dockerfile
- Configuración de Alembic
- Tests unitarios

### Funcionalidades
1. ✅ Autenticación con Auth0
2. ✅ CRUD de productos (digitales + físicos)
3. ✅ Sistema de órdenes y carrito
4. ✅ Pagos con Stripe
5. ✅ Sistema de fidelización con niveles
6. ✅ Promociones y cupones
7. ✅ Reglas de felicitación
8. ✅ Motor de IA con Ollama
9. ✅ Dashboard admin con sugerencias IA
10. ✅ Templates responsivos

### Para Ejecutar

```bash
# 1. Clonar y configurar
cd C:\Users\Manu\tienda-eaciot
cp .env.example .env
# Editar .env con tus credenciales

# 2. Iniciar servicios
docker-compose up -d

# 3. Ejecutar migraciones
alembic upgrade head

# 4. Iniciar aplicación
uvicorn app.main:app --reload

# 5. Ejecutar tests
pytest tests/ -v
```

---

**Plan completo. Dos opciones de ejecución:**

**1. Subagent-Driven (recomendado)** - Despacho un subagente fresco por tarea, revisión entre tareas, iteración rápida

**2. Ejecución Inline** - Ejecuto las tareas en esta sesión con puntos de verificación

**¿Cuál prefieres?**
