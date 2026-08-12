# AI Marketing Department — Arquitectura Open Source

**Fecha:** 2026-08-12  
**Autor:** Investigador Senior en Arquitecturas de Agentes AI  
**Proyecto:** tienda-eaciot  

---

## 1. Resumen Ejecutivo

El "AI Marketing Department" es un sistema de agentes AI que opera como un departamento de marketing autónomo para tu tienda ecommerce. Utiliza **orquestación jerárquica** (no mesh ni swarm puro) donde un orquestador central delega tareas especializadas a sub-agentes, cada uno con herramientas específicas y acceso a conocimiento de productos/clientes via RAG.

**Stack recomendado:**
- **Orquestador:** CrewAI (Flows + Crews)
- **LLMs:** Ollama Cloud + OpenCode Go
- **RAG/GraphRAG:** LlamaIndex + Microsoft GraphRAG
- **Persistencia:** SQLite + AgentDB
- **Backend:** FastAPI
- **Imagen:** Stable Diffusion via Ollama (modelos multimodales)

---

## 2. Patrones de Orquestación Investigados

### 2.1 Hierarchical (RECOMENDADO)
- **Descripción:** Orquestador central que delega a sub-agentes especializados
- **Ventaja:** Control centralizado, trazabilidad, fácil de auditar
- **Frameworks:** CrewAI (Flows), LangGraph (StateGraph)
- **Uso en Marketing:** El "Marketing Director" asigna tareas al "Content Writer", "SEO Analyst", "Campaign Manager"

### 2.2 Mesh
- **Descripción:** Agentes que se comunican entre sí sin jerarquía fija
- **Ventaja:** Flexibilidad, resiliencia
- **Desventaja:** Complejidad de debugging, difícil de auditar
- **Decisión:** No recomendado para marketing (necesita control de calidad humano)

### 2.3 Swarm
- **Descripción:** Enjambre de agentes simples que emergen comportamiento complejo
- **Ventaja:** Escalabilidad masiva
- **Desventaja:** Falta de control granular, difícil de predecir
- **Decisión:** No recomendado (demasiado caótico para contenido de marca)

---

## 3. Arquitectura Recomendada: Hierarchical con Flows

```
┌─────────────────────────────────────────────────────────────┐
│                    MARKETING ORCHESTRATOR                     │
│                    (CrewAI Flow principal)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   CONTENT    │  │     SEO     │  │   CAMPAIGN          │  │
│  │    AGENT     │  │    AGENT    │  │     AGENT           │  │
│  │              │  │             │  │                     │  │
│  │ • Blog posts │  │ • Keywords  │  │ • Email sequences   │  │
│  │ • Descrip.   │  │ • Meta tags │  │ • Social media      │  │
│  │ • Social     │  │ • Backlinks │  │ • Ads copy          │  │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                 │                     │             │
│         └─────────────────┼─────────────────────┘             │
│                           │                                   │
│  ┌────────────────────────▼─────────────────────────────┐    │
│  │              SHARED KNOWLEDGE LAYER                   │    │
│  │                                                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │    │
│  │  │  Product     │  │  Customer   │  │  Campaign    │  │    │
│  │  │  Knowledge   │  │  Knowledge  │  │  History     │  │    │
│  │  │  (RAG)       │  │  (GraphRAG) │  │  (SQLite)    │  │    │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐    │
│  │              TOOL LAYER                                │    │
│  │                                                       │    │
│  │  • Image Generator (Stable Diffusion via Ollama)      │    │
│  │  • Web Scraper (para investigación de mercado)        │    │
│  │  • Analytics API (métricas de la tienda)              │    │
│  │  • Email Sender (para campañas)                       │    │
│  │  • Social Media APIs                                  │    │
│  └───────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Frameworks y Bibliotecas Open Source

### 4.1 Orquestación de Agentes

| Framework | GitHub | Estrellas | Uso en este proyecto |
|-----------|--------|-----------|---------------------|
| **CrewAI** | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | 57k | Orquestador principal (Flows + Crews) |
| **LangGraph** | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | 39.5k | Alternativa para flujos complejos con state |
| **AgentScope** | [agentscope-ai/agentscope](https://github.com/agentscope-ai/agentscope) | 28.9k | Alternativa con soporte nativo para Ollama |

### 4.2 LLMs y Modelos Locales

| Herramienta | GitHub | Estrellas | Uso en este proyecto |
|-------------|--------|-----------|---------------------|
| **Ollama** | [ollama/ollama](https://github.com/ollama/ollama) | 178k | Servidor de modelos locales (texto + multimodal) |
| **OpenCode Go** | (proveedor configurado) | - | Backup/alternativa a Ollama |

**Modelos recomendados para marketing:**
- **Texto:** llama3.1:8b, qwen2.5:14b, deepseek-coder-v2
- **Multimodal (imagen):** llava:13b, bakllava
- **Embeddings:** nomic-embed-text, bge-small-en-v1.5

### 4.3 RAG y GraphRAG

| Framework | GitHub | Estrellas | Uso en este proyecto |
|-----------|--------|-----------|---------------------|
| **LlamaIndex** | [run-llama/llama_index](https://github.com/run-llama/llama_index) | 51.6k | RAG para catálogo de productos |
| **Microsoft GraphRAG** | [microsoft/graphrag](https://github.com/microsoft/graphrag) | 35.4k | Relaciones cliente-producto-campaña |

### 4.4 Persistencia y Memoria

| Herramienta | GitHub | Estrellas | Uso en este proyecto |
|-------------|--------|-----------|---------------------|
| **SQLite** | (built-in Python) | - | Base de datos principal |
| **AgentDB** | (integrado en ecosistema) | - | Memoria de agentes, decisiones, contexto |
| **ChromaDB** | [chroma-core/chroma](https://github.com/chroma-core/chroma) | 16k | Vector store para embeddings |

### 4.5 Generación de Imágenes

| Herramienta | GitHub | Estrellas | Uso en este proyecto |
|-------------|--------|-----------|---------------------|
| **Ollama (multimodal)** | [ollama/ollama](https://github.com/ollama/ollama) | 178k | Modelos como llava para análisis/generación |
| **Stable Diffusion WebUI** | [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | 140k | Generación de imágenes para campañas |

### 4.6 Backend API

| Framework | GitHub | Estrellas | Uso en este proyecto |
|-----------|--------|-----------|---------------------|
| **FastAPI** | [tiangolo/fastapi](https://github.com/tiangolo/fastapi) | 75k | API REST para el sistema |
| **Uvicorn** | [encode/uvicorn](https://github.com/encode/uvicorn) | 8k | Servidor ASGI |

---

## 5. Auto-Routing de Tareas de Marketing

El orquestador implementa un sistema de routing basado en el tipo de tarea:

```python
# Pseudocódigo del router
TASK_ROUTES = {
    "content_creation": ContentAgent,
    "seo_optimization": SEOAgent,
    "campaign_management": CampaignAgent,
    "customer_analysis": AnalyticsAgent,
    "image_generation": ImageAgent,
}

