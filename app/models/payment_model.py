from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid


class Payment(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str
    amount: int
    status: str = Field(default="PENDING")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = None
    
    # Payme-specific fields
    payme_transaction_id: Optional[str] = Field(default=None, index=True)
    payme_cheque_id: Optional[str] = Field(default=None, index=True)
    tariff_id: Optional[int] = Field(default=None, foreign_key="tariff.id")
    payment_method: str = Field(default="PAYME")
    payme_error_code: Optional[str] = Field(default=None)
    payme_error_message: Optional[str] = Field(default=None)
    
    # Additional tracking fields
    updated_at: Optional[datetime] = Field(default=None)
    webhook_received_at: Optional[datetime] = Field(default=None)