import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailClient:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        try:
            parsed = parseaddr(email)
            return '@' in parsed[1] and '.' in parsed[1].split('@')[1]
        except:
            return False

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """
        Send email with proper error handling and validation
        Returns True if email was sent successfully, False otherwise
        """
        try:
            # Validate inputs
            if not to_email or not subject or not body:
                logger.error("Email parameters cannot be empty")
                return False
            
            if not self._validate_email(to_email):
                logger.error(f"Invalid email address: {to_email}")
                return False

            # Create message
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = to_email

            # Try to send email with SSL/TLS
            try:
                # First try with SMTP_SSL (port 465)
                if self.smtp_port == 465:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
                else:
                    # Use STARTTLS (port 587 or 25)
                    with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                        server.starttls()
                        server.login(self.smtp_user, self.smtp_password)
                        server.send_message(msg)
                
                logger.info(f"Email sent successfully to {to_email}")
                return True

            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP authentication failed: {e}")
                return False
            except smtplib.SMTPRecipientsRefused as e:
                logger.error(f"Recipients refused: {e}")
                return False
            except smtplib.SMTPServerDisconnected as e:
                logger.error(f"SMTP server disconnected: {e}")
                return False
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error occurred: {e}")
                return False

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
