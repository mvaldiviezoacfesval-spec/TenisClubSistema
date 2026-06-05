# Publicar gratis en PythonAnywhere

Esta opcion usa una sola plataforma. El link publico queda asi:

```text
https://TU_USUARIO.pythonanywhere.com
```

La base `tenis_club.db` queda guardada en tu carpeta de PythonAnywhere, asi que cuando abras el link desde cualquier celular o computadora veras los mismos datos.

## Pasos sin Render ni Turso

1. Entra a `https://www.pythonanywhere.com`
2. Crea una cuenta gratis.
3. Ve a la pestana **Consoles**.
4. Abre una consola **Bash**.
5. Ejecuta este unico comando:

```bash
bash <(curl -s https://raw.githubusercontent.com/mvaldiviezoacfesval-spec/TenisClubSistema/main/setup_pythonanywhere.sh)
```

6. Ve a la pestana **Web**.
7. Click en **Add a new web app**.
8. Elige **Manual configuration**.
9. Elige Python 3.12 si aparece; si no, elige la version Python 3 disponible.
10. En **Code**, cambia:

```text
Source code: /home/TU_USUARIO/TenisClubSistema
Working directory: /home/TU_USUARIO/TenisClubSistema
```

11. En **Virtualenv**, coloca:

```text
/home/TU_USUARIO/TenisClubSistema/venv
```

12. Abre el archivo WSGI.
13. Borra su contenido.
14. Pega el contenido de `pythonanywhere_wsgi.py` si el script no lo hizo automaticamente.
15. Debajo de `APP_USERNAME`, agrega tu contrasena privada:

```python
os.environ["APP_PASSWORD"] = "Directiva2026"
```

16. Guarda.
17. Click en **Reload**.

## Verificar

Abre:

```text
https://TU_USUARIO.pythonanywhere.com/health
```

Debe salir:

```json
{"status":"ok"}
```

Luego abre:

```text
https://TU_USUARIO.pythonanywhere.com
```

Registra un socio desde una computadora y revisa desde otro navegador o celular. Debe aparecer el mismo dato.
