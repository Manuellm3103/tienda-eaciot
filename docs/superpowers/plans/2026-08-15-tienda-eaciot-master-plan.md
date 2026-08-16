# Tienda Eaciot — Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Tienda Eaciot ecommerce platform by closing all P0/P1 AI innovation gaps and building the AI Marketing Department architecture on top of the existing FastAPI + SQLAlchemy async foundation.

**Architecture:** Extend the existing modular service layer (`app/services/`, `app/ai/`, `app/routers/`) with new AI services, admin routers, and Jinja2 templates. Keep optional AI dependencies isolated in `requirements-ai-innovations.txt` and gate runtime features with `settings.*` flags so the store runs without them. Use SQLite as the primary persistence and add ChromaDB/Meilisearch only where semantic capabilities require it.

**Tech Stack:** FastAPI 0.115+, SQLAlchemy 2.0 async, SQLite, Pydantic V2, Jinja2 + HTMX, Stripe/PayPal, Ollama/OpenCode Go LLM router, pytest.

## Global Constraints

- Target Python 3.11+; avoid syntax above 3.11.
- All new functions must be type-annotated; prefer `str | None` over `Optional[str]`.
- All new DB models need Alembic migrations in `migrations/versions/`.
- All new service functions need unit/integration tests; aim for ≥80% coverage of new code.
- Never block order fulfillment on best-effort AI side effects.
- Gate heavy/optional AI dependencies behind settings flags and runtime imports.
- Keep admin UI consistent with existing Bootstrap/Jinja2 patterns in `app/templates/admin/`.
- Preserve existing 96-test baseline; every phase must end with `pytest tests/ -q` green.

---

## Phase 0 — Foundation (DONE)

**Goal:** Close the Stripe Checkout Session fallback work-in-progress and leave the repo in a clean, committed state.

- [x] Commit Stripe fallback: `app/routers/pages.py`, `app/services/stripe_service.py`, UUID-to-string fixes, integration tests.
- [x] Verify full suite: `pytest tests/ -q` → 96 passed.

---

## Phase 1 — Quick Wins (P0/P1, Small Effort)

**Goal:** Ship 3–4 small AI features that close obvious gaps and build momentum.

### Task 1.1: Complete AI Product Content (Alt Text + SEO Score)

**Files:**
- Create: `app/services/product_content_service.py` extensions
- Modify: `app/models/product.py`, `app/routers/admin_products.py`, `app/templates/admin/products.html`
- Test: `tests/test_admin_product_content.py`

**Interfaces:**
- Consumes: existing `ProductContentGenerator.generate_all()`
- Produces: `alt_texts: list[str]`, `content_score: float`, `seo_score: float` stored on `Product`

- [ ] **Step 1:** Add columns to `Product`: `content_generated_at`, `content_score`, `seo_score`, `alt_texts`.
- [ ] **Step 2:** Generate `alt_texts` list in `generate_all()`.
- [ ] **Step 3:** Compute `seo_score` from title/meta/description/alt coverage.
- [ ] **Step 4:** Expose SEO score in admin product list and batch-enrich UI.
- [ ] **Step 5:** Write migration and tests; run `pytest tests/test_admin_product_content.py -v`.
- [ ] **Step 6:** Commit.

### Task 1.2: Voice Commerce MVP

**Files:**
- Create: `app/services/voice_service.py`, `app/routers/voice.py`
- Modify: `app/main.py`, `app/templates/base.html`, `requirements-ai-innovations.txt`
- Test: `tests/test_voice_search.py`

**Interfaces:**
- Consumes: `search_service.search()` / `search_service.search_with_expansion()`
- Produces: `POST /api/voice-search` returning `{"query": str, "products": list[ProductResponse]}`

- [ ] **Step 1:** Add `faster-whisper` behind runtime import in `voice_service.py`.
- [ ] **Step 2:** Implement `VoiceCommerceService.transcribe(audio_bytes: bytes) -> str`.
- [ ] **Step 3:** Implement `voice_search(audio_bytes)` → transcribe → text search.
- [ ] **Step 4:** Add `/api/voice-search` router and include in `app/main.py`.
- [ ] **Step 5:** Add microphone button + Web Speech API fallback in storefront.
- [ ] **Step 6:** Write tests with mocked whisper; run `pytest tests/test_voice_search.py -v`.
- [ ] **Step 7:** Commit.

### Task 1.3: AI Product Photo Enhancement

**Files:**
- Create: `app/services/image_enhance_service.py`, `app/routers/admin_photos.py`
- Modify: `app/templates/admin/products.html`
- Test: `tests/test_image_enhance.py`

