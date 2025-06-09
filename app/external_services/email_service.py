import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

class EmailClient:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    def send_email(self, to_email: str, subject: str, body: str):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.smtp_user
        msg['To'] = to_email

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
