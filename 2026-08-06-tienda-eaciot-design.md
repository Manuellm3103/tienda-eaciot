# Especificación: tienda.eaciot.com - Tienda Online con IA

## Resumen Ejecutivo

Tienda online de productos digitales y físicos para el dominio `tienda.eaciot.com`, con sistema de autenticación Auth0, inteligencia artificial mediante Ollama, sistema de fidelización de clientes con niveles, y panel de administración completo donde el administrador tiene control total sobre promociones y felicitaciones.

---

## 1. Objetivos del Proyecto

### 1.1 Objetivo Principal
Crear una tienda online profesional para `eaciot.com` que permita vender productos digitales y físicos, con un sistema de fidelización inteligente que analice clientes y sugiera promociones, pero manteniendo el control total del administrador.

### 1.2 Objetivos Específicos
- Autenticación segura con Auth0 (email/password, Google, GitHub, magic link)
- Catálogo de productos digitales (ebooks, cursos, software, templates) y físicos
- Pasarela de pagos con Stripe y PayPal
- Sistema de fidelización con niveles (Bronce, Plata, Oro, Diamante)
- Motor de IA (Ollama) para análisis de clientes y sugerencias
- Panel de administración con control total sobre promociones y felicitaciones
- Dashboard con métricas de ventas y análisis de IA

---

## 2. Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|------------|---------------|
| Backend | FastAPI (Python 3.11+) | Async, rápido, OpenAPI automático |
| ORM | SQLAlchemy 2.0 + Alembic | Migraciones robustas, async support |
| Base de Datos | PostgreSQL 15+ | Potente, confiable, escalable |
| Templates | Jinja2 + Tailwind CSS | SSR rápido, CSS utility-first |
| Interactividad | HTMX | Sin SPA compleja, actualización parcial |
| Autenticación | Auth0 | OAuth2, múltiples proveedores, seguro |
| Pagos | Stripe + PayPal SDK | Procesadores líderes |
| IA | Ollama (local) | Privacidad, sin costo por uso |
| Testing | Pytest + pytest-asyncio | Testing robusto |

---

## 3. Arquitectura del Sistema

### 3.1 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                      tienda.eaciot.com                          │
├─────────────────────────────────────────────────────────────────┤
│  Frontend: Jinja2 + Tailwind CSS + HTMX (SSR)                   │
├─────────────────────────────────────────────────────────────────┤
│  Backend: FastAPI (async)                                       │
├─────────────────────────────────────────────────────────────────┤
│  Auth: Auth0 (Email/Pass + Google + GitHub + Magic Link)        │
├─────────────────────────────────────────────────────────────────┤
│  DB: PostgreSQL (usuarios, productos, pedidos, fidelización)    │
├─────────────────────────────────────────────────────────────────┤
│  Pagos: Stripe + PayPal                                         │
├─────────────────────────────────────────────────────────────────┤
│  IA: Ollama (local) ─── Análisis + Sugerencias                  │
├─────────────────────────────────────────────────────────────────┤
│  Storage: Local filesystem + CDN opcional                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Módulos Principales

1. **Módulo de Autenticación** (Auth0)
2. **Módulo de Productos** (CRUD + catálogo)
3. **Módulo de Órdenes** (checkout + historial)
4. **Módulo de Pagos** (Stripe + PayPal)
5. **Módulo de Fidelización** (niveles + puntos)
6. **Módulo de Promociones** (admin controla)
7. **Módulo de Felicitaciones** (reglas admin)
8. **Módulo de IA** (Ollama - análisis + sugerencias)
9. **Módulo de Admin** (dashboard + gestión)

---

## 4. Modelo de Datos

### 4.1 Usuarios (Auth0)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture TEXT,
    
    -- Fidelización
    loyalty_level VARCHAR(20) DEFAULT 'bronce' CHECK (loyalty_level IN ('bronce', 'plata', 'oro', 'diamante')),
    loyalty_points INTEGER DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0.00,
    purchase_count INTEGER DEFAULT 0,
    last_purchase_at TIMESTAMP,
    
    -- IA
    is_fidel BOOLEAN DEFAULT FALSE,
    fidel_score INTEGER DEFAULT 0 CHECK (fidel_score >= 0 AND fidel_score <= 100),
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Categorías