**Interfaces:**
- Consumes: uploaded image bytes
- Produces: enhanced PNG bytes, 1080x1080 social square bytes

- [ ] **Step 1:** Add `rembg` + Pillow behind runtime import.
- [ ] **Step 2:** Implement `ImageEnhancementService.enhance_product_photo(image_bytes)`.
- [ ] **Step 3:** Implement `generate_social_media_square(image_bytes, text=None)`.
- [ ] **Step 4:** Add admin endpoints: `/admin/products/{id}/enhance-photo`, `/admin/products/{id}/social-square`.
- [ ] **Step 5:** Add admin UI buttons on product detail.
- [ ] **Step 6:** Write tests with mocked rembg; run `pytest tests/test_image_enhance.py -v`.
- [ ] **Step 7:** Commit.

---

## Phase 2 — P0 Medium Features

**Goal:** Implement the highest-impact P0 innovations that build on existing foundations.

### Task 2.1: AI Semantic Search + Faceted Navigation

**Files:**
- Create: `app/services/semantic_search_service.py`, `app/routers/admin_search.py`
- Modify: `app/services/search_service.py`, `app/routers/search.py`, `app/templates/search.html`, `docker-compose.yml`
- Test: `tests/test_semantic_search.py`

**Interfaces:**
- Consumes: `Product` rows
- Produces: `SemanticSearchService.search(query, filters)` returning Meilisearch hits

- [ ] **Step 1:** Add optional Meilisearch client behind settings flag.
- [ ] **Step 2:** Implement `index_products()` and `search()` wrappers.
- [ ] **Step 3:** Add facet filters (category, price range, type) to search page.
- [ ] **Step 4:** Add admin reindex, synonym, and "no results" query pages.
- [ ] **Step 5:** Add Meilisearch service to `docker-compose.yml`.
- [ ] **Step 6:** Write tests with mocked Meilisearch client.
- [ ] **Step 7:** Commit.

### Task 2.2: AI-Driven Dynamic Pricing (Production Hardening)

**Files:**
- Create: `app/models/product_analytics.py`, `app/services/dynamic_pricing_service.py`
- Modify: `app/models/product.py`, `app/routers/admin_pricing.py`, `app/templates/admin/pricing.html`
- Test: `tests/test_dynamic_pricing.py`

**Interfaces:**
- Consumes: `UserEvent` aggregates, `Product.stock`, `Product.base_price`
- Produces: recommended `dynamic_price`, optional auto-apply

- [ ] **Step 1:** Add columns: `base_price`, `dynamic_price`, `dynamic_pricing_enabled`, `price_updated_at`.
- [ ] **Step 2:** Create `product_analytics` table with views/cart-adds/sales aggregates.
- [ ] **Step 3:** Implement demand, inventory, and time multipliers.
- [ ] **Step 4:** Add admin UI: recommendations, simulate, apply selected.
- [ ] **Step 5:** Write tests and migration.
- [ ] **Step 6:** Commit.

### Task 2.3: AI-Driven Personalization Engine

**Files:**
- Create: `app/services/personalization_service.py`
- Modify: `app/routers/pages.py` (homepage), `app/services/recommendation_service.py`, `app/models/user.py`
- Test: `tests/test_personalization.py`

**Interfaces:**
- Consumes: `UserEvent` interactions
- Produces: `recommend_for_user(user_id, n=10) -> list[Product]`

- [ ] **Step 1:** Add `favorite_category_id` to `User` model.
- [ ] **Step 2:** Build simple ALS-like implicit feedback model in pure Python/NumPy (avoid heavy deps).
- [ ] **Step 3:** Add cold-start fallback to trending/same-category.
- [ ] **Step 4:** Render personalized carousel on homepage for logged-in users.
- [ ] **Step 5:** Write tests and migration.
- [ ] **Step 6:** Commit.

### Task 2.4: AI Analytics Charts & Saved Reports

**Files:**
- Create: `app/services/chart_service.py`, `app/models/saved_report.py`
- Modify: `app/services/ai_analytics.py`, `app/routers/admin_analytics.py`, `app/templates/admin/analytics.html`
- Test: `tests/test_ai_analytics.py`

**Interfaces:**
- Consumes: SQL result rows + chart_type hint
- Produces: chart image bytes or Plotly JSON + saved report records

- [ ] **Step 1:** Add read-only SQL execution path.
- [ ] **Step 2:** Add `matplotlib` chart generation (bar/line/pie/table/number).
- [ ] **Step 3:** Add `SavedReport` model and CRUD UI.
- [ ] **Step 4:** Write tests.
- [ ] **Step 5:** Commit.

---

## Phase 3 — P0 Large Features

