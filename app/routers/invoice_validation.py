from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from app.services.invoice_advisor import advise

router = APIRouter(prefix="/invoices", tags=["invoice-validation"])


class RFCValidateRequest(BaseModel):
    rfc: str = Field(max_length=20)
    name: str = Field(default="", max_length=255)
    cp: str = Field(default="", max_length=10)


@router.post("/validate-rfc")
async def validate_rfc(data: RFCValidateRequest):
    """Public, rate-limited validation + AI guidance for checkout invoice data."""
    result = await advise(rfc_raw=data.rfc, name=data.name, cp=data.cp)
    return JSONResponse(result)