```sql
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 Productos (Digitales + Físicos)

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category_id UUID REFERENCES categories(id),
    
    -- Tipo de producto
    product_type VARCHAR(20) NOT NULL CHECK (product_type IN ('ebook', 'curso', 'software', 'template', 'fisico')),
    
    -- Archivos y medios
    image_url TEXT,
    file_path TEXT, -- Para productos digitales
    weight DECIMAL(8,2), -- Para productos físicos (kg)
    
    -- Inventario
    is_active BOOLEAN DEFAULT TRUE,
    stock INTEGER DEFAULT -1, -- -1 = ilimitado para digitales
    
    -- SEO
    meta_title VARCHAR(255),
    meta_description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.4 Órdenes

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    
    -- Montos
    subtotal DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    shipping_amount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(10,2) NOT NULL,
    
    -- Estado
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled', 'refunded')),
    
    -- Pago
    payment_method VARCHAR(20) CHECK (payment_method IN ('stripe', 'paypal')),
    payment_id VARCHAR(255),
    
    -- Envío (para productos físicos)
    shipping_address JSONB,
    tracking_number VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.5 Items de Orden

```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(id),
    product_id UUID REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    price_at_purchase DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.6 Reglas de Felicitación (Admin configura)

```sql
CREATE TABLE congratulation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Evento que dispara la felicitación
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('total_spent', 'purchase_count', 'specific_product', 'loyalty_level_up')),
    event_value DECIMAL(10,2), -- Ej: 5000 para $5000 en compras
    event_product_id UUID REFERENCES products(id), -- Si es producto específico
    
    -- Recompensa
    reward_type VARCHAR(30) NOT NULL CHECK (reward_type IN ('coupon', 'free_product', 'points', 'free_shipping')),
    reward_value DECIMAL(10,2), -- Ej: 20 para 20% descuento
    reward_product_id UUID REFERENCES products(id), -- Si es producto gratis
    
    -- Mensaje (admin escribe o edita sugerencia IA)
    message_template TEXT NOT NULL,
    email_subject VARCHAR(255),
    
    -- Control
    is_active BOOLEAN DEFAULT TRUE,
    max_uses INTEGER DEFAULT -1, -- -1 = ilimitado
    current_uses INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.7 Historial de Felicitaciones

```sql
CREATE TABLE congratulation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    rule_id UUID REFERENCES congratulation_rules(id),
    order_id UUID REFERENCES orders(id),
    
    message_sent TEXT,
    reward_sent TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.8 Promociones (Admin crea)

```sql
CREATE TABLE promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Descuento
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed', 'free_shipping')),
    discount_value DECIMAL(10,2) NOT NULL,
    
    -- Condiciones
    conditions JSONB, -- {min_purchase: 100, levels: ['oro','diamante'], products: [...]}
    
    -- Vigencia
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    
    -- Cupón
    coupon_code VARCHAR(50) UNIQUE,
    auto_generate_coupons BOOLEAN DEFAULT FALSE,
    
    -- Control
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE, -- Admin aprueba antes de activar
    
    -- IA (sugerencias)
    ai_suggestion JSONB, -- Sugerencias de la IA
    
    -- Estadísticas
    usage_count INTEGER DEFAULT 0,
    max_uses INTEGER DEFAULT -1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.9 Cupones

```sql
CREATE TABLE coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    
    promotion_id UUID REFERENCES promotions(id),
    congratulation_rule_id UUID REFERENCES congratulation_rules(id),
    
    -- Uso
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    used_in_order_id UUID REFERENCES orders(id),
    
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.10 Historial de Fidelización

```sql
CREATE TABLE loyalty_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    points_change INTEGER NOT NULL,
    reason VARCHAR(255),
    order_id UUID REFERENCES orders(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.11 Métricas del Dashboard

```sql
CREATE TABLE metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE UNIQUE NOT NULL,
    
    -- Ventas
    total_sales DECIMAL(10,2) DEFAULT 0.00,
    order_count INTEGER DEFAULT 0,
    
    -- Clientes
    new_customers INTEGER DEFAULT 0,
    returning_customers INTEGER DEFAULT 0,
    
    -- Promociones
    promotions_sent INTEGER DEFAULT 0,
    promotions_redeemed INTEGER DEFAULT 0,
    
    -- Felicitaciones
    congratulations_sent INTEGER DEFAULT 0,
    
    -- Por nivel
    revenue_by_level JSONB, -- {"bronce": 1000, "plata": 2000, ...}
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Sistema de Fidelización

