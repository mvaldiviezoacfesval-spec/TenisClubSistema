#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/mvaldiviezoacfesval-spec/TenisClubSistema.git"
PROJECT_HOME="$HOME/TenisClubSistema"
WSGI_FILE="/var/www/${USER}_pythonanywhere_com_wsgi.py"

echo "Preparando Sistema Contable Tenis Club en PythonAnywhere..."

if [ -d "$PROJECT_HOME/.git" ]; then
  cd "$PROJECT_HOME"
  git pull
else
  git clone "$REPO_URL" "$PROJECT_HOME"
  cd "$PROJECT_HOME"
fi

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
else
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -c "from database import init_db; init_db(); print('Base de datos inicializada')"

if [ -w "$(dirname "$WSGI_FILE")" ]; then
  cp pythonanywhere_wsgi.py "$WSGI_FILE"
  echo "Archivo WSGI actualizado: $WSGI_FILE"
else
  echo "No pude escribir automaticamente el WSGI."
  echo "Cuando crees la Web App, abre el archivo WSGI y pega el contenido de:"
  echo "$PROJECT_HOME/pythonanywhere_wsgi.py"
fi

echo ""
echo "Listo."
echo "Ahora en la pestana Web de PythonAnywhere configura:"
echo "Source code: $PROJECT_HOME"
echo "Working directory: $PROJECT_HOME"
echo "Virtualenv: $PROJECT_HOME/venv"
echo "Luego presiona Reload."
echo "Tu link sera: https://${USER}.pythonanywhere.com"
