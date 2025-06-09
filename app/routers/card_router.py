from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
import logging

from app.db.session import get_session
from app.models.card_model import CardRegion
from app.schemas.card_schema import CardCreate, CardRead, CardUpdate, CardListResponse
from app.dependencies import get_admin_user, get_current_user
from app.models import User
from app.crud.card_crud import CardCRUD

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cards", tags=["cards"])

@router.post("", response_model=CardRead)
async def create_card(
    card_data: CardCreate = Depends(CardCreate.as_form),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create a new card (admin only)."""
    try:
        crud = CardCRUD(session)
        # Convert None to empty list if no images provided
        image_list = images if images is not None else []
        card = await crud.create_card(card_data, image_list)
        return card
    except HTTPException as e:
        logger.error(f"Error creating card: {str(e.detail)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating card: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("", response_model=CardListResponse)
async def list_cards(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    min_price: Optional[float] = Query(None, description="Minimum price for filtering"),
    max_price: Optional[float] = Query(None, description="Maximum price for filtering"),
    location: Optional[CardRegion] = Query(None, description="Filter by region"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    min_rating: Optional[float] = Query(None, description="Minimum rating for filtering"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status")
):
    """List all cards with optional filters and pagination (all users)."""
    try:
        crud = CardCRUD(session)
        total = await crud.get_total_cards(
            min_price=min_price,
            max_price=max_price,
            location=location,
            category_id=category_id,
            min_rating=min_rating,
            is_featured=is_featured
        )
        cards = await crud.get_cards(
            skip=skip,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            location=location,
            category_id=category_id,
            min_rating=min_rating,
            is_featured=is_featured
        )
        return CardListResponse(
            total=total,
            cards=cards,
            page=(skip // limit) + 1,
            size=limit
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing cards: {str(e)}"
        )

@router.get("/{card_id}", response_model=CardRead)
async def get_card(
    card_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a card by ID (all users)."""
    try:
        crud = CardCRUD(session)
        card = await crud.get_card_by_id(card_id)
        return card
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting card: {str(e)}"
        )

@router.put("/{card_id}", response_model=CardRead)
async def update_card(
    card_id: int,
    card_data: CardUpdate = Depends(CardUpdate.as_form),
    image: UploadFile = File(None),
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update a card (admin only)."""
    crud = CardCRUD(session)
    card = await crud.update_card(card_id, card_data, image)
    return card

@router.delete("/{card_id}")
async def delete_card(
    card_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete a card (admin only)."""
    crud = CardCRUD(session)
    await crud.delete_card(card_id)
    return {"message": "Card deleted"}

@router.patch("/{card_id}/feature", response_model=CardRead)
async def toggle_card_featured(
    card_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Toggle card featured status (admin only)."""
    crud = CardCRUD(session)
    card = await crud.toggle_card_featured(card_id)
    return card 