from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlmodel import Session
from app.db.session import get_session
from app.models.tariff_model import Tariff
from app.models.user_model import User, UserRole
from app.schemas.tariff_schema import (
    TariffCreate, TariffUpdate, TariffResponse,
    TariffListResponse, TariffRead
)
from app.dependencies import get_current_user, get_admin_user
from app.crud.tariff_crud import TariffCRUD
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tariffs", tags=["tariffs"])

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