"""Pruebas de integración Finkok (demo) — lo que pide el integrador.

Ejecuta exactamente las pruebas del proceso de integración de Finkok:
  1. --ping    : valida usuario/contraseña contra el WS demo (XML vacío).
                 Si responde 301 (XML mal formado) = credenciales OK.
                 Si responde "validating the reseller and user" = la cuenta
                 demo aún no está activada/registrada.
  2. (default) : timbrado completo — CFDI 4.0 firmado con TU CSD real ->
                 stamp SOAP demo -> UUID. Si timbra, también prueba
                 cancelación + get_sat_status.

Uso:
  python scripts/finkok_probe.py --ping
  python scripts/finkok_probe.py            # prueba completa de timbrado+cancelación
"""
import argparse
import base64
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
# Permitir importar app.* cuando el script corre fuera del repo
sys.path.insert(0, str(REPO))
ENV_FILE = Path.home() / ".config" / "tienda-eaciot" / ".env"
CSD_CER = REPO / "csd" / "CSD EAC240318.cer"
CSD_KEY = REPO / "csd" / "CSD_EMANUEL_AZUR_CORP_EAC2403183F0_20241019_012905.key"


def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def ping(env: dict, user: str = "", pwd: str = "") -> None:
    print("== PING credenciales Finkok demo ==")
    user = user or env.get("PAC_USERNAME", "")
    pwd = pwd or env.get("PAC_PASSWORD", "")
    if not user or not pwd:
        print("Faltan PAC_USERNAME/PAC_PASSWORD en el .env (o pásalos por parámetro)")
        return
    import httpx

    body = (
        '<stamp xmlns="http://facturacion.finkok.com/stamp">'
        f'<xml>{base64.b64encode(b"<Comprobante/>").decode()}</xml>'
        f"<username>{user}</username><password>{pwd}</password></stamp>"
    )
    envelope = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
                'xmlns:tns="http://facturacion.finkok.com/stamp"><soapenv:Body>'
                + body + "</soapenv:Body></soapenv:Envelope>")
    r = httpx.post("https://demo-facturacion.finkok.com/servicios/soap/stamp",
                   content=envelope,
                   headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": '"stamp"'},
                   timeout=45)
    print(f"HTTP {r.status_code}")
    txt = r.text
    low = txt.lower()

    # Códigos OFICIALES de Finkok (elementos con namespace, no substrings):
    #   705 = XML estructura inválida -> significa que las credenciales SÍ
    #         autenticaron y se llegó a validar el XML (esperado con XML basura).
    #   300 = usuario/contraseña inválidos.
    #   301 = XML mal formado (también = credenciales OK).
    import re as _re
    codes = _re.findall(r"CodigoError[^>]*>(\d+)", txt)
    msgs = _re.findall(r"MensajeIncidencia[^>]*>([^<]+)", txt)
    code = codes[0] if codes else None

    if code == "300":
        print("❌ ERROR 300: usuario/contraseña inválidos en DEMO.")
        print("   (O estás usando credenciales de producción contra demo.)")
    elif code in ("705", "301"):
        print(f"✅ CREDENCIALES DEMO OK — Finkok respondió {code} ({msgs[0] if msgs else ''})")
        print("   Tus credenciales demo autentican; solo falta completar el registro del RFC emisor.")
    elif "reseller and user" in low or "validating the reseller" in low:
        print("⚠ Cuenta demo incompleta: Finkok dice 'validating the reseller and user'.")
        print("   Falta: panel demo -> datos fiscales + Clientes -> Agregar RFC emisor.")
    else:
        print("Respuesta cruda:")
        print(txt[:800])


def full_test(env: dict) -> None:
    print("== PRUEBA COMPLETA: timbrado CFDI 4.0 con tu CSD + cancelación ==")

    # Volcar el .env al entorno del proceso (pydantic-settings los toma) y
    # apuntar el CSD a los archivos locales del repo para esta prueba.
    for k, v in env.items():
        os.environ[k] = v
    os.environ["PAC_ENVIRONMENT"] = "test"  # demo — obligatorio para las pruebas
    os.environ["CSD_CERT_PATH"] = str(CSD_CER)
    os.environ["CSD_KEY_PATH"] = str(CSD_KEY)

    from app.services.cfdi_satcfdi import SATCFDIIssuer

    issuer = SATCFDIIssuer()
    try:
        result = issuer.issue(
            customer_rfc="XAXX010101000",
            customer_name="PUBLICO EN GENERAL",
            uso_cfdi="G03",
            items=[{"description": "Producto de prueba Tienda Eaciot", "quantity": 1, "unit_price": "10.00"}],
        )
        uuid = result.get("uuid")
        print(f"✅ TIMBRADO EXITOSO — UUID: {uuid}")
        print(f"   XML timbrado guardado en: /tmp/finkok_timbrado.xml")
        Path("/tmp/finkok_timbrado.xml").write_text(result["xml"], encoding="utf-8")

        # Cancelación + estado SAT (las otras pruebas que pide el integrador)
        from app.services.cfdi_finkok import finkok_client
        cer_b64 = base64.b64encode(CSD_CER.read_bytes()).decode("ascii")
        key_b64 = base64.b64encode(CSD_KEY.read_bytes()).decode("ascii")
        try:
            canc = finkok_client.cancel(
                uuid=uuid,
                taxpayer_id=env.get("BUSINESS_RFC", "EAC2403183F0"),
                cer_b64=cer_b64,
                key_b64=key_b64,
                store_pending=False,
            )
            print(f"✅ CANCELACIÓN: estatus={canc.get('estatus')} codestatus={canc.get('codestatus')}")
            status = finkok_client.get_sat_status(
                taxpayer_id=env.get("BUSINESS_RFC", "EAC2403183F0"),
                uuid=uuid,
                total="11.60",
                rfc_receptor="XAXX010101000",
            )
            print(f"✅ ESTADO SAT: {status}")
        except Exception as exc:
            print(f"⚠ Cancelación/estado: {str(exc)[:200]}")
    except Exception as exc:
        msg = str(exc)
        print(f"❌ TIMBRADO FALLÓ: {msg[:300]}")
        if "reseller" in msg:
            print("   Causa: cuenta demo incompleta — falta registrar el RFC emisor en el panel.")
            print("   Pasos: https://demo-facturacion.finkok.com -> login con tus credenciales demo")
            print("   -> completar Asistente de Datos Fiscales -> Clientes -> Agregar RFC emisor")
            print("   -> EAC2403183F0. Luego: python scripts\\finkok_probe.py de nuevo.")
        elif "300" in msg or "usuario" in msg:
            print("   Causa: credenciales PAC inválidas (error 300).")
        elif "301" in msg or "XML" in msg or "mal formado" in msg:
            print("   Causa: el XML firmado no pasó validación del SAT (revisar campos).")
        elif "303" in msg or "Sello" in msg:
            print("   Causa: sello no corresponde al emisor (¿CSD de otro RFC?).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pruebas de integración Finkok (demo)")
    parser.add_argument("--ping", action="store_true", help="solo validar credenciales contra el WS demo")
    parser.add_argument("--user", help="usuario Finkok (si no usas el del .env)")
    parser.add_argument("--password", help="contraseña Finkok (si no usas la del .env)")
    args = parser.parse_args()

    env = load_env(ENV_FILE)
    if args.ping:
        ping(env, user=args.user or "", pwd=args.password or "")
    else:
        if args.user:
            env["PAC_USERNAME"] = args.user
        if args.password:
            env["PAC_PASSWORD"] = args.password
        full_test(env)


if __name__ == "__main__":
    main()
