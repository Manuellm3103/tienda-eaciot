"""Simulación E2E de producción comercial — Tienda Eaciot.

Ejecuta los flujos completos de la tienda con las credenciales REALES de
producción (Stripe live, SendGrid real, Finkok demo real, CSD real, admin
real) contra un contenedor Docker idéntico al de despliegue.

Límites duros (nadie puede cruzarlos sin tu participación):
  * NO captura una tarjeta real: en modo live de Stripe no existen tarjetas de
    prueba. La sesión de Checkout se crea DE VERDAD en Stripe live y se valida
    con la API; el cobro final queda como única pieza no ejercitable.
  * NO timbra un CFDI válido ante el SAT: Finkok rechaza las credenciales en
    producción (verificado). El timbrado DEMO sí es real (SOAP firmado con el
    CSD) y devuelve UUID, pero el SAT no conoce ese folio.

Uso:
  python scripts/e2e_prod_sim.py

Los secretos se leen de ~/.config/tienda-eaciot/.env dentro del propio script;
nunca se imprimen ni se pasan por línea de comandos.
"""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")

ENV_FILE = Path.home() / ".config" / "tienda-eaciot" / ".env"
REPO = Path(__file__).resolve().parent.parent
CSD_CER = REPO / "csd" / "CSD EAC240318.cer"
CSD_KEY = REPO / "csd" / "CSD_EMANUEL_AZUR_CORP_EAC2403183F0_20241019_012905.key"
IMAGE = "tienda-eaciot:prodsim"
CONTAINER = "tienda-prodsim"
PORT = 8125
BASE = f"http://localhost:{PORT}"
BUYER_EMAIL = "emanuelazurcorp@icloud.com"  # buzón real del usuario: recibe los emails
BUYER_PASSWORD = "Buyer123!Eaciot"

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def load_env() -> dict:
    env = {}
    for line in open(ENV_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def run_docker(args):
    return subprocess.run(["docker"] + args, capture_output=True, text=True)


def start_container(env: dict) -> None:
    run_docker(["rm", "-f", CONTAINER])
    run_docker(["volume", "rm", "-f", "tienda_prodsim_data"])
    # FORCE_HTTPS=true como en producción; ALLOWED_HOSTS local para probar aquí.
    env = dict(env)
    env["ALLOWED_HOSTS"] = "localhost,127.0.0.1,tienda.eaciot.com"
    # Batería funcional sobre HTTP plano: con FORCE_HTTPS=true el middleware
    # redirige TODAS las peticiones sin X-Forwarded-Proto a https (307), y las
    # cookies Secure no viajan por http — httpx nunca podría completar un flujo.
    # El camino TLS del proxy (X-Forwarded-Proto: https) se valida aparte en
    # tls_proxy_check(), igual que lo hace Nixopus/Render.
    env["FORCE_HTTPS"] = "false"
    cmd = ["docker", "run", "-d", "--name", CONTAINER, "-p", f"{PORT}:8000",
           "-v", "tienda_prodsim_data:/data"]
    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]
    cmd.append(IMAGE)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"docker run falló: {r.stderr[:400]}")

    # Subir CSD al volumen persistente (una sola vez, como en producción).
    run_docker(["exec", CONTAINER, "mkdir", "-p", "/data/csd"])
    for src, dst in ((CSD_CER, "/data/csd/CSD.cer"), (CSD_KEY, "/data/csd/CSD.key")):
        cp = run_docker(["cp", str(src), f"{CONTAINER}:{dst}"])
        if cp.returncode != 0:
            raise SystemExit(f"docker cp CSD falló: {cp.stderr[:300]}")
    run_docker(["restart", CONTAINER])

    for _ in range(60):
        time.sleep(2)
        try:
            if httpx.get(f"{BASE}/health", timeout=5).status_code == 200:
                return
        except Exception:
            pass
    raise SystemExit("El contenedor no arrancó a tiempo (ver: docker logs tienda-prodsim)")


