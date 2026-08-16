"""Deploy + sync de variables a Nixopus Cloud — nunca vuelvas a tocar el .env a mano.

Un solo comando lee el .env de la raíz del repo y lo aplica completo a la app
en Nixopus (creándola la primera vez, actualizándola las siguientes), asegura
el health check y puede conectar el dominio custom.

Requisitos (una sola vez, en el dashboard de Nixopus):
  1. Conectar el repo de GitHub (Apps -> GitHub App) en dashboard.nixopus.com
  2. Crear una API key (API Keys -> Create) con prefijo nxp_  [plan Pro+]
  3. Copiar el Organization ID

Uso:
  set NIXOPUS_API_KEY=nxp_...           (Windows)
  set NIXOPUS_ORG_ID=org_...
  python scripts/nixopus_deploy.py --sync               # crea/actualiza + redeploy
  python scripts/nixopus_deploy.py --sync --domain tienda.eaciot.com
  python scripts/nixopus_deploy.py --list                # lista apps
  python scripts/nixopus_deploy.py --healthcheck <APP_ID>

Sin API key (plan gratuito): el script imprime las variables listas para pegar
en el formulario de deploy / AI Chat de Nixopus.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

API_BASE = os.environ.get("NIXOPUS_API_BASE", "https://api.nixopus.com/api/v1")
APP_NAME = "tienda-eaciot"
REPOSITORY = "github.com/Manuellm3103/tienda-eaciot"
BRANCH = "main"
PORT = 8000
HEALTH_ENDPOINT = "/health"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = Path(__file__).resolve().parent.parent


def default_env_file() -> str:
    """Resuelve el .env de producción: NIXOPUS_ENV_FILE -> ~/.config/tienda-eaciot/.env -> .env del repo."""
    candidates = [
        os.environ.get("NIXOPUS_ENV_FILE"),
        str(Path.home() / ".config" / "tienda-eaciot" / ".env"),
        str(REPO_ROOT / ".env"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return str(REPO_ROOT / ".env")


def load_env(path: str) -> dict:
    """Lee el .env (KEY=VALUE, comentarios #, comillas opcionales)."""
    env = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            env[key] = value
    return env


def api_request(method: str, path: str, body: dict | None = None, api_key: str | None = None) -> dict:
    url = f"{API_BASE}{path}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        org = os.environ.get("NIXOPUS_ORG_ID")
        if org:
            headers["X-Organization-Id"] = org
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"API error {exc.code} en {method} {path}: {detail[:500]}") from exc


def find_application(api_key: str | None, name: str = APP_NAME) -> dict | None:
    resp = api_request("GET", "/deploy/applications", api_key=api_key)
    data = resp.get("data", {})
    apps = data.get("applications") if isinstance(data, dict) else data
    if isinstance(apps, list):
        for app in apps:
            if app.get("name") == name:
                return app
    return None


def deploy_application(env: dict, api_key: str | None) -> dict | None:
    payload = {
        "name": APP_NAME,
        "repository": REPOSITORY,
        "branch": BRANCH,
        "build_pack": "compose",
        "port": PORT,
        "environment": "production",
        "environment_variables": env,
        "domains": [],
    }
    for pack in ("compose", "docker-compose", "dockerfile"):
        payload["build_pack"] = pack
        try:
            resp = api_request("POST", "/deploy/application", payload, api_key)
            app = resp.get("data", {})
            print(f"✓ App creada ({pack}): {app.get('name')} id={app.get('id')}")
            return app
        except SystemExit as exc:
            if pack == "dockerfile":
                raise
            print(f"  build_pack={pack} rechazado, probando {pack == 'compose' and 'docker-compose' or 'dockerfile'}...")
    return None


def update_application(app: dict, env: dict, api_key: str | None) -> None:
    app_id = app.get("id")
    api_request("PUT", "/deploy/application", {"id": app_id, "environment_variables": env, "force": True}, api_key)
    print(f"✓ Variables sincronizadas ({len(env)}) en {app.get('name')}")
    api_request("POST", "/deploy/application/redeploy", {"id": app_id, "force": True}, api_key)
    print("✓ Redeploy disparado (las variables solo se aplican al redeployar)")


