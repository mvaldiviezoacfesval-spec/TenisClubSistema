# Obtener el link publico del sistema

El sistema ya no debe usarse desde `127.0.0.1`. Para tener un link propio necesitas subir este proyecto a una plataforma cloud. La configuracion lista esta en `render.yaml`.

## Opcion recomendada: Render

1. Crea o abre tu cuenta en Render:
   `https://dashboard.render.com`
2. Sube este proyecto a GitHub.
3. En Render entra a:
   `https://dashboard.render.com/blueprints/new`
4. Selecciona el repositorio del sistema.
5. Render detectara `render.yaml`.
6. Confirma el Blueprint.
7. Espera a que el deploy termine.
8. Render entregara un link parecido a:
   `https://tenis-club-sistema.onrender.com`

Ese sera el link real del sistema.

## Confirmar datos sincronizados

1. Entra al link publico desde una computadora.
2. Registra un socio de prueba.
3. Entra al mismo link desde otro navegador, celular o computadora.
4. El socio debe aparecer porque todos usan la misma base en `/data/tenis_club.db`.

## Verificacion automatica

Cuando tengas el link, ejecuta:

```powershell
python verificar_nube.py https://tenis-club-sistema.onrender.com
```

Debe responder `200` en todas las rutas.

## Importante

El archivo `tenis_club.db` local no se sube al cloud. En Render la base se crea y guarda en el disco persistente definido en `render.yaml`:

```yaml
disk:
  name: tenis-club-data
  mountPath: /data
  sizeGB: 1
```
