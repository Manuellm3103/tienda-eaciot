from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.dependencies import require_admin
from app.models.chat import ChatMessage
from app.services.rag_service import rag_service

router = APIRouter(
    prefix="/admin/rag",
    tags=["admin-rag"],
    dependencies=[Depends(require_admin)],
)

# Canned answers emitted when the LLM backend is unavailable (fallback responses).
FALLBACK_MARKERS = (
    "El asistente AI está cargando",
    "No encontré productos para esa búsqueda",
)


@router.post("/reindex")
async def reindex_products(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Re-index the product catalog into the vector store."""
    count = await rag_service.index_products(db)
    return JSONResponse({"status": "ok", "indexed_products": count})


@router.get("/stats")
async def rag_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Intent statistics for the AI shopping assistant.

    Derives intent distribution from the agent that handled each message
    (supervisor routes to product_advisor or copywriter), plus conversation
    volume and the current RAG index size.
    """
    intent_rows = await db.execute(
        select(ChatMessage.agent_name, func.count(ChatMessage.id))
        .where(ChatMessage.agent_name.isnot(None))
        .group_by(ChatMessage.agent_name)
    )
    intent_distribution = {row[0]: row[1] for row in intent_rows.all()}

    total_messages = (await db.execute(select(func.count(ChatMessage.id)))).scalar_one()
    total_sessions = (
        await db.execute(select(func.count(func.distinct(ChatMessage.session_id))))
    ).scalar_one()
    user_messages = (
        await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.role == "user")
        )
    ).scalar_one()

    return JSONResponse(
        {
            "status": "ok",
            "intent_distribution": intent_distribution,
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "user_messages": user_messages,
            "rag_indexed_products": rag_service.size(),
        }
    )


@router.get("/fallbacks")
async def fallback_responses(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List recent conversations where the assistant fell back to a canned
    answer (LLM backend unavailable or no products matched)."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc())
        .limit(500)
    )

    fallbacks = []
    for m in result.scalars():
        content = m.content or ""
        if any(marker in content for marker in FALLBACK_MARKERS):
            fallbacks.append(
                {
                    "session_id": m.session_id,
                    "agent": m.agent_name,
                    "content": content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
            )

    return JSONResponse({"status": "ok", "count": len(fallbacks), "fallbacks": fallbacks})
