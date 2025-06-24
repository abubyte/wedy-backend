from sqlmodel import Session, select
from app.models.payment_model import Payment
from app.models.tariff_model import Tariff
from app.models.user_model import User
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


def create_payment(session: Session, user_id: str, amount: int) -> Payment:
    payment = Payment(user_id=user_id, amount=amount)
    session.add(payment)
    session.commit()
    session.refresh(payment)
    return payment


def create_payme_payment(session: Session, user_id: str, amount: int, tariff_id: int) -> Payment:
    """Create a payment record for Payme integration"""
    payment = Payment(
        user_id=user_id,
        amount=amount,
        tariff_id=tariff_id,
        payment_method="PAYME",
        status="PENDING"
    )
    session.add(payment)
    session.commit()
    session.refresh(payment)
    logger.info(f"Created Payme payment: {payment.id} for user: {user_id}, tariff: {tariff_id}")
    return payment


def get_payment(session: Session, payment_id: str) -> Payment | None:
    return session.get(Payment, payment_id)


def get_payment_by_payme_transaction(session: Session, payme_transaction_id: str) -> Payment | None:
    """Get payment by Payme transaction ID"""
    return session.exec(
        select(Payment).where(Payment.payme_transaction_id == payme_transaction_id)
    ).first()


def get_user_payments(session: Session, user_id: str, limit: int = 50) -> List[Payment]:
    """Get all payments for a specific user"""
    return session.exec(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    ).all()


def get_pending_payments(session: Session) -> List[Payment]:
    """Get all pending payments"""
    return session.exec(
        select(Payment).where(Payment.status == "PENDING")
    ).all()


def update_payment_with_payme_data(
    session: Session, 
    payment_id: str, 
    payme_transaction_id: str,
    payme_cheque_id: Optional[str] = None
) -> bool:
    """Update payment with Payme transaction data"""
    payment = session.get(Payment, payment_id)
    if not payment:
        logger.error(f"Payment not found: {payment_id}")
        return False
    
    payment.payme_transaction_id = payme_transaction_id
    payment.payme_cheque_id = payme_cheque_id
    payment.updated_at = datetime.utcnow()
    
    session.add(payment)
    session.commit()
    logger.info(f"Updated payment {payment_id} with Payme data: {payme_transaction_id}")
    return True


def mark_payment_paid(session: Session, payment_id: str) -> bool:
    payment = session.get(Payment, payment_id)
    if not payment:
        return False
    payment.status = "PAID"
    payment.paid_at = datetime.utcnow()
    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    logger.info(f"Payment marked as paid: {payment_id}")
    return True


def mark_payment_failed(session: Session, payment_id: str, error_code: Optional[str] = None, error_message: Optional[str] = None) -> bool:
    payment = session.get(Payment, payment_id)
    if not payment:
        return False
    payment.status = "FAILED"
    payment.payme_error_code = error_code
    payment.payme_error_message = error_message
    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    logger.info(f"Payment marked as failed: {payment_id}, error: {error_message}")
    return True


def mark_payment_cancelled(session: Session, payment_id: str) -> bool:
    payment = session.get(Payment, payment_id)
    if not payment:
        return False
    payment.status = "CANCELLED"
    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    logger.info(f"Payment marked as cancelled: {payment_id}")
    return True


def update_payment_from_webhook(
    session: Session, 
    payme_transaction_id: str, 
    status: str,
    paid_at: Optional[datetime] = None,
    cheque_id: Optional[str] = None
) -> bool:
    """Update payment status from Payme webhook"""
    payment = get_payment_by_payme_transaction(session, payme_transaction_id)
    if not payment:
        logger.error(f"Payment not found for Payme transaction: {payme_transaction_id}")
        return False
    
    payment.status = status
    payment.webhook_received_at = datetime.utcnow()
    payment.updated_at = datetime.utcnow()
    
    if status == "PAID":
        payment.paid_at = paid_at or datetime.utcnow()
        payment.payme_cheque_id = cheque_id
    elif status == "FAILED":
        payment.payme_error_code = "WEBHOOK_FAILED"
        payment.payme_error_message = "Payment failed via webhook"
    
    session.add(payment)
    session.commit()
    logger.info(f"Updated payment {payment.id} from webhook: {status}")
    return True


def activate_user_tariff(session: Session, user_id: str, tariff_id: int) -> bool:
    """Activate tariff for user after successful payment"""
    user = session.get(User, user_id)
    tariff = session.get(Tariff, tariff_id)
    
    if not user or not tariff:
        logger.error(f"User or tariff not found: user_id={user_id}, tariff_id={tariff_id}")
        return False
    
    # Calculate tariff expiry date
    from datetime import timedelta
    expiry_date = datetime.utcnow() + timedelta(days=tariff.duration_days)
    
    user.tariff_id = tariff_id
    user.tariff_expires_at = expiry_date
    user.updated_at = datetime.utcnow()
    
    session.add(user)
    session.commit()
    logger.info(f"Activated tariff {tariff_id} for user {user_id}, expires: {expiry_date}")
    return True


def get_payment_statistics(session: Session, user_id: Optional[str] = None) -> dict:
    """Get payment statistics"""
    query = select(Payment)
    if user_id:
        query = query.where(Payment.user_id == user_id)
    
    payments = session.exec(query).all()
    
    total_payments = len(payments)
    total_amount = sum(p.amount for p in payments)
    paid_payments = len([p for p in payments if p.status == "PAID"])
    failed_payments = len([p for p in payments if p.status == "FAILED"])
    pending_payments = len([p for p in payments if p.status == "PENDING"])
    
    return {
        "total_payments": total_payments,
        "total_amount": total_amount,
        "paid_payments": paid_payments,
        "failed_payments": failed_payments,
        "pending_payments": pending_payments,
        "success_rate": (paid_payments / total_payments * 100) if total_payments > 0 else 0
    }
