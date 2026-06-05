"""
Plantilla WSGI para PythonAnywhere.

En PythonAnywhere, reemplaza TU_USUARIO por tu nombre de usuario y pega este
contenido en el archivo WSGI de la pestana Web.
"""

import os
import sys
import getpass

USERNAME = getpass.getuser()
PROJECT_HOME = f"/home/{USERNAME}/TenisClubSistema"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.environ["DB_PATH"] = os.path.join(PROJECT_HOME, "tenis_club.db")
os.environ["FLASK_DEBUG"] = "0"
os.environ.setdefault("APP_USERNAME", "administraciontenisclub")
# En PythonAnywhere, agrega esta variable manualmente con la contrasena privada.
# os.environ["APP_PASSWORD"] = "TU_CONTRASENA"

from app import create_app

application = create_app()
