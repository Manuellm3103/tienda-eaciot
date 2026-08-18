from sqlalchemy import Column, String, Text
from app.database import Base


class AppSetting(Base):
    """Almacén clave/valor para preferencias operativas del admin.

    Se usa para persistir cosas que hoy solo viven en .env (p. ej. el modelo de
    LLM elegido desde el dashboard) sin tener que redesplegar.
    """

    __tablename__ = "app_settings"

    key = Column(String(120), primary_key=True)
    value = Column(Text)
