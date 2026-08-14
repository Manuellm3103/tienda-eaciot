import pytest
from app.services.rfc_validator import validate_format, normalize, validate_cp
from app.services.invoice_advisor import advise


def test_normalize_uppercases_and_strips():
    assert normalize("  eac-2403183f0 ") == "EAC2403183F0"


def test_validate_format_moral_rfc():
    result = validate_format("EAC2403183F0")
    assert result["valid"] is True
    assert result["tipo"] == "moral"
    assert result["normalized"] == "EAC2403183F0"


def test_validate_format_fisica_rfc():
    result = validate_format("GODE561231GR8")
    assert result["valid"] is True
    assert result["tipo"] == "fisica"


def test_validate_format_rejects_short():
    result = validate_format("EAC2403")
    assert result["valid"] is False
    assert any("caracteres" in e for e in result["errors"])


def test_validate_format_publico_general():
    result = validate_format("XAXX010101000")
    assert result["valid"] is True
    assert result["is_publico"] is True


def test_validate_format_detects_letter_o_typo():
    result = validate_format("EAC24O3183F0")  # 'O' en vez de '0'
    assert any("O" in w or "cero" in w.lower() for w in result["warnings"])


def test_validate_cp():
    assert validate_cp("62410")["valid"] is True
    assert validate_cp("6241")["valid"] is False
    assert validate_cp("abcde")["valid"] is False


@pytest.mark.asyncio
async def test_advise_returns_suggestion_for_bad_rfc():
    result = await advise(rfc_raw="123", name="Cliente", cp="62410")
    assert result["rfc"]["valid"] is False
    assert result["suggestion"]  # always non-empty


@pytest.mark.asyncio
async def test_advise_valid_rfc():
    result = await advise(rfc_raw="EAC2403183F0", name="EMANUEL AZUR", cp="62410")
    assert result["rfc"]["valid"] is True
    assert result["cp"]["valid"] is True
    assert result["rfc"]["exists_at_sat"] in (None, True, False)  # not configured -> None
