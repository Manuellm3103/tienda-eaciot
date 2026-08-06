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
