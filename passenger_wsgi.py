import sys
import os

# Agregar directorio del proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app

# Passenger necesita esta variable
application = app
