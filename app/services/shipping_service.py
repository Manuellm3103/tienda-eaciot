from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from app.models.shipping import ShippingAddress, Shipment
from app.schemas.shipping import ShippingAddressCreate, ShipmentCreate


class ShippingService:
    # Shipping rates by zone (simplified)
    SHIPPING_RATES = {
        "local": {"base": 50, "per_kg": 10},
        "national": {"base": 100, "per_kg": 25},
        "international": {"base": 500, "per_kg": 100},
    }
    
    def calculate_shipping_cost(self, weight: Decimal, destination_state: str, origin_state: str = "CDMX", destination_country: str = "México") -> Decimal:
        """Calculate shipping cost based on weight, destination state and country"""
        # International shipping
        if destination_country.lower() not in ("méxico", "mexico", ""):
            zone = "international"
        elif destination_state.lower() == origin_state.lower():
            zone = "local"
        elif destination_state.lower() in ["méxico", "estado de méxico", "cdmx"]:
            zone = "local"
        else:
            zone = "national"
        
        rate = self.SHIPPING_RATES[zone]
        cost = Decimal(str(rate["base"])) + (weight * Decimal(str(rate["per_kg"])))
        return cost.quantize(Decimal("0.01"))
    
    async def create_address(self, db: AsyncSession, user_id: UUID, data: ShippingAddressCreate) -> ShippingAddress:
        """Create shipping address"""
        # If this is default, unset other defaults
        if data.is_default:
            result = await db.execute(
                select(ShippingAddress).where(
                    ShippingAddress.user_id == user_id,
                    ShippingAddress.is_default == "1"
                )
            )
            for addr in result.scalars().all():
                addr.is_default = "0"
        
        address = ShippingAddress(
            user_id=user_id,
            **data.model_dump(exclude={"is_default"}),
            is_default="1" if data.is_default else "0",
        )
        db.add(address)
        await db.flush()
        return address
    
    async def get_user_addresses(self, db: AsyncSession, user_id: UUID) -> List[ShippingAddress]:
        """Get all addresses for a user"""
        result = await db.execute(
            select(ShippingAddress)
            .where(ShippingAddress.user_id == user_id)
            .order_by(ShippingAddress.is_default.desc(), ShippingAddress.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_address(self, db: AsyncSession, address_id: UUID) -> Optional[ShippingAddress]:
        """Get address by ID"""
        result = await db.execute(select(ShippingAddress).where(ShippingAddress.id == address_id))
        return result.scalar_one_or_none()
    
    async def create_shipment(self, db: AsyncSession, data: ShipmentCreate) -> Shipment:
        """Create shipment"""
        # Generate tracking URL based on carrier
        tracking_url = None
        if data.tracking_number:
            carrier_urls = {
                "fedex": f"https://www.fedex.com/fedextrack/?trknbr={data.tracking_number}",
                "dhl": f"https://www.dhl.com/en/express/tracking.html?AWB={data.tracking_number}",
                "estafeta": f"https://www.estafeta.com/Herramientas/Rastreo?cb={data.tracking_number}",
                "99minutos": f"https://www.99minutos.com/tracking/{data.tracking_number}",
            }
            tracking_url = carrier_urls.get(data.carrier.lower())
        
        data_dict = data.model_dump()
        # String(36) PK in SQLite — always bind order_id as str, never UUID.
        data_dict["order_id"] = str(data_dict["order_id"])
        shipment = Shipment(
            **data_dict,
            tracking_url=tracking_url,
        )
        db.add(shipment)
        await db.flush()
        return shipment
    
    async def update_shipment_status(self, db: AsyncSession, shipment_id: UUID, status: str) -> Optional[Shipment]:
        """Update shipment status"""
        result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
        shipment = result.scalar_one_or_none()
        
        if not shipment:
            return None
        
        shipment.status = status
        if status == "delivered":
            from datetime import datetime
            shipment.delivered_at = datetime.utcnow()
        
        await db.flush()
        return shipment
    
    async def get_order_shipment(self, db: AsyncSession, order_id: UUID) -> Optional[Shipment]:
        """Get shipment for an order"""
        result = await db.execute(select(Shipment).where(Shipment.order_id == order_id))
        return result.scalar_one_or_none()

    async def list_shipments(self, db: AsyncSession, limit: int = 100) -> list[dict]:
        """Admin view: shipments joined with order + customer info."""
        from app.models.order import Order
        from app.models.user import User

        result = await db.execute(
            select(Shipment).order_by(Shipment.created_at.desc()).limit(limit)
        )
        shipments = result.scalars().all()

        rows = []
        for s in shipments:
            order = await db.get(Order, s.order_id)
            user = await db.get(User, order.user_id) if order else None
            rows.append(
                {
                    "id": str(s.id),
                    "order_id": str(s.order_id),
                    "carrier": s.carrier,
                    "tracking_number": s.tracking_number,
                    "tracking_url": s.tracking_url,
                    "status": s.status,
                    "customer_email": user.email if user else None,
                    "customer_name": (user.name or user.email) if user else "—",
                    "total": float(order.total_amount) if order else 0.0,
                }
            )
        return rows

    async def assign_tracking(
        self,
        db: AsyncSession,
        shipment_id: UUID,
        carrier: str,
        tracking_number: str,
    ) -> Optional[Shipment]:
        """Assign a carrier + tracking number and regenerate the tracking URL."""
        result = await db.execute(
            select(Shipment).where(Shipment.id == shipment_id)
        )
        shipment = result.scalar_one_or_none()
        if not shipment:
            return None
        shipment.carrier = carrier
        shipment.tracking_number = tracking_number

        carrier_urls = {
            "fedex": f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}",
            "dhl": f"https://www.dhl.com/en/express/tracking.html?AWB={tracking_number}",
            "estafeta": f"https://www.estafeta.com/Herramientas/Rastreo?cb={tracking_number}",
            "99minutos": f"https://www.99minutos.com/tracking/{tracking_number}",
            "correos": f"https://www.correosdemexico.gob.mx/ServiciosLinea/Paginas/ccpost.aspx?c={tracking_number}",
        }
        shipment.tracking_url = carrier_urls.get(carrier.lower())
        await db.flush()
        return shipment


shipping_service = ShippingService()