### 5.1 Niveles

| Nivel | Monto Acumulado | Beneficios |
|-------|-----------------|------------|
| 🥉 Bronce | $0 - $499 | 5% descuento, acceso básico |
| 🥈 Plata | $500 - $1,499 | 10% descuento, ofertas exclusivas |
| 🥇 Oro | $1,500 - $4,999 | 15% descuento, soporte prioritario, early access |
| 💎 Diamante | $5,000+ | 20% descuento, regalos sorpresa, consultoría VIP |

### 5.2 Lógica de Ascenso

```python
def calculate_loyalty_level(total_spent: float) -> str:
    if total_spent >= 5000:
        return "diamante"
    elif total_spent >= 1500:
        return "oro"
    elif total_spent >= 500:
        return "plata"
    else:
        return "bronce"
```

### 5.3 Puntos

- 1 punto por cada $1 gastado
- Puntos canjeables por descuentos (100 puntos = $1 descuento)
- Puntos no expiran

---

## 6. Módulo de IA (Ollama)

### 6.1 Funcionalidades

La IA **NO ejecuta acciones automáticamente**. Solo:

1. **Analiza datos** de clientes y ventas
2. **Sugiere promociones** basadas en patrones
3. **Sugiere mensajes** para felicitaciones
4. **Identifica clientes fieles** y oportunidades
5. **Predice comportamiento** de compra

### 6.2 Servicios de IA

#### CustomerAnalyzer
- Calcula score RFM (Recency, Frequency, Monetary)
- Identifica clientes fieles
- Detecta clientes en riesgo de abandono
- Segmenta clientes por comportamiento

#### PromotionGenerator
- Sugiere promociones basadas en datos
- Estima tasa de canje
- Sugiere productos relacionados
- Optimiza condiciones de promo

#### WelcomeGenerator
- Sugiere textos para felicitaciones
- Personaliza mensajes por cliente
- Sugiere recompensas apropiadas

### 6.3 Flujo de Sugerencias IA

```
1. Admin abre Dashboard
   ↓
2. Backend solicita análisis a Ollama
   ↓
3. Ollama analiza datos y genera sugerencias
   ↓
4. Frontend muestra sugerencias en cards
   ↓
5. Admin decide:
   ├── [Aprobar] → Se ejecuta la sugerencia
   ├── [Editar] → Admin modifica, luego se ejecuta
   └── [Rechazar] → Se descarta
```

---

## 7. Módulo de Autenticación (Auth0)

### 7.1 Métodos Soportados

- Email + contraseña
- Login con Google
- Login con GitHub
- Magic link (passwordless)

### 7.2 Flujo de Autenticación

```
1. Usuario hace clic en "Iniciar Sesión"
   ↓
2. Redirección a Auth0 Universal Login
   ↓
3. Usuario elige método (email, Google, GitHub, magic link)
   ↓
4. Auth0 autentica y redirige a callback
   ↓
5. Backend recibe código, intercambia por tokens
   ↓
6. Backend crea/actualiza usuario en DB local
   ↓
7. Backend establece sesión (JWT cookie)
   ↓
8. Usuario redirigido a su cuenta
```

### 7.3 Endpoints de Auth

- `GET /auth/login` - Redirige a Auth0
- `GET /auth/callback` - Callback de Auth0
- `GET /auth/logout` - Cierra sesión
- `GET /auth/me` - Usuario actual

---

## 8. Módulo de Pagos

### 8.1 Stripe

- Checkout Session para pagos únicos
- Webhooks para confirmación de pago
- Soporte para tarjetas de crédito/débito

### 8.2 PayPal

- PayPal Checkout
- Webhooks para confirmación
- Soporte para PayPal balance y tarjetas

### 8.3 Flujo de Checkout