def route_task(task_description: str) -> Agent:
    # 1. Clasificar la tarea usando LLM
    task_type = classify_task(task_description)
    
    # 2. Buscar agente especializado
    agent = TASK_ROUTES.get(task_type, ContentAgent)
    
    # 3. Cargar contexto relevante (RAG)
    context = load_context(task_description)
    
    # 4. Ejecutar con contexto
    return agent.execute(task_description, context)
```

**Flujo de decisión:**
1. Usuario solicita tarea → Orquestador
2. Orquestador clasifica tipo de tarea
3. Carga contexto relevante desde RAG/GraphRAG
4. Delega al sub-agente especializado
5. Sub-agente ejecuta y retorna resultado
6. Orquestador valida y persiste decisión

---

## 6. RAG y GraphRAG para Conocimiento

### 6.1 RAG para Productos (LlamaIndex)

```
[Documentos de productos] → [Chunking] → [Embeddings] → [Vector Store]
                                                           ↓
[Query: "zapatos deportivos"] → [Retrieval] → [Contexto relevante] → [LLM Response]
```

**Fuentes de datos:**
- Descripciones de productos
- Reseñas de clientes
- FAQs
- Blog posts existentes

### 6.2 GraphRAG para Relaciones (Microsoft)

```
[Cliente] --compró--> [Producto]
    ↓
[tiene_interés_en] → [Categoría]
    ↓
[responde_a] → [Campaña anterior]
```

**Entidades y relaciones:**
- Clientes → compras → Productos
- Productos → pertenecen_a → Categorías
- Campañas → dirigidas_a → Segmentos
- Contenido → optimizado_para → Keywords

---

## 7. Memoria y Persistencia

### 7.1 SQLite (Decisiones Operativas)

```sql
-- Tabla de decisiones de marketing
CREATE TABLE marketing_decisions (
    id INTEGER PRIMARY KEY,
    agent_id TEXT,
    task_type TEXT,
    decision TEXT,
    context JSON,
    outcome TEXT,
    created_at TIMESTAMP
);

-- Tabla de campañas
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    status TEXT,
    target_audience JSON,
    content JSON,
    metrics JSON,
    created_at TIMESTAMP
);
```

### 7.2 AgentDB (Memoria de Largo Plazo)

- **Session Memory:** Contexto de la conversación actual
- **Long-term Memory:** Decisiones pasadas, patrones aprendidos
- **Pattern Learning:** Qué funcionó antes para similares tipos de contenido

---

## 8. Multi-Modalidad (Texto + Imagen)

### 8.1 Flujo de Generación de Contenido Visual

```
[Requerimiento: "imagen para post de Instagram sobre zapatos"]
    ↓
[Content Agent] → Genera prompt descriptivo
    ↓
[Image Agent] → Envía a Ollama (llava) o Stable Diffusion
    ↓
[Resultado] → Imagen generada + copy sugerido
    ↓