def sign_stripe(whsec: str, payload: str) -> str:
    t = str(int(time.time()))
    sig = hmac.new(whsec.encode(), f"{t}.{payload}".encode(), hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def tls_proxy_check(env: dict) -> None:
    """Valida el camino TLS real de producción en un contenedor dedicado.

    FORCE_HTTPS=true (como en el .env de producción) + el proxy inyectando
    X-Forwarded-Proto: https (como hace Nixopus/Render). Sin la cabecera la app
    DEBE redirigir a https — eso es lo que rompía la espera de /health de la
    batería principal, y aquí es justo lo que se verifica.
    """
    env2 = dict(env)
    env2["FORCE_HTTPS"] = "true"
    env2["ALLOWED_HOSTS"] = "localhost,127.0.0.1,tienda.eaciot.com"
    name = CONTAINER + "-tls"
    port = PORT + 1
    base = f"http://localhost:{port}"
    run_docker(["rm", "-f", name])
    run_docker(["volume", "rm", "-f", "tienda_prodsim_data_tls"])
    cmd = ["docker", "run", "-d", "--name", name, "-p", f"{port}:8000",
           "-v", "tienda_prodsim_data_tls:/data"]
    for k, v in env2.items():
        cmd += ["-e", f"{k}={v}"]
    cmd.append(IMAGE)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        record("FORCE_HTTPS (contenedor TLS)", False, r.stderr[:200])
        return
    up = False
    for _ in range(60):
        time.sleep(2)
        try:
            if httpx.get(f"{base}/health", timeout=5,
                         headers={"X-Forwarded-Proto": "https"}).status_code == 200:
                up = True
                break
        except Exception:
            pass
    if not up:
        record("FORCE_HTTPS (contenedor TLS)", False, "no arrancó")
        run_docker(["rm", "-f", name])
        return

    raw = httpx.Client(timeout=30, follow_redirects=False)
    ok = raw.get(f"{base}/health", headers={"X-Forwarded-Proto": "https"})
    bad = raw.get(f"{base}/health")
    record("FORCE_HTTPS: con cabecera del proxy TLS sirve 200", ok.status_code == 200,
           f"HTTP {ok.status_code}")
    record("FORCE_HTTPS: sin cabecera redirige a https (no loop)",
           bad.status_code in (301, 307) and "https" in (bad.headers.get("location") or "").lower(),
           f"HTTP {bad.status_code}")
    record("Cookies con flag Secure tras proxy TLS",
           "Secure" in (ok.headers.get("set-cookie") or ""))
    run_docker(["rm", "-f", name])
    run_docker(["volume", "rm", "-f", "tienda_prodsim_data_tls"])


def main() -> None:
    env = load_env()
    print(f"== E2E producción sim (env: {len(env)} variables) ==")
    print("Construyendo imagen...")
    b = run_docker(["build", "-t", IMAGE, str(REPO)])
    if b.returncode != 0:
        raise SystemExit(f"build falló: {b.stderr[-500:]}")
    print("Levantando contenedor con env real de producción...")
    start_container(env)

    client = httpx.Client(timeout=60, follow_redirects=False)

    # ── 1. Stripe: la API key live es válida (lectura, sin cargos) ─────────
    try:
        r = httpx.get("https://api.stripe.com/v1/account", auth=(env["STRIPE_SECRET_KEY"], ""), timeout=30)
        acct = r.json()
        record("Stripe live: API key válida (GET /account)",
               r.status_code == 200 and acct.get("id", "").startswith("acct_"),
               f"account={acct.get('id')} email={acct.get('email')}" if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as exc:
        record("Stripe live: API key válida", False, str(exc)[:150])

    # ── 2. Salud + catálogo sembrado + admin creado por bootstrap ──────────
    h = client.get(f"{BASE}/health")
    record("Health + DB conectada", h.status_code == 200 and h.json().get("database") == "connected")
    prods = client.get(f"{BASE}/products/")
    record("Catálogo sembrado por bootstrap", "Camiseta Eaciot" in prods.text and "Ebook: Domina la IA" in prods.text)

    # ── 3. Login admin REAL (admin@eaciot.com, creado por bootstrap) ───────
    client.get(BASE)  # obtener cookie csrf_token
    csrf = client.cookies.get("csrf_token", "")
    admin = httpx.Client(timeout=60, follow_redirects=False)
    admin.get(BASE)
    acsrf = admin.cookies.get("csrf_token", "")
    r = admin.post(f"{BASE}/auth/login/web",
                   json={"email": env["ADMIN_EMAIL"], "password": env["ADMIN_PASSWORD"],
                         "_csrf_token": acsrf})
    r2 = admin.get(f"{BASE}/admin/dashboard")
    # login/web responde 302 (redirect) en éxito — el 200 del dashboard prueba
    # que la cookie de sesión quedó correctamente establecida.
    record("Login admin real + panel admin", r.status_code == 302 and r2.status_code == 200,
           f"login={r.status_code} dashboard={r2.status_code}")

    # ── 4. Registro comprador real (email de verificación via SendGrid real) ──
    buyer = httpx.Client(timeout=60, follow_redirects=False)
    buyer.get(BASE)
    bcsrf = buyer.cookies.get("csrf_token", "")
    reg = buyer.post(f"{BASE}/auth/register",
                     json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD, "name": "Cliente Real",
                           "_csrf_token": bcsrf})
    record("Registro comprador real (email verificación vía SendGrid)",
           reg.status_code in (200, 201, 400),  # 400 = ya existía de una corrida previa
           f"HTTP {reg.status_code}")

    # Hallazgo de producto: register NO inicia sesión (solo crea el usuario y
    # encola el email de verificación) — para ordenar hay que loguearse.
    bl = buyer.post(f"{BASE}/auth/login/web",
                    json={"email": BUYER_EMAIL, "password": BUYER_PASSWORD,
                          "_csrf_token": buyer.cookies.get("csrf_token", "")})
    record("Login comprador (session cookie establecida)", bl.status_code == 302,
           f"HTTP {bl.status_code}")

    # ── 5. Crear orden real (RFC genérico, uso G03) ────────────────────────
    pid = None
    import re as _re
    m = _re.search(r"/products/([0-9a-f-]{36})", prods.text)
    if not m:
        m = _re.search(r'href="/products/([0-9a-f-]{36})"', prods.text)
    if m:
        pid = m.group(1)
    else:
        # fallback: consultar API pública
        try:
            pl = client.get(f"{BASE}/api/products").json()
            pid = str(pl[0]["id"])
        except Exception:
            pid = None
    record("Producto disponible para ordenar", bool(pid), f"product_id={pid}" if pid else "no hallado")

    if pid:
        order = buyer.post(f"{BASE}/orders/",
                           json={"items": [{"product_id": pid, "quantity": 2}],
                                 "customer_rfc": "XAXX010101000", "uso_cfdi": "G03",
                                 "_csrf_token": buyer.cookies.get("csrf_token", "")})
        ok_order = order.status_code in (200, 201)
        order_id = None
        if ok_order:
            order_id = order.json().get("id")
        record("Crear orden (RFC XAXX010101000, Uso G03)", ok_order,
               f"HTTP {order.status_code} order={order_id}")

        if order_id:
            # ── 6. Checkout Session REAL en Stripe live (sin capturar tarjeta) ──
            sess = buyer.post(f"{BASE}/payments/stripe/create", params={"order_id": order_id})
            ok_sess = sess.status_code == 200 and "session_id" in (sess.json() or {})
            session_id = (sess.json() or {}).get("session_id")
            # Verificación server-side con la API de Stripe live (real):
            verified = False
            if ok_sess:
                import stripe
                stripe.api_key = env["STRIPE_SECRET_KEY"]
                try:
                    s = stripe.checkout.Session.retrieve(session_id)
                    verified = s.get("id") == session_id and s.get("payment_status") == "unpaid"
                    record("Checkout Session creada Y verificada en Stripe live",
                           verified, f"session={session_id[:12]}… status={s.get('payment_status')}")
                    stripe.checkout.Session.expire(session_id)  # higiene: nadie podrá pagarla después
                except Exception as exc:
                    record("Checkout Session en Stripe live", False, str(exc)[:200])
            else:
                record("Checkout Session en Stripe live", False, f"HTTP {sess.status_code}: {sess.text[:200]}")

            # ── 7. Webhook firmado con el whsec REAL → fulfillment completo ──
            if verified:
                payload = json.dumps({
                    "id": "evt_prodsim_1", "object": "event", "type": "checkout.session.completed",
                    "data": {"object": {"id": session_id, "payment_intent": "pi_prodsimulado",
                                        "metadata": {"order_id": order_id}}},
                })
                sig = sign_stripe(env["STRIPE_WEBHOOK_SECRET"], payload)
                wh = client.post(f"{BASE}/payments/stripe/webhook", content=payload,
                                 headers={"Stripe-Signature": sig})
                record("Webhook Stripe (firma válida, evento simulado)", wh.status_code == 200,
                       f"HTTP {wh.status_code}")

                # firma inválida debe rechazarse (400)
                bad = client.post(f"{BASE}/payments/stripe/webhook", content=payload,
                                  headers={"Stripe-Signature": "t=1,v1=deadbeef"})
                record("Webhook con firma inválida rechazado (400)", bad.status_code == 400,
                       f"HTTP {bad.status_code}")

                # ── 8. Orden pagada + efectos (stock, loyalty, shipment, invoice) ──
                o = buyer.get(f"{BASE}/orders/{order_id}").json()
                record("Orden marcada PAGADA por el webhook", o.get("status") == "paid",
                       f"status={o.get('status')} total={o.get('total_amount')}")
                invs = admin.get(f"{BASE}/admin/invoices/list").json()
                inv = next((i for i in invs.get("invoices", []) if i.get("order_id") == order_id), None)
                record("Factura pendiente creada automáticamente (get_or_create)",
                       inv is not None, f"invoice={inv.get('id') if inv else None}")

                # ── 9. Emisión CFDI REAL: CSD firma local + Finkok demo timbra ──
                if inv:
                    issue = admin.post(f"{BASE}/admin/invoices/{order_id}/issue",
                                       headers={"X-CSRF-Token": admin.cookies.get("csrf_token", "")})
                    data = issue.json() if issue.headers.get("content-type", "").startswith("application/json") else {}
                    record("CFDI timbrado en Finkok (demo) con CSD real",
                           issue.status_code == 200 and data.get("status") == "issued",
                           f"HTTP {issue.status_code} status={data.get('status')} error={data.get('error')}")
                    if data.get("status") == "issued":
                        # PDF de la factura
                        pdf = admin.get(data["pdf_url"])
                        record("PDF de factura descargable", pdf.status_code == 200 and pdf.content[:4] == b"%PDF",
                               f"HTTP {pdf.status_code} bytes={len(pdf.content)}")
                        # Cancelación + estado SAT (flujo demo real)
                        canc = admin.post(f"{BASE}/admin/invoices/{inv['id']}/cancel",
                                          headers={"X-CSRF-Token": admin.cookies.get("csrf_token", "")})
                        cd = canc.json()
                        record("Cancelación CFDI vía Finkok (demo)",
                               canc.status_code == 200 and cd.get("status") in ("cancelled", "cancel_pending"),
                               f"status={cd.get('status')} error={cd.get('error')}")

                # ── 10. Emails reales en la cola (SMTP SendGrid) ────────────
                # _flush_after_commit entrega a los 1s (+retry a los 4s): esperar
                # antes de contar para no medir la cola a mitad de vuelo.
                time.sleep(6)
                q = admin.get(f"{BASE}/admin/email-queue/list")
                try:
                    qd = q.json()
                    entries = qd if isinstance(qd, list) else qd.get("emails", qd)
                    sent = [e for e in entries if isinstance(e, dict) and str(e.get("status", "")).lower() in ("sent", "enviado", "delivered", "ok")]
                    record("Correos transaccionales enviados por SMTP real",
                           len(sent) >= 1, f"{len(sent)} enviado(s) de {len(entries)} en cola")
                except Exception as exc:
                    record("Correos transaccionales (cola)", False, str(exc)[:150])

    # ── 11. Camino TLS del proxy de producción (contenedor dedicado) ───────
    # FORCE_HTTPS=true + X-Forwarded-Proto: https, exactamente lo que hace el
    # proxy de Nixopus/Render antes de reenviar al contenedor.

    # ── 12. OAuth Google real: redirect a Google con el client_id correcto ──
    g = client.get(f"{BASE}/auth/google")
    loc = g.headers.get("location", "")
    record("OAuth Google inicia sesión en Google (client_id real)",
           "accounts.google.com" in loc and env["GOOGLE_CLIENT_ID"] in loc,
           f"HTTP {g.status_code}")

    # ── 13. Chat IA degrada con gracia sin OLLAMA_API_KEY ──────────────────
    try:
        chat = client.post(f"{BASE}/api/chat/", json={"message": "Hola, ¿tienen envíos?", "_csrf_token": csrf or ""})
        record("Chat/IA responde sin 500 (Ollama sin key → fallback)",
               chat.status_code in (200, 503) or (chat.status_code < 500), f"HTTP {chat.status_code}")
    except Exception as exc:
        record("Chat/IA responde sin 500", False, str(exc)[:120])

    # ── 14. Persistencia: reinicio del contenedor y re-verificación ────────
    run_docker(["restart", CONTAINER])
    for _ in range(60):
        time.sleep(2)
        try:
            if client.get(f"{BASE}/health", timeout=5).status_code == 200:
                break
        except Exception:
            pass
    prods2 = client.get(f"{BASE}/products/")
    ords = buyer.get(f"{BASE}/orders/")
    record("Persistencia tras reinicio (volumen /data): catálogo + orden",
           "Camiseta Eaciot" in prods2.text and ords.status_code == 200)

    # ── 15. Camino TLS del proxy de producción (contenedor dedicado) ────────
    tls_proxy_check(env)

    # ── Reporte final ──────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("RESUMEN E2E (producción simulada con credenciales reales)")
    print("=" * 64)
    for name, ok, _ in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{n_pass}/{len(RESULTS)} pasaron.")
    print("Contenedor de prueba sigue activo: docker logs tienda-prodsim")
    print("Apagarlo: docker rm -f tienda-prodsim && docker volume rm tienda_prodsim_data")


if __name__ == "__main__":
    main()