```
1. Usuario agrega productos al carrito
   ↓
2. Usuario procede al checkout
   ↓
3. Sistema calcula total (con descuentos si aplica)
   ↓
4. Usuario elige método de pago (Stripe/PayPal)
   ↓
5. Sistema crea sesión de pago
   ↓
6. Usuario completa pago en pasarela
   ↓
7. Pasarela envía webhook de confirmación
   ↓
8. Sistema:
   ├── Actualiza estado de orden a "paid"
   ├── Actualiza fidelización del usuario
   ├── Verifica reglas de felicitación
   ├── Si cumple regla → Envía felicitación
   └── Genera cupones si aplica
```

---

## 9. Panel de Administración

### 9.1 Dashboard Principal

- Métricas de ventas en tiempo real
- Gráficos de ingresos por período
- Clientes nuevos vs recurrentes
- Productos más vendidos
- Alertas de IA (sugerencias pendientes)

### 9.2 Gestión de Productos

- CRUD completo de productos
- Categorías y subcategorías
- Upload de archivos digitales
- Gestión de inventario (físicos)
- SEO (meta título, descripción)

### 9.3 Gestión de Órdenes

- Lista de órdenes con filtros
- Detalle de orden
- Cambio de estado
- Gestión de envíos (físicos)
- Reembolsos

### 9.4 Gestión de Clientes

- Lista de clientes con filtros
- Detalle de cliente (historial, nivel, puntos)
- Acciones: Enviar promo, Subir nivel, Felicitar
- Segmentos de clientes

### 9.5 Gestión de Promociones

- Crear nueva promoción
- Configurar condiciones
- Ver sugerencias de IA
- Aprobar/Editar/Rechazar sugerencias
- Historial de promociones
- Estadísticas de canje

### 9.6 Gestión de Felicitaciones

- Crear reglas de felicitación
- Configurar eventos y recompensas
- Ver sugerencias de IA para textos
- Editar mensajes
- Historial de felicitaciones enviadas

### 9.7 Sugerencias de IA

- Cards con sugerencias pendientes
- Cada sugerencia tiene:
  - Descripción de la oportunidad
  - Datos que la respaldan
  - Acción sugerida
  - Botones: [Aprobar] [Editar] [Rechazar]

---

## 10. Estructura de Archivos

```
tienda-eaciot/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings from env
│   ├── database.py                # SQLAlchemy async setup
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── category.py
│   │   ├── order.py
│   │   ├── loyalty.py
│   │   ├── promotion.py
│   │   ├── coupon.py
│   │   └── congratulation.py
│   │
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── loyalty.py
│   │   ├── promotion.py
│   │   └── congratulation.py
│   │
│   ├── routers/                   # API routes
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── products.py
│   │   ├── orders.py
│   │   ├── payments.py
│   │   ├── loyalty.py
│   │   ├── promotions.py
│   │   ├── congratulations.py
│   │   └── admin.py
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── auth0_service.py
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   ├── payment_service.py
│   │   ├── stripe_service.py
│   │   ├── paypal_service.py
│   │   ├── loyalty_service.py
│   │   ├── promotion_service.py
│   │   └── congratulation_service.py
│   │
│   ├── ai/                        # Ollama integration
│   │   ├── __init__.py
│   │   ├── ollama_client.py
│   │   ├── customer_analyzer.py
│   │   ├── promotion_generator.py
│   │   └── welcome_generator.py
│   │
│   ├── templates/                 # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── callback.html
│   │   ├── products/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── category.html
│   │   ├── cart/
│   │   │   └── view.html
│   │   ├── checkout/
│   │   │   ├── checkout.html
│   │   │   └── success.html
│   │   ├── account/
│   │   │   ├── profile.html
│   │   │   ├── orders.html
│   │   │   └── loyalty.html
│   │   └── admin/
│   │       ├── dashboard.html
│   │       ├── products/
│   │       ├── orders/
│   │       ├── customers/
│   │       ├── promotions/
│   │       ├── congratulations/
│   │       └── ai_suggestions.html
│   │
│   └── static/                    # Static files
│       ├── css/
│       │   └── styles.css
│       ├── js/
│       │   └── app.js
│       └── images/
│
├── alembic/                       # Database migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── tests/                         # Tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
│   ├── test_payments.py
│   ├── test_loyalty.py
│   ├── test_promotions.py
│   ├── test_congratulations.py
│   └── test_ai.py
│
├── docker-compose.yml             # PostgreSQL + Ollama
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 11. Variables de Entorno

```env
# App
APP_NAME=Tienda Eaciot
APP_SECRET_KEY=your-secret-key-here
FRONTEND_URL=https://tienda.eaciot.com
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tienda_eaciot

