# Sistema Contable Milagro Tenis Club en la nube

Este proyecto ya esta preparado para publicarse como una aplicacion Flask con una base SQLite en disco persistente. Al quedar en la nube, todos los usuarios entran al mismo URL y ven los mismos datos sincronizados.

## Como funciona la sincronizacion

- La app usa una sola base de datos central.
- En local usa `tenis_club.db`.
- En nube usa la variable `DB_PATH`, por ejemplo `/data/tenis_club.db`.
- El archivo `render.yaml` crea un disco persistente en Render montado en `/data`.
- Mientras la app use ese disco persistente, los datos no dependen de la computadora donde se abra el sistema.

## Publicar en Render

1. Sube la carpeta `TenisClubSistema` a un repositorio de GitHub.
2. En Render, crea un nuevo servicio usando `Blueprint`.
3. Selecciona el repositorio.
4. Render detectara `render.yaml`.
5. Confirma la creacion del servicio.
6. Cuando termine el despliegue, abre el URL publico que Render entrega.

El blueprint configura:

- `DB_PATH=/data/tenis_club.db`
- disco persistente `tenis-club-data`
- comando de inicio con Gunicorn
- verificacion de salud en `/health`

## Verificar que los datos estan sincronizados

1. Abre el URL publico en una computadora.
2. Registra un socio, factura o movimiento.
3. Abre el mismo URL publico desde otro dispositivo o navegador.
4. El dato debe aparecer ahi tambien.

Tambien puedes validar que la app desplegada responde con:

```powershell
python verificar_nube.py https://tu-url-publica.onrender.com
```

Debe mostrar `200` en `/health`, `/`, `/socios`, `/ventas` y `/reportes`.

## Importante sobre los datos

No uses el archivo local `tenis_club.db` para produccion. En Render los datos se guardan en `/data/tenis_club.db`, que esta conectado al disco persistente `tenis-club-data`.

Si el servicio se crea sin disco persistente, los datos se pueden perder al reiniciar o redesplegar. El archivo `render.yaml` ya incluye el disco; no lo elimines.

## Ejecutar localmente

```powershell
pip install -r requirements.txt
python app.py
```

Luego abre:

```text
http://127.0.0.1:5000/
```

## Variables utiles

```text
DB_PATH=/data/tenis_club.db
SECRET_KEY=una-clave-segura
PORT=5000
FLASK_DEBUG=0
```
