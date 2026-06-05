"""
Plantilla WSGI para PythonAnywhere.

En PythonAnywhere, reemplaza TU_USUARIO por tu nombre de usuario y pega este
contenido en el archivo WSGI de la pestana Web.
"""

import os
import sys

USERNAME = "TU_USUARIO"
PROJECT_HOME = f"/home/{USERNAME}/TenisClubSistema"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.environ["DB_PATH"] = os.path.join(PROJECT_HOME, "tenis_club.db")
os.environ["FLASK_DEBUG"] = "0"

from app import create_app

application = create_app()
