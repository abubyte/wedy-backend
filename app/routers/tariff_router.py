from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlmodel import Session
from app.db.session import get_session
from app.models.tariff_model import Tariff
from app.models.user_model import User, UserRole
from app.schemas.tariff_schema import (
    TariffCreate, TariffUpdate, TariffResponse,
    TariffListResponse, TariffRead, TariffPurchaseResponse
)
from app.schemas.payment_schema import PaymePaymentResponse, TariffPurchaseRequest
from app.dependencies import get_current_user, get_admin_user
from app.crud.tariff_crud import TariffCRUD
from app.external_services.payme_service import PaymeService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tariffs", tags=["tariffs"])

# Initialize Payme service
payme_service = PaymeService()

@router.get("", response_model=TariffListResponse)
async def list_tariffs(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(False)
):
    """List all tariffs."""
    try:
        crud = TariffCRUD(session)
        total = await crud.get_total_tariffs(active_only)
        tariffs = await crud.get_tariffs(skip, limit, active_only)
        
        return TariffListResponse(
            total=total,
            tariffs=tariffs,
            page=(skip // limit) + 1,
            size=limit
        )
    except Exception as e:
        logger.error(f"Error listing tariffs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing tariffs: {str(e)}"
        )

@router.get("/{tariff_id}", response_model=TariffRead)
async def get_tariff(
    tariff_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a tariff by ID."""
    try:
        crud = TariffCRUD(session)
        return await crud.get_tariff_by_id(tariff_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting tariff: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting tariff: {str(e)}"
        )

@router.post("/{tariff_id}/purchase", response_model=TariffPurchaseResponse)
async def purchase_tariff(
    tariff_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Purchase a tariff using Payme payment."""
    try:
        # Get tariff details
        crud = TariffCRUD(session)
        tariff = await crud.get_tariff_by_id(tariff_id)
        
        if not tariff.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This tariff is not available for purchase"
            )
        
        # Check if user has an active tariff
        if current_user.tariff_id and current_user.tariff_expires_at:
            from datetime import datetime
            if current_user.tariff_expires_at > datetime.utcnow():
                # Get current tariff details
                current_tariff = await crud.get_tariff_by_id(current_user.tariff_id)
                
                # Only allow upgrading to more expensive tariffs
                if tariff.price <= current_tariff.price:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="You cannot downgrade to a cheaper tariff until your current tariff expires. Current tariff expires at: " + 
                        current_user.tariff_expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                    )
                else:
                    logger.info(f"User {current_user.id} is upgrading from tariff {current_tariff.id} (price: {current_tariff.price}) to tariff {tariff.id} (price: {tariff.price})")
        
        # Create payment data
        from app.schemas.payment_schema import PaymePaymentCreate
        payment_data = PaymePaymentCreate(
            user_id=str(current_user.id),  # Convert to string since PaymePaymentCreate expects string
            tariff_id=tariff_id,
            amount=int(tariff.price),
            description=f"Tariff: {tariff.name}"
        )
        
        # Create payment record
        from app.crud.payment_crud import create_payme_payment, update_payment_with_payme_data, mark_payment_failed
        
        payment = create_payme_payment(
            session=session,
            user_id=str(current_user.id),  # Convert to string since schema expects string
            amount=int(tariff.price),
            tariff_id=tariff_id
        )
        
        # Create payment in Payme
        payme_result = payme_service.create_payment(
            amount=int(tariff.price),
            order_id=payment.id,
            description=f"Tariff: {tariff.name}"
        )
        
        if payme_result['success']:
            # Update payment with Payme transaction data
            update_payment_with_payme_data(
                session=session,
                payment_id=payment.id,
                payme_transaction_id=payme_result['transaction_id'],
                payme_cheque_id=payme_result.get('cheque_id')
            )
            
            logger.info(f"Created Payme payment for tariff {tariff_id} by user {current_user.id}")
            
            return TariffPurchaseResponse(
                success=True,
                message="Payment created successfully. Please complete the payment using the provided URL.",
                tariff=tariff,
                payment_url=payme_result.get('pay_url'),
                transaction_id=payme_result['transaction_id']
            )
        else:
            # Mark payment as failed
            mark_payment_failed(
                session=session,
                payment_id=payment.id,
                error_code="PAYME_CREATE_FAILED",
                error_message=payme_result.get('error', 'Unknown error')
            )
            
            return TariffPurchaseResponse(
                success=False,
                message="Failed to create payment",
                tariff=tariff,
                error=payme_result.get('error', 'Unknown error')
            )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error purchasing tariff: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error purchasing tariff: {str(e)}"
        )

@router.post("", response_model=TariffResponse)
async def create_tariff(
    tariff_data: TariffCreate = Depends(TariffCreate.as_form),
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create a new tariff (admin only)."""
    try:
        crud = TariffCRUD(session)
        tariff = await crud.create_tariff(tariff_data, current_user.id)
        return TariffResponse(
            message="Tariff created successfully",
            tariff=tariff
        )
    except Exception as e:
        logger.error(f"Error creating tariff: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tariff: {str(e)}"
        )

@router.put("/{tariff_id}", response_model=TariffResponse)
async def update_tariff(
    tariff_id: int,
    tariff_data: TariffUpdate = Depends(TariffUpdate.as_form),
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update a tariff (admin only)."""
    try:
        crud = TariffCRUD(session)
        tariff = await crud.get_tariff_by_id(tariff_id)
        updated_tariff = await crud.update_tariff(tariff, tariff_data)
        
        return TariffResponse(
            message="Tariff updated successfully",
            tariff=updated_tariff
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating tariff: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tariff: {str(e)}"
        )

@router.delete("/{tariff_id}", response_model=dict)
async def delete_tariff(
    tariff_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete a tariff (admin only)."""
    try:
        crud = TariffCRUD(session)
        tariff = await crud.get_tariff_by_id(tariff_id)
        await crud.delete_tariff(tariff)
        return {"message": "Tariff deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting tariff: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting tariff: {str(e)}"
        ) 