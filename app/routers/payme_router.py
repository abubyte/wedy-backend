from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlmodel import Session
from typing import Optional
import logging
from datetime import datetime

from app.db.session import get_session
from app.dependencies import get_current_user, get_admin_user
from app.models.user_model import User
from app.models.tariff_model import Tariff
from app.schemas.payment_schema import (
    PaymePaymentCreate, 
    PaymePaymentResponse, 
    PaymeWebhookData,
    PaymeTransactionStatus,
    TariffPurchaseRequest
)
from app.crud.payment_crud import (
    create_payme_payment,
    get_payment_by_payme_transaction,
    update_payment_with_payme_data,
    update_payment_from_webhook,
    activate_user_tariff,
    get_payment_statistics,
    mark_payment_failed
)
from app.external_services.payme_service import PaymeService, PaymeError, PaymeAPIError, PaymeValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payme", tags=["payme"])

# Initialize Payme service
payme_service = PaymeService()


@router.post("/create-payment", response_model=PaymePaymentResponse)
async def create_payment(
    payment_data: PaymePaymentCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new Payme payment for tariff purchase"""
    try:
        # Verify tariff exists and is active
        tariff = session.get(Tariff, payment_data.tariff_id)
        if not tariff:
            raise HTTPException(status_code=404, detail="Tariff not found")
        if not tariff.is_active:
            raise HTTPException(status_code=400, detail="This tariff is not available for purchase")
        
        # Verify amount matches tariff price
        if payment_data.amount != int(tariff.price):
            raise HTTPException(
                status_code=400, 
                detail=f"Amount {payment_data.amount} does not match tariff price {int(tariff.price)}"
            )
        
        # Check if user has an active tariff
        if current_user.tariff_id and current_user.tariff_expires_at:
            if current_user.tariff_expires_at > datetime.utcnow():
                # Get current tariff
                current_tariff = session.get(Tariff, current_user.tariff_id)
                
                # Only allow upgrading to more expensive tariffs
                if tariff.price <= current_tariff.price:
                    raise HTTPException(
                        status_code=400,
                        detail="You cannot downgrade to a cheaper tariff until your current tariff expires. Current tariff expires at: " + 
                        current_user.tariff_expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    )
                else:
                    logger.info(f"User {current_user.id} is upgrading from tariff {current_tariff.id} (price: {current_tariff.price}) to tariff {tariff.id} (price: {tariff.price})")
        
        # Create payment record
        payment = create_payme_payment(
            session=session,
            user_id=payment_data.user_id,
            amount=payment_data.amount,
            tariff_id=payment_data.tariff_id
        )
        
        # Create payment in Payme
        payme_result = payme_service.create_payment(
            amount=payment_data.amount,
            order_id=payment.id,
            description=payment_data.description
        )
        
        if payme_result['success']:
            # Update payment with Payme transaction data
            update_payment_with_payme_data(
                session=session,
                payment_id=payment.id,
                payme_transaction_id=payme_result['transaction_id'],
                payme_cheque_id=payme_result.get('cheque_id')
            )
            
            return PaymePaymentResponse(
                success=True,
                transaction_id=payme_result['transaction_id'],
                cheque_id=payme_result.get('cheque_id'),
                pay_url=payme_result.get('pay_url'),
                data=payme_result.get('data')
            )
        else:
            # Mark payment as failed
            mark_payment_failed(
                session=session,
                payment_id=payment.id,
                error_code="PAYME_CREATE_FAILED",
                error_message=payme_result.get('error', 'Unknown error')
            )
            
            return PaymePaymentResponse(
                success=False,
                error=payme_result.get('error', 'Failed to create payment'),
                data=payme_result.get('data')
            )
            
    except HTTPException:
        raise
    except PaymeError as e:
        logger.error(f"Payme error creating payment: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error creating Payme payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook")
async def payme_webhook(
    request: Request,
    session: Session = Depends(get_session)
):
    """Handle Payme webhook notifications"""
    try:
        # Get request body
        webhook_data_raw = await request.json()
        # Validate request body using schema
        try:
            webhook_data = PaymeWebhookData(**webhook_data_raw)
        except Exception as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid webhook payload")
        logger.info(f"Received Payme webhook: method={webhook_data.method}, params_keys={list(webhook_data.params.keys())}")
        
        # Get signature from headers
        signature = request.headers.get('X-Auth-Signature')
        if not signature:
            logger.error("Missing signature in webhook")
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Verify webhook signature
        if not payme_service.verify_webhook_signature(webhook_data_raw, signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse webhook data
        parsed_data = payme_service.parse_webhook_data(webhook_data_raw)
        
        if parsed_data['type'] == 'error':
            logger.error(f"Error parsing webhook data: {parsed_data.get('error')}")
            raise HTTPException(status_code=400, detail="Invalid webhook data")
        
        if parsed_data['type'] == 'payment_success':
            # Update payment status
            success = update_payment_from_webhook(
                session=session,
                payme_transaction_id=parsed_data['transaction_id'],
                status="PAID",
                paid_at=parsed_data.get('paid_at'),
                cheque_id=parsed_data.get('cheque_id')
            )
            
            if success:
                # Get payment details
                payment = get_payment_by_payme_transaction(session, parsed_data['transaction_id'])
                if payment and payment.tariff_id:
                    # Activate user tariff
                    activate_user_tariff(session, payment.user_id, payment.tariff_id)
                    logger.info(f"Activated tariff {payment.tariff_id} for user {payment.user_id}")
                
                return {"result": "ok"}
            else:
                logger.error(f"Failed to update payment from webhook: {parsed_data['transaction_id']}")
                raise HTTPException(status_code=500, detail="Failed to process webhook")
                
        elif parsed_data['type'] == 'payment_cancelled':
            # Update payment status to cancelled
            success = update_payment_from_webhook(
                session=session,
                payme_transaction_id=parsed_data['transaction_id'],
                status="CANCELLED"
            )
            
            if success:
                return {"result": "ok"}
            else:
                logger.error(f"Failed to update cancelled payment: {parsed_data['transaction_id']}")
                raise HTTPException(status_code=500, detail="Failed to process webhook")
        
        else:
            logger.warning(f"Unknown webhook type: {parsed_data['type']}")
            return {"result": "ok"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing Payme webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/check-status/{transaction_id}", response_model=PaymeTransactionStatus)
async def check_transaction_status(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Check Payme transaction status"""
    try:
        # Validate transaction ID format
        if not transaction_id or len(transaction_id) < 10:
            raise HTTPException(status_code=400, detail="Invalid transaction ID format")
        
        # Check if payment exists in our database
        payment = get_payment_by_payme_transaction(session, transaction_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Transaction not found in our system")
        
        # Check status in Payme
        payme_result = payme_service.check_transaction(transaction_id)
        
        if payme_result['success']:
            return PaymeTransactionStatus(
                success=True,
                status=payme_result['status'],
                amount=payme_result.get('amount'),
                paid_at=payme_result.get('paid_at'),
                data=payme_result.get('data')
            )
        else:
            return PaymeTransactionStatus(
                success=False,
                error=payme_result.get('error', 'Unknown error'),
                data=payme_result.get('data')
            )
            
    except HTTPException:
        raise
    except PaymeError as e:
        logger.error(f"Payme error checking transaction status: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error checking transaction status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/purchase-tariff", response_model=PaymePaymentResponse)
async def purchase_tariff(
    purchase_data: TariffPurchaseRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Purchase a tariff using Payme"""
    try:
        # Verify tariff exists and is active
        tariff = session.get(Tariff, purchase_data.tariff_id)
        if not tariff:
            raise HTTPException(status_code=404, detail="Tariff not found")
        if not tariff.is_active:
            raise HTTPException(status_code=400, detail="This tariff is not available for purchase")
        
        # Create payment data
        from app.schemas.payment_schema import PaymePaymentCreate
        payment_data = PaymePaymentCreate(
            user_id=purchase_data.user_id,
            tariff_id=purchase_data.tariff_id,
            amount=int(tariff.price),
            description=f"Tariff: {tariff.name}"
        )
        
        # Create payment
        return await create_payment(payment_data, current_user, session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error purchasing tariff: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
    user_id: Optional[str] = None
):
    """Get payment statistics (admin only)"""
    try:
        stats = get_payment_statistics(session, user_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting payment statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cancel-payment/{transaction_id}")
async def cancel_payment(
    transaction_id: str,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Cancel a Payme payment (admin only)"""
    try:
        # Validate transaction ID
        if not transaction_id or len(transaction_id) < 10:
            raise HTTPException(status_code=400, detail="Invalid transaction ID format")
        
        # Check if payment exists
        payment = get_payment_by_payme_transaction(session, transaction_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Cancel in Payme
        payme_result = payme_service.cancel_transaction(transaction_id)
        
        if payme_result['success']:
            # Update local payment record
            update_payment_from_webhook(
                session=session,
                payme_transaction_id=transaction_id,
                status="CANCELLED"
            )
            
            return {"success": True, "message": "Payment cancelled successfully"}
        else:
            return {"success": False, "error": payme_result.get('error', 'Unknown error')}
            
    except HTTPException:
        raise
    except PaymeError as e:
        logger.error(f"Payme error cancelling payment: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error cancelling payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 