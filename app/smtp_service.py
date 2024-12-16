from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from aiosmtplib import send
from app.config import settings


async def send_email_async(subject: str, body: str, to_email: str):
    """Send email asynchronously using aiosmtplib."""
    try:
        # Criar o e-mail
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Content-Type"] = 'text/html; charset="UTF-8"'
        msg.set_charset("UTF-8")
        msg.attach(MIMEText(body, "html", "utf-8"))

        # Enviar o e-mail de forma assíncrona
        await send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")