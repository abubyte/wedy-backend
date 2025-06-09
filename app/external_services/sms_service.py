import time
import requests
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EskizClient:
    def __init__(self):
        self.token = None
        self.token_expiry = 0

    def _get_new_token(self):
        url = 'https://notify.eskiz.uz/api/auth/login'
        data = {
            'email': settings.ESKIZ_EMAIL,
            'password': settings.ESKIZ_PASSWORD
        }
        try:
            logger.info(f"Attempting to authenticate with Eskiz using email: {settings.ESKIZ_EMAIL}")
            response = requests.post(url, data=data)
            response.raise_for_status()
            result = response.json()
            
            if 'data' not in result or 'token' not in result['data']:
                logger.error(f"Unexpected response from Eskiz: {result}")
                raise ValueError("Invalid response format from Eskiz API")

            self.token = result['data']['token']
            self.token_expiry = time.time() + 3500
            logger.info("Successfully obtained new token from Eskiz")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to authenticate with Eskiz: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            raise

    def _ensure_token(self):
        if not self.token or time.time() > self.token_expiry:
            self._get_new_token()

    def send_sms(self, phone, message):
        try:
            self._ensure_token()
            url = 'https://notify.eskiz.uz/api/message/sms/send'
            headers = {
                'Authorization': f'Bearer {self.token}'
            }
            data = {
                'mobile_phone': phone,
                'message': message,
                'from': '4546',
                'callback_url': ''
            }
            logger.info(f"Sending SMS to {phone}")
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"SMS sent successfully. Response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            raise
