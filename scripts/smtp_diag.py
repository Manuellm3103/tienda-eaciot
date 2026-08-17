"""Diagnóstico SMTP: muestra el diálogo real con SendGrid (códigos y mensajes
del servidor, SIN imprimir credenciales).

Uso:  python scripts/smtp_diag.py

Cada paso imprime (código, mensaje) tal como responde SendGrid. Con eso se
sabe exactamente por qué corta la conexión: key inválida (535), remitente no
verificado (550 Sender Identity), etc.
"""
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ENV_FILE = Path.home() / ".config" / "tienda-eaciot" / ".env"


def load_env() -> dict:
    env = {}
    for line in open(ENV_FILE, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def show(label, resp):
    """Respuesta smtplib: (code, bytes) o (code, str)."""
    code, msg = resp[0], resp[1]
    if isinstance(msg, bytes):
        msg = msg.decode("utf-8", errors="replace")
    print(f"  {label}: {code} {str(msg).strip()[:250]}")


def main() -> None:
    env = load_env()
    host = env["SMTP_HOST"]
    port = int(env.get("SMTP_PORT", "587"))
    user = env["SMTP_USER"]
    pwd = env["SMTP_PASSWORD"]
    sender = env["SMTP_FROM"]
    to = "lmmo151253@gmail.com"  # buzón real del usuario para confirmar entrega

    print(f"Conectando a {host}:{port} ...")
    smtp = smtplib.SMTP(host, port, timeout=30)
    try:
        show("EHLO", smtp.ehlo())
        if smtp.has_extn("starttls"):
            show("STARTTLS", smtp.starttls())
            show("EHLO(2)", smtp.ehlo())
        try:
            show("AUTH LOGIN", smtp.login(user, pwd))
        except smtplib.SMTPAuthenticationError as exc:
            print(f"  AUTH RECHAZADO: {exc.smtp_code} {exc.smtp_error}")
            return
        except smtplib.SMTPException as exc:
            print(f"  AUTH ERROR: {type(exc).__name__}: {str(exc)[:200]}")
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = "Diagnóstico SMTP — Tienda Eaciot"
        msg.attach(MIMEText("<p>Si lees esto en tu bandeja, SendGrid aceptó el envío.</p>", "html"))

        show("MAIL FROM", smtp.mail(sender))
        show("RCPT TO", smtp.rcpt(to))
        try:
            show("DATA", smtp.data(msg.as_string()))
            print("\n  ✅ SendGrid ACEPTÓ el correo. Revisa la bandeja de", to)
        except smtplib.SMTPException as exc:
            print(f"  ENVÍO RECHAZADO: {type(exc).__name__}: {str(exc)[:300]}")
    finally:
        try:
            show("QUIT", smtp.quit())
        except Exception:
            pass


if __name__ == "__main__":
    main()
