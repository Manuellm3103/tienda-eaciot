from decimal import Decimal, InvalidOperation
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_token"] = lambda request: getattr(request.state, "csrf_token", "")


def _money(value) -> str:
    """Formatea un precio (Decimal) como MXN con separador de miles.

    Ej: Decimal("16000.00") -> "$16,000.00". None/0 -> "Pendiente".
    """
    if value is None:
        return "Pendiente"
    try:
        return f"${Decimal(str(value)):,.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return f"${value}"


templates.env.filters["money"] = _money
