from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentCreate(BaseModel):
    user_id: str
    amount: int


class PaymentRead(BaseModel):
    id: str
    user_id: str
    amount: int
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None


class PaymentStatus(BaseModel):
    status: str


# Payme-specific schemas
class PaymePaymentCreate(BaseModel):
    user_id: str
    tariff_id: int
    amount: int
    description: Optional[str] = "Tariff payment"


class PaymePaymentResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    cheque_id: Optional[str] = None
    pay_url: Optional[str] = None
    error: Optional[str] = None
    data: Optional[dict] = None


class PaymeWebhookData(BaseModel):
    method: str
    params: dict
    signature: Optional[str] = None


class PaymeTransactionStatus(BaseModel):
    success: bool
    status: Optional[str] = None
    amount: Optional[int] = None
    paid_at: Optional[datetime] = None
    error: Optional[str] = None
    data: Optional[dict] = None


class PaymePaymentUpdate(BaseModel):
    payme_transaction_id: str
    payme_cheque_id: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    payme_error_code: Optional[str] = None
    payme_error_message: Optional[str] = None


class TariffPurchaseRequest(BaseModel):
    tariff_id: int
    user_id: str