def ensure_health_check(app_id: str, api_key: str | None) -> None:
    resp = api_request("GET", f"/healthcheck?application_id={app_id}", api_key=api_key)
    existing = resp.get("data", [])
    if isinstance(existing, dict):
        existing = existing.get("health_checks", [])
    if existing:
        print(f"✓ Health check ya existe ({len(existing)})")
        return
    api_request("POST", "/healthcheck", {
        "application_id": app_id,
        "endpoint": HEALTH_ENDPOINT,
        "method": "GET",
        "expected_status_codes": [200],
        "interval_seconds": 60,
        "timeout_seconds": 30,
        "failure_threshold": 3,
        "success_threshold": 1,
    }, api_key)
    print(f"✓ Health check creado: GET {HEALTH_ENDPOINT}")


def add_domain(name: str, api_key: str | None) -> None:
    resp = api_request("POST", "/domain/custom", {"name": name}, api_key)
    print(f"✓ Dominio registrado: {name}")
    print(f"  Respuesta: {json.dumps(resp, ensure_ascii=False)[:300]}")
    print("  Ahora crea el registro DNS que te indique Nixopus (CNAME para subdominios,")
    print("  ALIAS/ANAME para el apex) y verifícalo en Domains -> Verify. SSL es automático.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy/sync de Tienda Eaciot a Nixopus Cloud")
    parser.add_argument("--sync", action="store_true", help="crea o actualiza la app con el .env y redeploya")
    parser.add_argument("--list", action="store_true", help="lista aplicaciones")
    parser.add_argument("--domain", metavar="DOMINIO", help="conecta un dominio custom (requiere plan Pro+)")
    parser.add_argument("--healthcheck", metavar="APP_ID", help="asegura el health check de la app")
    parser.add_argument("--env-file", default=default_env_file(),
                        help="ruta al .env (default: ~/.config/tienda-eaciot/.env si existe)")
    args = parser.parse_args()

    api_key = os.environ.get("NIXOPUS_API_KEY", "").strip() or None

    if args.list:
        resp = api_request("GET", "/deploy/applications", api_key=api_key)
        apps = resp.get("data", {}).get("applications", [])
        for app in apps:
            print(f"  {app.get('name')}  id={app.get('id')}  build={app.get('build_pack')}  repo={app.get('repository')}")
        if not apps:
            print("  (sin aplicaciones)")
        return

    if args.healthcheck:
        ensure_health_check(args.healthcheck, api_key)
        return

    env = load_env(args.env_file)
    print(f"✓ .env leído: {len(env)} variables ({args.env_file})")

    if args.domain and api_key:
        add_domain(args.domain, api_key)

    if not args.sync:
        return

    if not api_key:
        print("\n⚠  Sin NIXOPUS_API_KEY — no puedo tocar el API de Nixopus.")
        print("   Opción A (plan gratuito): abre https://dashboard.nixopus.com/apps,")
        print("   selecciona el repo tienda-eaciot y pega esto en el AI Chat:")
        print("   'Deploy con Docker Compose, puerto 8000, estas environment variables:'")
        print(json.dumps(env, indent=2, ensure_ascii=False))
        print("   Opción B (plan Pro): crea la API key y ejecuta:")
        print("   set NIXOPUS_API_KEY=nxp_... && set NIXOPUS_ORG_ID=org_... && python scripts/nixopus_deploy.py --sync")
        return

    app = find_application(api_key)
    if app:
        print(f"✓ App existente: {app.get('name')} (id={app.get('id')})")
        update_application(app, env, api_key)
    else:
        app = deploy_application(env, api_key)
        if not app:
            raise SystemExit("No se pudo crear la aplicación.")

    app_id = app.get("id")
    if app_id:
        ensure_health_check(app_id, api_key)
    print("\nListo. Siguiente paso (una sola vez): conecta tienda.eaciot.com:")
    print("  python scripts/nixopus_deploy.py --domain tienda.eaciot.com")


if __name__ == "__main__":
    main()
