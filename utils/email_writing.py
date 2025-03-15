import smtplib
import ssl
from email.message import EmailMessage

EMAIL_USER = 'mhackathon2o25@gmail.com'
EMAIL_PASSWORD = 'axdv gkxt dpax pmxd'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = '587'
IMAP_SERVER = 'imap.gmail.com'
IMAP_PORT = '993'

def send_official_email(to_address: str, subject: str, body: str):
    """
    Sends an email via SMTP with the given parameters.
    You must have your EMAIL_USER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT set.
    """
    if not all([EMAIL_USER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT]):
        raise ValueError("Email environment variables are not fully set.")

    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        # SMTP over TLS
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"Failed to send email: {e}")