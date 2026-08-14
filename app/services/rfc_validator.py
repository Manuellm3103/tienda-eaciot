"""RFC validation for the checkout / invoicing flow.

Two layers:
1. Deterministic format + typo detection (free, instant, catches most errors).
2. Existence check against the SAT via the PAC's `rfc_valid` (authoritative,
   but requires PAC credentials and is network-bound — best-effort).

The homoclave (last 3 chars) CANNOT be verified from the RFC alone — SAT
generates it from the legal name, so the PAC/SAT lookup is the only source of
truth for "does this RFC exist".
"""
import re
import time
from typing import Optional

from app.config import settings

# Persona moral: 3 letras + 6 dígitos + 3 homoclave (12 total)
# Persona física: 4 letras + 6 dígitos + 3 homoclave (13 total)
_RFC_MORAL = re.compile(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$")
_RFC_FISICA = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
_RFC_GENERIC = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")

PUBLICO_EN_GENERAL = "XAXX010101000"

# Common visual confusions in RFCs typed by hand.
_CONFUSIONS = {
    "O": ("¿Usaste la letra 'O'?", "La 'O' suele ser un cero (0) o parte del RFC, revisa."),
    "I": ("¿Usaste la letra 'I'?", "La 'I' suele confundirse con el uno (1)."),
    "S": ("¿Usaste la letra 'S'?", "La 'S' a veces es un cinco (5)."),
    " ": ("Hay espacios", "El RFC no lleva espacios."),
    "-": ("Hay guiones", "El RFC no lleva guiones."),
}

# Simple in-memory cache for SAT existence lookups (avoid repeat PAC billing).
_existence_cache: dict[str, tuple[float, Optional[bool]]] = {}
_EXISTENCE_TTL = 3600  # 1 hour


def normalize(rfc: str) -> str:
    """Uppercase, strip spaces/dashes, replace common confusions."""
    if not rfc:
        return ""
    return (
        rfc.upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .strip()
    )


def validate_format(rfc: str) -> dict:
    """Deterministic RFC format validation. Never raises."""
    raw = (rfc or "").strip()
    normalized = normalize(raw)

    if not normalized:
        return {
            "valid": False,
            "normalized": "",
            "tipo": None,
            "is_publico": False,
            "errors": ["El RFC está vacío."],
            "warnings": [],
        }

    if normalized == PUBLICO_EN_GENERAL:
        return {
            "valid": True,
            "normalized": normalized,
            "tipo": "publico_general",
            "is_publico": True,
            "errors": [],
            "warnings": [],
        }

    errors: list[str] = []
    warnings: list[str] = []

    # Typo heuristics on the raw input (before normalization hides them).
    for char, (title, hint) in _CONFUSIONS.items():
        if char in raw:
            warnings.append(f"{title} {hint}")

    if not _RFC_GENERIC.match(normalized):
        # Give a targeted message by length/structure.
        if len(normalized) < 12:
            errors.append(
                f"El RFC tiene {len(normalized)} caracteres; debe tener 12 (moral) o 13 (física)."
            )
        elif len(normalized) > 13:
            errors.append(
                f"El RFC tiene {len(normalized)} caracteres; sobran caracteres."
            )
        elif not re.match(r"^[A-ZÑ&]{3,4}", normalized):
            errors.append("El RFC debe empezar con 3 (moral) o 4 (física) letras.")
        elif not re.match(r".{3,4}\d{6}", normalized):
            errors.append("El RFC debe contener 6 dígitos (la fecha de constitución o nacimiento).")
        else:
            errors.append(
                "El RFC no tiene un formato válido. Formato: letras + 6 dígitos + 3 caracteres."
            )
        return {
            "valid": False,
            "normalized": normalized,
            "tipo": "moral" if len(normalized) == 12 else "fisica",
            "is_publico": False,
            "errors": errors,
            "warnings": warnings,
        }

    tipo = "moral" if _RFC_MORAL.match(normalized) else "fisica"
    return {
        "valid": True,
        "normalized": normalized,
        "tipo": tipo,
        "is_publico": False,
        "errors": [],
        "warnings": warnings,
    }


def _pac_rfc_valid(rfc: str) -> Optional[bool]:
    """Ask the PAC/SAT whether the RFC exists. Returns None if unavailable."""
    try:
        from satcfdi.pacs import Environment
        from satcfdi.pacs.swsapien import SWSapien

        env = (
            Environment.TEST
            if settings.pac_environment.lower() == "test"
            else Environment.PRODUCTION
        )
        pac = SWSapien(
            user=settings.pac_username or None,
            password=settings.pac_password or None,
            environment=env,
        )
        return bool(pac.rfc_valid(rfc))
    except Exception:
        return None


async def validate_existence(rfc: str) -> Optional[bool]:
    """Check RFC existence against SAT (cached, best-effort, async-friendly)."""
    normalized = normalize(rfc)
    if not normalized or normalized == PUBLICO_EN_GENERAL:
        return True

    now = time.time()
    cached = _existence_cache.get(normalized)
    if cached and (now - cached[0]) < _EXISTENCE_TTL:
        return cached[1]

    if not (settings.pac_username and settings.pac_password):
        return None  # not configured — can't check existence

    import asyncio

    result = await asyncio.to_thread(_pac_rfc_valid, normalized)
    _existence_cache[normalized] = (now, result)
    return result


def validate_cp(cp: str) -> dict:
    """Validate a Mexican postal code (5 digits)."""
    cleaned = (cp or "").strip()
    if not cleaned:
        return {"valid": False, "errors": ["El código postal está vacío."]}
    if not re.match(r"^\d{5}$", cleaned):
        return {
            "valid": False,
            "errors": ["El código postal debe tener exactamente 5 dígitos."],
        }
    return {"valid": True, "errors": []}
