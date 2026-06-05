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
5. Ejecuta estos comandos:

```bash
git clone https://github.com/mvaldiviezoacfesval-spec/TenisClubSistema.git
cd TenisClubSistema
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "from database import init_db; init_db()"
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
14. Pega el contenido de `pythonanywhere_wsgi.py`.
15. Cambia `TU_USUARIO` por tu usuario real de PythonAnywhere.
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