**Goal:** Implement the two largest P0 gaps that drive revenue: autonomous campaigns and WhatsApp commerce.

### Task 3.1: Autonomous Marketing Campaigns Engine

**Files:**
- Create: `app/services/campaign_engine.py`, `app/models/campaign.py`, `app/routers/admin_campaigns.py`, `app/scheduler.py`
- Modify: `app/services/abandoned_cart_service.py`, `app/services/promotion_service.py`, `app/main.py`
- Test: `tests/test_campaign_engine.py`

**Interfaces:**
- Consumes: orders, cart events, user events, email queue
- Produces: scheduled `Campaign` records and queued emails

- [ ] **Step 1:** Create `Campaign` model (name, type, status, target_audience JSON, content JSON, metrics JSON).
- [ ] **Step 2:** Implement post-purchase, win-back, new-arrival, and seasonal (Mexican holidays) flows.
- [ ] **Step 3:** Add APScheduler background jobs in `app/scheduler.py`.
- [ ] **Step 4:** Add admin "Campañas IA" tab with create/active/metrics UI.
- [ ] **Step 5:** Integrate with existing abandoned-cart recovery.
- [ ] **Step 6:** Write tests.
- [ ] **Step 7:** Commit.

### Task 3.2: Social Commerce — WhatsApp Business Bot

**Files:**
- Create: `app/services/whatsapp_service.py`, `app/routers/webhooks.py`
- Modify: `app/services/chat_service.py`, `app/config.py`, `app/main.py`
- Test: `tests/test_whatsapp.py`

**Interfaces:**
- Consumes: incoming WhatsApp messages via webhook
- Produces: replies routed through `chat_service`, optional product cards

- [ ] **Step 1:** Add WhatsApp webhook endpoint and signature verification.
- [ ] **Step 2:** Implement customer lookup/creation by phone.
- [ ] **Step 3:** Route messages to existing chat assistant and format replies for WhatsApp.
- [ ] **Step 4:** Add admin "Social Commerce" tab with pending messages/stats.
- [ ] **Step 5:** Write tests with mocked WhatsApp API.
- [ ] **Step 6:** Commit.

---

## Phase 4 — P1/P2 Features

**Goal:** Close remaining P1 and P2 innovations.

### Task 4.1: Agentic Checkout (P1)

**Files:**
- Create: `app/services/agents/checkout_agent.py`, `app/models/agent_action.py`
- Modify: `app/routers/chat.py`, `app/services/chat_service.py`
- Test: `tests/test_checkout_agent.py`

**Interfaces:**
- Consumes: chat session, cart, user profile
- Produces: confirmed order or human-escalation

- [ ] **Step 1:** Build state-machine checkout flow in plain Python.
- [ ] **Step 2:** Add confirmation gate, spending limits, audit log.
- [ ] **Step 3:** Integrate with order/payment services.
- [ ] **Step 4:** Write tests.
- [ ] **Step 5:** Commit.

### Task 4.2: AI Fraud Detection (P1)

**Files:**
- Create: `app/services/fraud_detector.py`, `app/models/fraud_score.py`
- Modify: `app/routers/payments.py`, `app/routers/admin_orders.py`
- Test: `tests/test_fraud_detection.py`

- [ ] **Step 1:** Implement feature extraction (IP velocity, account age, email domain).
- [ ] **Step 2:** Add `pyod` Isolation Forest behind runtime import.
- [ ] **Step 3:** Score orders on creation and surface risk level in admin.
- [ ] **Step 4:** Write tests.
- [ ] **Step 5:** Commit.

### Task 4.3: AI Inventory & Restock Prediction (P1)

**Files:**
- Create: `app/services/inventory_forecast.py`, `app/routers/admin_inventory.py`
- Modify: `app/models/product.py`
- Test: `tests/test_inventory_forecast.py`

- [ ] **Step 1:** Build daily sales-history query.
- [ ] **Step 2:** Add `statsforecast` or rule-based forecaster behind runtime import.
- [ ] **Step 3:** Predict stock-out dates and reorder quantities.
- [ ] **Step 4:** Add Mexican holiday calendar multipliers.
- [ ] **Step 5:** Add admin "Inventario IA" tab.
- [ ] **Step 6:** Write tests.
- [ ] **Step 7:** Commit.

### Task 4.4: Visual Search (P2)

**Files:**
- Create: `app/services/visual_search.py`, `app/models/product_embedding.py`, `app/routers/visual_search.py`
- Modify: `app/templates/base.html`
- Test: `tests/test_visual_search.py`

