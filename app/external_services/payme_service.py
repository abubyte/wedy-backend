import hashlib
import hmac
import json
import logging
import time
from typing import Dict, Optional, Any
import requests
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PaymeError(Exception):
    pass


class PaymeAPIError(PaymeError):
    def __init__(self, message: str, error_code: Optional[str] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.response_data = response_data
        super().__init__(self.message)


class PaymeValidationError(PaymeError):
    pass


class PaymeService:
    def __init__(self):
        self.merchant_id = settings.PAYME_MERCHANT_ID
        self.secret_key = settings.PAYME_SECRET_KEY
        self.test_mode = settings.PAYME_TEST_MODE
        self.callback_url = settings.PAYME_CALLBACK_URL

        if not self.merchant_id or not self.secret_key:
            raise PaymeError("Payme merchant ID and secret key are required")

        self.api_url = (
            settings.PAYME_TEST_API_URL if self.test_mode else settings.PAYME_API_URL
        )
        logger.info("Payme service initialized in %s mode", "TEST" if self.test_mode else "PRODUCTION")

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        try:
            json_data = json.dumps(data, separators=(',', ':'))
            return hmac.new(
                self.secret_key.encode('utf-8'),
                json_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
        except Exception as e:
            logger.error(f"Error generating signature: {str(e)}")
            raise PaymeError(f"Failed to generate signature: {str(e)}")

    def _make_request(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            data = data.copy()
            data['method'] = method
            data.setdefault('params', {})

            signature = self._generate_signature(data)

            headers = {
                'Content-Type': 'application/json',
                'X-Auth': f'{self.merchant_id}:{signature}'
            }

            response = requests.post(
                f"{self.api_url}/api",
                json=data,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                raise PaymeAPIError(
                    f"HTTP {response.status_code}",
                    response_data={"status_code": response.status_code, "text": response.text}
                )

            result = response.json()

            if 'error' in result:
                raise PaymeAPIError(
                    result['error'].get('message', 'Unknown Payme error'),
                    error_code=result['error'].get('code'),
                    response_data=result
                )

            return result

        except PaymeAPIError:
            raise
        except requests.exceptions.Timeout:
            raise PaymeAPIError("Request timeout")
        except requests.exceptions.ConnectionError:
            raise PaymeAPIError("Connection error")
        except requests.exceptions.RequestException as e:
            raise PaymeAPIError(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise PaymeAPIError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            raise PaymeAPIError(f"Unexpected error: {str(e)}")

    def create_payment(self, amount: int, order_id: str, description: str = "Tariff payment") -> Dict[str, Any]:
        try:
            if amount <= 0:
                raise PaymeValidationError("Amount must be greater than 0")
            if not order_id:
                raise PaymeValidationError("Order ID is required")

            transaction_id = str(uuid.uuid4())
            current_time = int(time.time() * 1000)

            data = {
                "params": {
                    "id": transaction_id,
                    "time": current_time,
                    "amount": amount * 100,
                    "account": {
                        "order_id": order_id
                    }
                }
            }

            result = self._make_request("CreateTransaction", data)

            transaction = result.get('result', {}).get('transaction')
            if transaction:
                return {
                    'success': True,
                    'transaction_id': transaction['id'],
                    'data': result
                }

            return {
                'success': False,
                'error': 'No transaction data received',
                'data': result
            }

        except (PaymeValidationError, PaymeAPIError) as e:
            return {
                'success': False,
                'error': str(e),
                'data': getattr(e, 'response_data', None)
            }

    def check_transaction(self, transaction_id: str) -> Dict[str, Any]:
        try:
            if not transaction_id:
                raise PaymeValidationError("Transaction ID is required")

            result = self._make_request("CheckTransaction", {
                "params": {"id": transaction_id}
            })

            result_data = result.get('result')
            if result_data:
                return {
                    "success": True,
                    "create_time": result_data.get("create_time"),
                    "perform_time": result_data.get("perform_time"),
                    "cancel_time": result_data.get("cancel_time"),
                    "transaction": result_data.get("transaction"),
                    "state": result_data.get("state"),
                    "reason": result_data.get("reason"),
                    "data": result_data
                }

            return {
                "success": False,
                "error": "Transaction not found",
                "data": result
            }

        except (PaymeValidationError, PaymeAPIError) as e:
            return {
                'success': False,
                'error': str(e),
                'data': getattr(e, 'response_data', None)
            }

    def cancel_transaction(self, transaction_id: str, reason: int) -> Dict[str, Any]:
        try:
            if not transaction_id:
                raise PaymeValidationError("Transaction ID is required")

            result = self._make_request("CancelTransaction", {
                "params": {
                    "id": transaction_id,
                    "reason": reason
                }
            })

            cancel_result = result.get("result")
            if cancel_result:
                return {
                    "success": True,
                    "transaction": cancel_result.get("transaction"),
                    "cancel_time": cancel_result.get("cancel_time"),
                    "state": cancel_result.get("state"),
                    "data": cancel_result
                }

            return {
                "success": False,
                "error": "Cancel failed",
                "data": result
            }

        except (PaymeValidationError, PaymeAPIError) as e:
            return {
                "success": False,
                "error": str(e),
                "data": getattr(e, 'response_data', None)
            }

    def verify_webhook_signature(self, data: Dict[str, Any], signature: str) -> bool:
        try:
            if not signature:
                return False

            data_for_signature = data.copy()
            data_for_signature.pop('signature', None)

            expected_signature = self._generate_signature(data_for_signature)
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    def parse_webhook_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not webhook_data:
                raise PaymeValidationError("Webhook data is empty")

            method = webhook_data.get('method')
            params = webhook_data.get('params', {})

            if not method:
                raise PaymeValidationError("Webhook method is required")

            if method == 'receipts.pay':
                return {
                    'type': 'payment_success',
                    'transaction_id': params.get('id'),
                    'cheque_id': params.get('cheque_id'),
                    'amount': params.get('amount'),
                    'paid_at': params.get('paid_at'),
                    'data': webhook_data
                }

            if method == 'receipts.cancel':
                return {
                    'type': 'payment_cancelled',
                    'transaction_id': params.get('id'),
                    'data': webhook_data
                }

            return {
                'type': 'unknown',
                'method': method,
                'data': webhook_data
            }

        except (PaymeValidationError, Exception) as e:
            return {
                'type': 'error',
                'error': str(e),
                'data': webhook_data
            }