# Auth0
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_CALLBACK_URL=https://tienda.eaciot.com/auth/callback
AUTH0_AUDIENCE=https://api.eaciot.com

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3

# Stripe
STRIPE_SECRET_KEY=sk_test_your-key
STRIPE_WEBHOOK_SECRET=whsec_your-secret
STRIPE_PUBLISHABLE_KEY=pk_test_your-key

# PayPal
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_MODE=sandbox

# Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600  # 100MB
```

---

## 12. Endpoints de la API

### 12.1 Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /auth/login | Redirige a Auth0 |
| GET | /auth/callback | Callback de Auth0 |
| GET | /auth/logout | Cierra sesión |
| GET | /auth/me | Usuario actual |

### 12.2 Productos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /products | Lista de productos |
| GET | /products/{id} | Detalle de producto |
| GET | /products/category/{slug} | Productos por categoría |
| POST | /admin/products | Crear producto (admin) |
| PUT | /admin/products/{id} | Actualizar producto (admin) |
| DELETE | /admin/products/{id} | Eliminar producto (admin) |

### 12.3 Órdenes

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /orders | Mis órdenes |
| GET | /orders/{id} | Detalle de orden |
| POST | /orders | Crear orden |
| GET | /admin/orders | Todas las órdenes (admin) |
| PUT | /admin/orders/{id} | Actualizar orden (admin) |

### 12.4 Pagos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /payments/stripe/create | Crear sesión Stripe |
| POST | /payments/stripe/webhook | Webhook Stripe |
| POST | /payments/paypal/create | Crear orden PayPal |
| POST | /payments/paypal/capture | Capturar pago PayPal |

### 12.5 Fidelización

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /loyalty/status | Mi estado de fidelización |
| GET | /loyalty/history | Mi historial de puntos |
| GET | /admin/loyalty/customers | Clientes por nivel (admin) |
| PUT | /admin/loyalty/{user_id} | Ajustar fidelización (admin) |

### 12.6 Promociones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /promotions | Promociones activas |
| POST | /promotions/apply | Aplicar cupón |
| POST | /admin/promotions | Crear promoción (admin) |
| PUT | /admin/promotions/{id} | Actualizar promoción (admin) |
| POST | /admin/promotions/{id}/approve | Aprobar promoción (admin) |
| GET | /admin/promotions/suggestions | Sugerencias IA (admin) |

### 12.7 Felicitaciones

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /admin/congratulations/rules | Crear regla (admin) |
| PUT | /admin/congratulations/rules/{id} | Actualizar regla (admin) |
| GET | /admin/congratulations/rules | Listar reglas (admin) |
| GET | /admin/congratulations/history | Historial (admin) |
| GET | /admin/congratulations/suggestions | Sugerencias IA (admin) |

### 12.8 Dashboard Admin

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /admin/dashboard | Métricas principales |
| GET | /admin/dashboard/sales | Ventas por período |
| GET | /admin/dashboard/customers | Métricas de clientes |
| GET | /admin/ai/suggestions | Todas las sugerencias IA |
| POST | /admin/ai/suggestions/{id}/approve | Aprobar sugerencia |
| POST | /admin/ai/suggestions/{id}/reject | Rechazar sugerencia |

---

## 13. Testing

### 13.1 Cobertura Esperada

- Autenticación: 90%+
- Productos: 85%+
- Órdenes: 85%+
- Pagos: 80%+ (webhooks mocked)
- Fidelización: 90%+
- Promociones: 85%+
- Felicitaciones: 85%+
- IA: 70%+ (Ollama mocked)

### 13.2 Tipos de Tests

- Unit tests: Lógica de negocio
- Integration tests: Flujos completos
- API tests: Endpoints
- E2E tests: Flujos críticos (checkout)

---

## 14. Deployment

### 14.1 Requisitos del Servidor

- Python 3.11+
- PostgreSQL 15+
- Ollama (local o en servidor)
- Node.js (para Tailwind CSS build)
- Dominio: tienda.eaciot.com

### 14.2 Docker Compose (Desarrollo)

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

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - ollama
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@db:5432/tienda_eaciot
      OLLAMA_HOST: http://ollama:11434

volumes:
  postgres_data:
  ollama_data:
```