[Review Agent] → Valida calidad y coherencia de marca
```

### 8.2 Modelos Multimodales Disponibles en Ollama

- **llava:13b** - Análisis y generación de imágenes
- **bakllava** - Alternativa ligera
- **llava-llama3** - Más reciente, mejor calidad

---

## 9. Proactivismo: Agente que Detecta Oportunidades

### 9.1 Triggers Automáticos

```python
PROACTIVE_TRIGGERS = {
    "inventory_change": {
        "condition": "stock > threshold AND days_without_sale > 30",
        "action": "generate_promotion"
    },
    "trending_topic": {
        "condition": "keyword_trend_score > 0.8",
        "action": "create_related_content"
    },
    "customer_behavior": {
        "condition": "cart_abandonment_rate > 0.4",
        "action": "send_recovery_email"
    },
    "competitor_movement": {
        "condition": "competitor_price_change > 10%",
        "action": "suggest_price_adjustment"
    }
}
```

### 9.2 Ciclo de Monitoreo

```
[Cada 6 horas]
    ↓
[Analytics Agent] → Recolecta métricas
    ↓
[Decision Engine] → Evalúa triggers
    ↓
[Orchestrator] → Delega acciones si hay oportunidad
    ↓
[Execution] → Ejecuta campaña/contenido
    ↓
[Feedback Loop] → Mide resultados, aprende
```

---

## 10. Diagrama Mental del Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO                                  │
│                   (Dueño de tienda)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MARKETING ORCHESTRATOR                         │
│                   (CrewAI Flow)                                  │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Content    │    │     SEO      │    │    Campaign       │   │
│  │    Crew      │    │    Crew      │    │      Crew         │   │
│  │              │    │              │    │                   │   │
│  │ • Writer     │    │ • Analyst    │    │ • Manager         │   │
│  │ • Editor     │    │ • Researcher │    │ • Scheduler       │   │
│  │ • Designer   │    │ • Optimizer  │    │ • Analyst         │   │
│  └──────┬───────┘    └──────┬───────┘    └─────────┬─────────┘   │
│         │                   │                      │             │
│         └───────────────────┼──────────────────────┘             │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │                 KNOWLEDGE LAYER                            │   │
│  │                                                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │   │
│  │  │  Products  │  │  Customers │  │    Campaigns       │   │   │
│  │  │    RAG     │  │  GraphRAG  │  │    History         │   │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │                    TOOL LAYER                              │   │
│  │                                                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │   │
│  │  │   Image    │  │    Web     │  │     Analytics      │   │   │
│  │  │ Generator  │  │  Scraper   │  │       API          │   │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────┘   │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │                 PROACTIVE ENGINE                           │   │
│  │                                                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │   │
│  │  │  Monitor   │  │  Trigger   │  │     Executor       │   │   │
│  │  │  (6h)      │  │  Evaluator │  │     (Actions)      │   │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TIENDA EACIOT                                 │
│              (Ecommerce existente)                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Riesgos y Recomendaciones

### 11.1 Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Calidad de contenido IA** | Alta | Alto | Human-in-the-loop para publicaciones críticas |
| **Costo de cómputo (modelos locales)** | Media | Alto | Usar modelos pequeños (7b-13b), caché de respuestas |
| **Consistencia de marca** | Alta | Alto | Guardrails de estilo, revisión humana |
| **Alucinaciones del LLM** | Media | Alto | Validación de hechos, fuentes verificadas |
| **Privacidad de datos de clientes** | Baja | Crítico | Datos anonimizados, cumplimiento GDPR |
| **Dependencia de un solo proveedor LLM** | Media | Medio | Soporte dual Ollama + OpenCode Go |

### 11.2 Recomendaciones

1. **Empezar pequeño:** Implementar solo el Content Agent primero, luego expandir
2. **Human-in-the-loop:** Todo contenido pasa por revisión antes de publicar
3. **Feedback loop:** Medir impacto de cada decisión de marketing
4. **Modelos apropiados:** No usar modelos de 70b para tareas simples
5. **Caché inteligente:** Reutilizar embeddings y respuestas frecuentes
6. **Monitoreo continuo:** Dashboard de métricas de agentes

### 11.3 Stack Alternativo (si CrewAI no se alinea)

Si prefieres algo más ligero:
- **LangGraph** para orquestación con state
- **LlamaIndex** para RAG
- **SQLite** directo (sin AgentDB)
- **Ollama** como único proveedor LLM

---

## 12. Siguientes Pasos

1. **Validar arquitectura** con stakeholders
2. **Prototipo del Content Agent** (2 semanas)
3. **Integración con catálogo de productos** (1 semana)
4. **Prueba de RAG** con datos reales (1 semana)
5. **Iteración basada en feedback**

---

## 13. Referencias

- CrewAI Documentation: https://docs.crewai.com
- LlamaIndex Documentation: https://docs.llamaindex.ai
- Microsoft GraphRAG: https://microsoft.github.io/graphrag
- Ollama: https://ollama.com
- AgentDB: https://github.com/ag2ai/ag2 (componente del ecosistema)
- FastAPI: https://fastapi.tiangolo.com

---

**Documento generado por:** Investigador Senior en Arquitecturas de Agentes AI  
**Fecha:** 2026-08-12  
**Versión:** 1.0
