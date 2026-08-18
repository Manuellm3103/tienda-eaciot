"""Automatización completa del deploy de Render — sin tocar el dashboard.

Un comando hace todo:
  1. Descubre el servicio (por nombre o id) vía API de Render.
  2. Sube el .env completo (reemplaza TODAS las environment variables).
  3. Opcional: sube el CSD como Secret Files (/etc/secrets/CSD.cer + CSD.key).
  4. Dispara un deploy nuevo.
  5. Espera /health en https://tienda.eaciot.com hasta que responda 200.

Único requisito humano (una sola vez, 30 segundos):
  Render dashboard -> Account Settings -> API Keys -> Create API Key.
  Es la única pieza que ningún script puede hacer por ti (requiere tu login).

Uso:
  set RENDER_API_KEY=rnd_tu_key
  python scripts/render_deploy.py                 # env + deploy
  python scripts/render_deploy.py --csd           # env + CSD + deploy
  python scripts/render_deploy.py --list          # lista tus servicios

El .env se lee de ~/.config/tienda-eaciot/render.env
(se puede cambiar con --env-file).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RENDER_API = "https://api.render.com/v1"
ENV_FILE = Path.home() / ".config" / "tienda-eaciot" / "render.env"
REPO_ROOT = Path(__file__).resolve().parent.parent
CSD_CER = REPO_ROOT / "csd" / "CSD EAC240318.cer"
CSD_KEY = REPO_ROOT / "csd" / "CSD_EMANUEL_AZUR_CORP_EAC2403183F0_20241019_012905.key"
HEALTH_URL = "https://tienda.eaciot.com/health"
SERVICE_NAME = "tienda-eaciot"


def api(method: str, path: str, api_key: str, body=None, content_type="application/json") -> dict:
    url = f"{RENDER_API}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    data = None
    if body is not None:
        if content_type == "application/json":
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            data = body
            headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Render API {exc.code} en {method} {path}: {detail[:400]}") from exc


def load_env(path: str) -> dict:
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def find_service(api_key: str) -> dict:
    services = api("GET", "/services?limit=100", api_key)
    for svc in services:
        if svc.get("service", {}).get("name") == SERVICE_NAME:
            return svc["service"]
        if svc.get("name") == SERVICE_NAME:
            return svc
    raise SystemExit(
        f"No encontré un servicio llamado '{SERVICE_NAME}'.\n"
        "Corre: python scripts/render_deploy.py --list  y pasa --service <id>."
    )


def list_services(api_key: str) -> None:
    services = api("GET", "/services?limit=100", api_key)
    print("Tus servicios en Render:")
    for svc in services:
        name = svc.get("name")
        sid = svc.get("id")
        stype = svc.get("type")
        print(f"  {name}  (id={sid}, type={stype})")
    if not services:
        print("  (ninguno)")


def put_env_vars(api_key: str, service_id: str, env: dict) -> None:
    # Render API: cada variable va como {"key": ..., "value": ...} (NO "name").
    # Render 400 "empty environment variable key" = campo mal nombrado o vacío.
    payload = [
        {"key": k, "value": v}
        for k, v in env.items()
        if k and v != ""
    ]
    api("PUT", f"/services/{service_id}/env-vars", api_key, body=payload)
    skipped = [k for k, v in env.items() if v == ""]
    print(f"✓ {len(payload)} variables subidas (reemplazo total)"
          + (f" — omitidas por vacías: {', '.join(skipped)}" if skipped else ""))


def multipart_file(field: str, filename: str, content: bytes, boundary: str) -> bytes:
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    return head + content + b"\r\n"


def upload_csd(api_key: str, service_id: str) -> None:
    """Render Secret Files: el nombre del archivo es la ruta montada en /etc/secrets/."""
    boundary = "----tienda" + uuid.uuid4().hex
    body = b""
    body += multipart_file("file", "CSD.cer", CSD_CER.read_bytes(), boundary)
    body += multipart_file("file", "CSD.key", CSD_KEY.read_bytes(), boundary)
    body += f"--{boundary}--\r\n".encode("utf-8")
    api("POST", f"/services/{service_id}/secret-files", api_key,
        body=body, content_type=f"multipart/form-data; boundary={boundary}")
    print("✓ CSD subido como Secret Files (/etc/secrets/CSD.cer + CSD.key)")


def trigger_deploy(api_key: str, service_id: str) -> dict:
    resp = api("POST", f"/services/{service_id}/deploys", api_key, body={})
    deploy = resp if "id" in resp else resp.get("deploy", {})
    print(f"✓ Deploy disparado (id={deploy.get('id', '?')})")
    return deploy


def wait_health(max_wait: int = 300) -> bool:
    print(f"Esperando {HEALTH_URL} ...")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=10) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    print(f"✓ TIENDA VIVA: {json.dumps(body)}")
                    return True
        except Exception:
            pass
        time.sleep(10)
    print(f"⚠ {HEALTH_URL} no respondió 200 en {max_wait}s — revisa el deploy en el dashboard.")
    return False


def _revive_products(api_key: str, service_id: str, env_file: str) -> None:
    """Recupera los productos apagados por el botón Eliminar viejo.

    Render free no incluye Shell, así que la reactivación corre en el release:
    se inyecta AUTO_REVIVE_PRODUCTS=true y se dispara un deploy.

    IMPORTANTE: la fuente de verdad es el .env completo (render.env). Se
    RESTAURA TODO el bloque de variables, no solo la flag — un GET+PUT parcial
    con el formato envuelto del API de Render había dejado el servicio con una
    sola variable (lección aprendida).
    """
    print("♻ Recuperación de productos (sin Shell, vía release del deploy)...")
    env = load_env(env_file)
    env["AUTO_REVIVE_PRODUCTS"] = "true"
    payload = [{"key": k, "value": v} for k, v in env.items() if k and v != ""]
    api("PUT", f"/services/{service_id}/env-vars", api_key, body=payload)
    print(f"✓ {len(payload)} variables restauradas + AUTO_REVIVE_PRODUCTS=true")
    trigger_deploy(api_key, service_id)
    print("⏳ El deploy corre revive_products.py (reactiva los inactivos) y")
    print("   bootstrap.py (sincroniza el admin con ADMIN_EMAIL/ADMIN_PASSWORD).")
    print("   Para quitar el modo revive después: python scripts\\render_deploy.py --unrevive")
    wait_health()


def _unrevive_products(api_key: str, service_id: str, env_file: str) -> None:
    """Restaura el .env completo SIN la flag de revive y redeploya."""
    env = load_env(env_file)
    payload = [{"key": k, "value": v} for k, v in env.items() if k and v != ""]
    api("PUT", f"/services/{service_id}/env-vars", api_key, body=payload)
    print(f"✓ Modo revive quitado ({len(payload)} variables restauradas)")
    trigger_deploy(api_key, service_id)
    wait_health()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy automatizado de Tienda Eaciot a Render")
    parser.add_argument("--list", action="store_true", help="lista servicios y sale")
    parser.add_argument("--service", help="id del servicio (default: se descubre por nombre 'tienda-eaciot')")
    parser.add_argument("--csd", action="store_true", help="subir también el CSD (Secret Files)")
    parser.add_argument("--env-file", default=str(ENV_FILE), help="ruta del .env (default: ~/.config/tienda-eaciot/render.env)")
    parser.add_argument("--skip-deploy", action="store_true", help="solo sincroniza variables, sin disparar deploy")
    parser.add_argument("--revive-products", action="store_true",
                        help="reactiva TODOS los productos inactivos (recupera los que apagó el botón Eliminar viejo)")
    parser.add_argument("--unrevive", action="store_true",
                        help="quita el modo revive y redeploya (limpieza posterior)")
    parser.add_argument("--restore-catalog", action="store_true",
                        help="crea el catálogo laptops/SSD desde scripts/data/catalogo.json + IA")
    args = parser.parse_args()

    api_key = os.environ.get("RENDER_API_KEY", "").strip()
    if not api_key:
        # Fallback permanente: archivo de key (sin depender de la sintaxis de
        # variables de entorno de cada shell — 'set' en PowerShell NO exporta
        # variables de entorno, por eso fallaba antes).
        key_file = Path.home() / ".config" / "tienda-eaciot" / "render_key.txt"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
    if api_key:
        # Diagnóstico seguro: solo los primeros caracteres (sin revelar la key).
        if not api_key.startswith("rnd_"):
            print(f"⚠ La key leída NO empieza con 'rnd_': '{api_key[:20]}...' — el archivo render_key.txt tiene contenido incorrecto.")
            print("  Borra el archivo y pégalo de nuevo con Notepad (ver instrucciones abajo).")
            raise SystemExit(1)
        print(f"✓ Key leída: {api_key[:11]}...(oculta)")
    if not api_key:
        print("Falta RENDER_API_KEY.\n"
              "Guarda tu key UNA vez con (PowerShell, pide la key sin mostrarla):\n"
              '  $key = Read-Host -MaskInput "Pega tu Render API key"\n'
              '  New-Item -ItemType Directory -Force "$env:USERPROFILE\\.config\\tienda-eaciot" | Out-Null\n'
              '  Set-Content -Path "$env:USERPROFILE\\.config\\tienda-eaciot\\render_key.txt" -Value $key -NoNewline\n'
              "  python scripts\\render_deploy.py --csd\n\n"
              "Alternativa: https://dashboard.render.com/u/settings#api-keys -> Create API Key")
        raise SystemExit(1)

    if args.list:
        list_services(api_key)
        return

    service_id = args.service or find_service(api_key)["id"]
    print(f"Servicio: {service_id}")

    if args.revive_products:
        _revive_products(api_key, service_id, args.env_file)
        return

    if args.unrevive:
        _unrevive_products(api_key, service_id, args.env_file)
        return

    if args.restore_catalog:
        env = load_env(args.env_file)
        env["RESTORE_CATALOG"] = "true"
        payload = [{"key": k, "value": v} for k, v in env.items() if k and v != ""]
        api("PUT", f"/services/{service_id}/env-vars", api_key, body=payload)
        print(f"✓ {len(payload)} variables restauradas + RESTORE_CATALOG=true")
        trigger_deploy(api_key, service_id)
        print("⏳ El deploy crea laptops/SSD desde catalogo.json y los enriquece con IA.")
        print("   Después limpia el modo: python scripts\\render_deploy.py --unrevive")
        wait_health()
        return

    env = load_env(args.env_file)
    print(f"✓ .env leído: {len(env)} variables ({args.env_file})")

    put_env_vars(api_key, service_id, env)
    if args.csd:
        if CSD_CER.exists() and CSD_KEY.exists():
            try:
                upload_csd(api_key, service_id)
            except SystemExit as exc:
                # El CSD NO es crítico: sin él las facturas salen como
                # comprobante imprimible (fallback). No bloquear el deploy.
                print(f"⚠ CSD: {exc}")
                print("  (no bloquea nada: facturas imprimibles hasta subir el CSD)")
        else:
            print(f"⚠ CSD no encontrado en {CSD_CER.parent} — se omite la subida.")

    if args.skip_deploy:
        print("Listo (sin deploy).")
        return

    trigger_deploy(api_key, service_id)
    wait_health()
    print("\nHecho. Siguiente: https://tienda.eaciot.com/admin/dashboard (admin@eaciot.com / Admin123!)")
    print("En el dashboard, botón: '✨ Re-escribir TODOS los productos con IA'")


if __name__ == "__main__":
    main()
