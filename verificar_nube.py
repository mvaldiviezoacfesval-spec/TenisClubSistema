import sys
from urllib.request import urlopen


def fetch(url):
    with urlopen(url, timeout=15) as response:
        return response.status, response.read().decode("utf-8", "ignore")


def main():
    if len(sys.argv) != 2:
        print("Uso: python verificar_nube.py https://tu-url-publica.onrender.com")
        return 1

    base_url = sys.argv[1].rstrip("/")
    checks = ["/health", "/", "/socios", "/ventas", "/reportes"]
    failed = False

    for path in checks:
        status, body = fetch(base_url + path)
        ok = 200 <= status < 400
        print(f"{path}: {status}")
        if not ok:
            failed = True
        if path == "/health" and '"ok"' not in body:
            print("Healthcheck no devolvio status ok")
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
