from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.schemas.refund import RefundCreate, RefundResponse
from app.services.refund_service import refund_service
from app.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.post("/", response_model=RefundResponse)
async def create_refund(
    data: RefundCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await refund_service.create_refund_request(db, user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=List[RefundResponse])
async def get_my_refunds(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await refund_service.get_user_refunds(db, user.id)


# ── Admin routes (auth-gated) ────────────────────────────────────────────

@router.get("/admin/all", response_model=List[RefundResponse])
async def get_all_refunds(
    status: str = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return await refund_service.get_all_refunds(db, status)


@router.post("/admin/{refund_id}/approve", response_model=RefundResponse)
async def approve_refund(
    refund_id: UUID,
    admin_notes: str = "",
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    refund = await refund_service.approve_refund(db, refund_id, admin_notes)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found or already processed")
    return refund


@router.post("/admin/{refund_id}/process", response_model=RefundResponse)
async def process_refund(
    refund_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    refund = await refund_service.process_refund(db, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found or not approved")
    return refund


@router.post("/admin/{refund_id}/reject", response_model=RefundResponse)
async def reject_refund(
    refund_id: UUID,
    reason: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    refund = await refund_service.reject_refund(db, refund_id, reason)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found or already processed")
    return refund
