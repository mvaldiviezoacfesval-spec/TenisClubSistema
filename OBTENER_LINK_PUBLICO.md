# Obtener el link publico del sistema

El sistema ya no debe usarse desde `127.0.0.1`. Para tener un link propio necesitas subir este proyecto a una plataforma cloud. La configuracion lista esta en `render.yaml` y usa Render Free + Turso Free para evitar pago.

## Crear base gratis en Turso

1. Entra a `https://turso.tech`
2. Crea una cuenta gratis.
3. Crea una base llamada `tenis-club-sistema`.
4. Copia:
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`

Turso tiene plan gratis sin tarjeta. Esta base sera donde quedan los datos sincronizados.

## Opcion recomendada: Render

1. Crea o abre tu cuenta en Render:
   `https://dashboard.render.com`
2. Sube este proyecto a GitHub.
   Si ya creaste el repositorio, ejecuta desde esta carpeta:

   ```powershell
   .\SUBIR_A_GITHUB.ps1 https://github.com/USUARIO/REPOSITORIO.git
   ```

3. En Render entra a:
   `https://dashboard.render.com/blueprints/new`
4. Selecciona el repositorio del sistema.
5. Render detectara `render.yaml`.
6. Cuando pida variables, pega:
   - `TURSO_DATABASE_URL`
   - `TURSO_AUTH_TOKEN`
7. Confirma el Blueprint.
8. Espera a que el deploy termine.
9. Render entregara un link parecido a:
   `https://tenis-club-sistema.onrender.com`

Ese sera el link real del sistema.

## Confirmar datos sincronizados

1. Entra al link publico desde una computadora.
2. Registra un socio de prueba.
3. Entra al mismo link desde otro navegador, celular o computadora.
4. El socio debe aparecer porque todos usan la misma base en Turso.

## Verificacion automatica

Cuando tengas el link, ejecuta:

```powershell
python verificar_nube.py https://tenis-club-sistema.onrender.com
```

Debe responder `200` en todas las rutas.

## Importante

El archivo `tenis_club.db` local no se sube al cloud. En Render se usa una replica temporal en `/tmp`, y la base real vive en Turso:

```yaml
envVars:
  - key: TURSO_DATABASE_URL
    sync: false
  - key: TURSO_AUTH_TOKEN
    sync: false
```
