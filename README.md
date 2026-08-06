# Tienda Eaciot

Tienda online de productos digitales y físicos para el dominio `tienda.eaciot.com`.

## Características

- Autenticación con Auth0 (email, Google, GitHub, magic link)
- Productos digitales (ebooks, cursos, software, templates) y físicos
- Pagos con Stripe y PayPal
- Sistema de fidelización con niveles (Bronce, Plata, Oro, Diamante)
- Motor de IA con Ollama para sugerencias
- Panel de administración completo

## Stack Tecnológico

- **Backend:** FastAPI (Python 3.11+)
- **Base de datos:** PostgreSQL 15+
- **ORM:** SQLAlchemy 2.0 + Alembic
- **Templates:** Jinja2 + Tailwind CSS + HTMX
- **Autenticación:** Auth0
- **Pagos:** Stripe + PayPal
- **IA:** Ollama (local)

## Instalación

```bash
# 1. Clonar repositorio
git clone <url>
cd tienda-eaciot

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Iniciar servicios (Docker)
docker-compose up -d

# 6. Ejecutar migraciones
alembic upgrade head

# 7. Iniciar aplicación
uvicorn app.main:app --reload
```

## Estructura del Proyecto

```
tienda-eaciot/
├── app/
│   ├── main.py           # FastAPI app
│   ├── config.py          # Settings
│   ├── database.py        # SQLAlchemy setup
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── routers/           # API routes
│   ├── services/          # Business logic
│   ├── ai/                # Ollama integration
│   ├── templates/         # Jinja2 templates
│   └── static/            # CSS, JS, images
├── alembic/               # Migrations
├── tests/                 # Tests
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Desarrollo

```bash
# Ejecutar tests
pytest tests/ -v

# Generar migración
alembic revision --autogenerate -m "description"

# Aplicar migraciones
alembic upgrade head
```

## Licencia

Propietaria - Eaciot
