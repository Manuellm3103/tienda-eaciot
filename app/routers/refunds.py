from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.refund import RefundCreate, RefundResponse
from app.services.refund_service import refund_service

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.post("/", response_model=RefundResponse)
async def create_refund(data: RefundCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        return await refund_service.create_refund_request(db, UUID(user_id), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=List[RefundResponse])
async def get_my_refunds(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await refund_service.get_user_refunds(db, UUID(user_id))


# Admin routes
@router.get("/admin/all", response_model=List[RefundResponse])
async def get_all_refunds(status: str = None, db: AsyncSession = Depends(get_db)):
    return await refund_service.get_all_refunds(db, status)


@router.post("/admin/{refund_id}/approve", response_model=RefundResponse)
async def approve_refund(refund_id: UUID, admin_notes: str = "", db: AsyncSession = Depends(get_db)):
    refund = await refund_service.approve_refund(db, refund_id, admin_notes)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found or already processed")
    return refund


@router.post("/admin/{refund_id}/process", response_model=RefundResponse)
async def process_refund(refund_id: UUID, db: AsyncSession = Depends(get_db)):
    refund = await refund_service.process_refund(db, refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found or not approved")
    return refund


@router.post("/admin/{refund_id}/reject", response_model=RefundResponse)
async def reject_refund(refund_id: UUID, reason: str, db: AsyncSession = Depends(get_db)):
    refund = await refund_service.reject_refund(db, refund_id, reason)
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found or already processed")
    return refund