- [ ] **Step 1:** Add `open_clip` behind runtime import.
- [ ] **Step 2:** Index product images on upload/admin action.
- [ ] **Step 3:** Implement `/api/visual-search` endpoint.
- [ ] **Step 4:** Add storefront upload UI.
- [ ] **Step 5:** Write tests.
- [ ] **Step 6:** Commit.

### Task 4.5: AI-Powered Loyalty & Gamification Enhancements (P1)

**Files:**
- Create: `app/services/ai_loyalty_service.py`, `app/models/loyalty_quest.py`
- Modify: `app/routers/loyalty.py`, `app/routers/admin_loyalty.py`
- Test: `tests/test_ai_loyalty.py`

- [ ] **Step 1:** Add churn-risk scoring based on recency/frequency.
- [ ] **Step 2:** Add `loyalty_quests` table and progress tracking.
- [ ] **Step 3:** Implement AI-generated retention offers and birthday campaign.
- [ ] **Step 4:** Write tests.
- [ ] **Step 5:** Commit.

---

## Phase 5 — AI Marketing Department

**Goal:** Implement the hierarchical marketing department architecture (orchestrator + specialized crews) on top of completed Phase 1–4 services.

### Task 5.1: Marketing Orchestrator (CrewAI/LangGraph)

**Files:**
- Create: `app/services/agents/marketing_orchestrator.py`
- Modify: `app/services/agents/supervisor.py`
- Test: `tests/test_marketing_orchestrator.py`

- [ ] **Step 1:** Add LLM-based task classification.
- [ ] **Step 2:** Route tasks to Content/SEO/Campaign/Analytics agents.
- [ ] **Step 3:** Persist decisions to `marketing_decisions` table.
- [ ] **Step 4:** Write tests.
- [ ] **Step 5:** Commit.

### Task 5.2: Specialized Marketing Agents

**Files:**
- Create: `app/services/agents/content_agent.py`, `seo_agent.py`, `campaign_agent.py`, `analytics_agent.py`
- Modify: existing product content, analytics, and campaign services
- Test: `tests/test_marketing_agents.py`

- [ ] **Step 1:** Content Agent: blog posts, social copy, editorial workflow.
- [ ] **Step 2:** SEO Agent: keyword tracking, meta optimization, search-term suggestions.
- [ ] **Step 3:** Campaign Agent: seasonal campaign generation and scheduling.
- [ ] **Step 4:** Analytics Agent: scheduled insight reports and proactive alerts.
- [ ] **Step 5:** Write tests.
- [ ] **Step 6:** Commit.

### Task 5.3: Proactive Engine & Feedback Loop

**Files:**
- Create: `app/services/proactive_engine.py`
- Modify: `app/scheduler.py`, `app/main.py`
- Test: `tests/test_proactive_engine.py`

- [ ] **Step 1:** Define triggers: inventory_change, trending_topic, customer_behavior, competitor_movement.
- [ ] **Step 2:** Implement 6-hour monitoring loop.
- [ ] **Step 3:** Execute recommended actions via orchestrator.
- [ ] **Step 4:** Measure outcomes and feed back to decision log.
- [ ] **Step 5:** Write tests.
- [ ] **Step 6:** Commit.

---

## Execution Order & Dependencies

```
Phase 0 (Foundation) ── DONE
        │
        ▼
Phase 1 (Quick Wins) ── parallel tasks 1.1, 1.2, 1.3
        │
        ▼
Phase 2 (P0 Medium) ── 2.1, 2.2, 2.3, 2.4 (2.3 depends on user_events; 2.2 on product_analytics)
        │
        ▼
Phase 3 (P0 Large) ── 3.1, 3.2 (3.1 depends on email queue; 3.2 on chat_service)
        │
        ▼
Phase 4 (P1/P2) ── 4.1–4.5 in parallel
        │
        ▼
Phase 5 (AI Marketing Dept) ── depends on most earlier phases
```

---

## Definition of Done for the Whole Project

- [ ] All P0 innovations from the AI report are implemented and tested.
- [ ] All P1 innovations are implemented and tested.
- [ ] P2 innovations (visual search, voice) are implemented and tested.
- [ ] AI Marketing Department orchestrator + 4 specialized agents run end-to-end.
- [ ] Full test suite passes: `pytest tests/ -q`.
- [ ] Admin sidebar reflects all new tabs from the report architecture map.
- [ ] Documentation updated: README, `.env.example`, `docker-compose.yml`.

---

## Notes

- This is a multi-week roadmap. Each phase should be treated as an independently shippable milestone.
- Optional AI dependencies must remain optional; always provide graceful degradation.
- When in doubt, follow the existing patterns in `app/services/order_service.py`, `app/routers/admin_*.py`, and the existing test suite.
