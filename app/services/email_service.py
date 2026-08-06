import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from app.config import settings
import secrets
from datetime import datetime, timedelta


class EmailService:
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from = settings.smtp_from
        self.smtp_tls = settings.smtp_tls
    
    async def send_email(self, to_email: str, subject: str, html_content: str):
        """Send email using SMTP"""
        message = MIMEMultipart("alternative")
        message["From"] = self.smtp_from
        message["To"] = to_email
        message["Subject"] = subject
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        try:
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=self.smtp_tls,
            )
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def generate_verification_token(self) -> str:
        """Generate a random verification token"""
        return secrets.token_urlsafe(32)
    
    async def send_verification_email(self, to_email: str, name: str, token: str):
        """Send verification email"""
        verification_url = f"{settings.frontend_url}/auth/verify-email?token={token}"
        
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
                .button { display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>¡Bienvenido a Tienda Eaciot!</h1>
                </div>
                <div class="content">
                    <h2>Hola {{ name }},</h2>
                    <p>Gracias por registrarte en Tienda Eaciot. Para completar tu registro, por favor verifica tu dirección de email.</p>
                    <p style="text-align: center;">
                        <a href="{{ verification_url }}" class="button">Verificar Email</a>
                    </p>
                    <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                    <p style="word-break: break-all; color: #2563eb;">{{ verification_url }}</p>
                    <p><strong>Este enlace expira en 24 horas.</strong></p>
                    <p>Si no creaste esta cuenta, puedes ignorar este email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Tienda Eaciot. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        html_content = template.render(
            name=name,
            verification_url=verification_url
        )
        
        return await self.send_email(
            to_email=to_email,
            subject="Verifica tu email - Tienda Eaciot",
            html_content=html_content
        )
    
    async def send_password_reset_email(self, to_email: str, name: str, token: str):
        """Send password reset email"""
        reset_url = f"{settings.frontend_url}/auth/reset-password?token={token}"
        
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc2626; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }
                .button { display: inline-block; background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Restablecer Contraseña</h1>
                </div>
                <div class="content">
                    <h2>Hola {{ name }},</h2>
                    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                    <p style="text-align: center;">
                        <a href="{{ reset_url }}" class="button">Restablecer Contraseña</a>
                    </p>
                    <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                    <p style="word-break: break-all; color: #dc2626;">{{ reset_url }}</p>
                    <p><strong>Este enlace expira en 1 hora.</strong></p>
                    <p>Si no solicitaste este cambio, puedes ignorar este email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 Tienda Eaciot. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        html_content = template.render(
            name=name,
            reset_url=reset_url
        )
        
        return await self.send_email(
            to_email=to_email,
            subject="Restablecer contraseña - Tienda Eaciot",
            html_content=html_content
        )


email_service = EmailService()
