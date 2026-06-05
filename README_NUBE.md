# Sistema Contable Milagro Tenis Club en la nube

Este proyecto ya esta preparado para publicarse como una aplicacion Flask con una base SQLite/libSQL en Turso. Al quedar en la nube, todos los usuarios entran al mismo URL y ven los mismos datos sincronizados.

## Como funciona la sincronizacion

- La app usa una sola base de datos central.
- En local usa `tenis_club.db`.
- En nube usa Turso con `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`.
- `DB_PATH=/tmp/tenis_club.db` es solo una replica temporal dentro de Render.
- Los datos reales viven en Turso, no en el servidor local ni en el disco de Render.

## Publicar en Render

1. Crea una base gratis en Turso.
2. Copia `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`.
3. En Render, crea un nuevo servicio usando `Blueprint`.
4. Selecciona el repositorio.
5. Render detectara `render.yaml`.
6. Cuando Render pida variables, pega `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`.
7. Confirma la creacion del servicio.
8. Cuando termine el despliegue, abre el URL publico que Render entrega.

El blueprint configura:

- `DB_PATH=/tmp/tenis_club.db`
- conexion a Turso mediante `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`
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

No uses el archivo local `tenis_club.db` para produccion. En Render el archivo de `/tmp` es temporal; la sincronizacion real se hace con Turso.

Si no configuras `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`, los datos no quedaran sincronizados en nube.

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
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...
SECRET_KEY=una-clave-segura
PORT=5000
FLASK_DEBUG=0
```