### 14.3 Pasos de Deployment

1. Configurar DNS: `tienda.eaciot.com` → IP del servidor
2. Instalar Docker y Docker Compose
3. Clonar repositorio
4. Configurar `.env`
5. Ejecutar `docker-compose up -d`
6. Ejecutar migraciones: `alembic upgrade head`
7. Crear admin inicial
8. Configurar SSL (Let's Encrypt)
9. Configurar webhooks de Stripe/PayPal
10. Configurar Auth0

---

## 15. Cronograma Estimado

| Fase | Descripción | Tiempo |
|------|-------------|--------|
| 1 | Setup proyecto + DB + Auth0 | 2 días |
| 2 | Módulo de Productos | 2 días |
| 3 | Módulo de Órdenes + Carrito | 2 días |
| 4 | Módulo de Pagos (Stripe + PayPal) | 2 días |
| 5 | Módulo de Fidelización | 1 día |
| 6 | Módulo de Promociones | 2 días |
| 7 | Módulo de Felicitaciones | 1 día |
| 8 | Módulo de IA (Ollama) | 2 días |
| 9 | Panel Admin | 3 días |
| 10 | Frontend + Templates | 3 días |
| 11 | Testing + QA | 2 días |
| 12 | Deployment + Configuración | 1 día |
| **Total** | | **23 días** |

---

## 16. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Ollama muy lento en servidor | Alto | Usar modelo pequeño (phi3), cache de resultados |
| Auth0 downtime | Medio | Implementar fallback local |
| Webhooks de pago no llegan | Alto | Retry logic, verificación manual |
| Productos digitales pirateados | Medio | Watermarking, limitar descargas |
| Base de datos crece mucho | Bajo | Particionar tablas históricas |

---

## 17. Criterios de Aceptación

### 17.1 Usuario Final

- [ ] Puede registrarse/iniciar sesión con Auth0
- [ ] Puede navegar catálogo de productos
- [ ] Puede agregar productos al carrito
- [ ] Puede completar checkout con Stripe o PayPal
- [ ] Puede ver historial de compras
- [ ] Puede descargar productos digitales comprados
- [ ] Puede ver su nivel de fidelización y puntos
- [ ] Recibe felicitaciones cuando cumple reglas configuradas

### 17.2 Administrador

- [ ] Puede acceder al panel admin
- [ ] Puede gestionar productos (CRUD)
- [ ] Puede ver y gestionar órdenes
- [ ] Puede ver métricas de ventas en dashboard
- [ ] Puede crear y gestionar promociones
- [ ] Puede crear reglas de felicitación
- [ ] Puede ver sugerencias de IA y aprobar/editar/rechazar
- [ ] Puede ver clientes fieles y su historial

### 17.3 Técnico

- [ ] Tests pasan con 80%+ cobertura
- [ ] API documentada con OpenAPI
- [ ] Migraciones de DB funcionan
- [ ] Webhooks de pago procesan correctamente
- [ ] Ollama responde en < 5 segundos
- [ ] Deploy funciona con Docker Compose

---

## 18. Fuera de Alcance

- App móvil nativa (solo web responsive)
- Marketplace de vendedores (solo admin vende)
- Chat en tiempo real
- Integración con redes sociales para ventas
- Sistema de envíos complejo (solo básico para físicos)
- Multi-idioma (solo español por ahora)
- Multi-moneda (solo MXN por ahora)

---

## 19. Aprobación

- [ ] Diseño aprobado por el usuario
- [ ] Spec revisado y aprobado
- [ ] Listo para plan de implementación

---

**Fecha:** 2026-08-06
**Versión:** 1.0
**Autor:** Product Owner / Analista de Sistemas
