from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
import logging

from app.db.session import get_session

from app.models.card_model import Card, CardRegion, SortField, SortOrder
from app.models.user_model import UserRole
from app.schemas.card_schema import CardCreate, CardRead, CardUpdate, CardListResponse
from app.dependencies import get_admin_user, get_current_user, TariffValidator
from app.models import User
from app.crud.card_crud import CardCRUD

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cards", tags=["cards"])

@router.post("", response_model=CardRead)
async def create_card(
    card_data: CardCreate = Depends(CardCreate.as_form),
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    tariff_validator: TariffValidator = Depends()
):
    """Create a new card (authenticated users)."""
    try:
        image_list = images if images is not None else []
        phone_numbers_list = card_data.phone_numbers if card_data.phone_numbers is not None else []
        
        # Validate card data against tariff limits
        tariff_validator.validate_card(card_data, image_list, phone_numbers_list)
        
        crud = CardCRUD(session)
        
        card = await crud.create_card(card_data, image_list, current_user.id)
        return CardRead.from_card(card)
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
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search in fields"),
    min_price: Optional[float] = Query(None, description="Minimum price for filtering"),
    max_price: Optional[float] = Query(None, description="Maximum price for filtering"),
    location: Optional[CardRegion] = Query(None, description="Filter by region"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    min_rating: Optional[float] = Query(None, description="Minimum rating for filtering"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    sort_by: Optional[SortField] = Query(SortField.created_at, description="Sort by field"),
    sort_order: Optional[SortOrder] = Query(SortOrder.desc, description="Sort order"),
    user_id: Optional[int] = Query(None, description="Show only user cards"),
    # current_user: Optional[User] = Depends(get_current_user)
):
    """List all cards with optional filters and pagination (public)."""
    try:
        crud = CardCRUD(session)
        # user_id = current_user.id if (my_cards and current_user) else None
        total = await crud.get_total_cards(
            search=search,
            min_price=min_price,
            max_price=max_price,
            location=location,
            category_id=category_id,
            min_rating=min_rating,
            is_featured=is_featured,
            user_id=user_id
        )
        cards = await crud.get_cards(
            search=search,
            skip=skip,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            location=location,
            category_id=category_id,
            min_rating=min_rating,
            is_featured=is_featured,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id
        )
        return CardListResponse(
            total=total,
            cards=[CardRead.from_card(card) for card in cards],
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
    session: Session = Depends(get_session)
):
    """Get a card by ID (public)."""
    try:
        crud = CardCRUD(session)
        card = await crud.get_card_by_id(card_id)
        return CardRead.from_card(card)
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
    images: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    tariff_validator: TariffValidator = Depends()
):
    """Update a card (owner or admin only)."""
    try:
        crud = CardCRUD(session)
        card = await crud.get_card_by_id(card_id)
        
        # Check ownership or admin status
        if card.user_id != current_user.id and current_user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this card"
            )
        
        # Validate updated data against tariff limits
        # Create a temporary card object with updated fields
        temp_card = Card(
            social_media=card_data.social_media or card.social_media,
            description=card_data.description or card.description,
            phone_numbers=card_data.phone_numbers or card.phone_numbers,
            image_urls=images or card.image_urls
        )
        tariff_validator.validate_card(temp_card, images or [], card_data.phone_numbers or card.phone_numbers)
        
        updated_card = await crud.update_card(card_id, card_data, images, current_user.id)
        return CardRead.from_card(updated_card)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating card: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating card: {str(e)}"
        )

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
    return CardRead.from_card(card)

# @router.post("/{card_id}/images", response_model=CardRead)
# async def upload_card_images(
#     card_id: int,
#     images: List[UploadFile] = File(...),
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session),
#     tariff_validator: TariffValidator = Depends()
# ):
#     """Upload images for a card (owner or admin only)."""
#     try:
#         crud = CardCRUD(session)
#         card = await crud.get_card_by_id(card_id)
        
#         # Check ownership or admin status
#         if card.user_id != current_user.id and current_user.role != UserRole.admin:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Not authorized to update this card"
#             )
        
#         # Validate total images count against tariff limit
#         current_images = len(card.image_urls)
#         if current_images + len(images) > tariff_validator.tariff.max_images:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail=f"Your tariff allows only {tariff_validator.tariff.max_images} images. "
#                       f"Current: {current_images}, Uploading: {len(images)}"
#             )
        
#         updated_card = await crud.upload_card_images(card, images)
#         return updated_card
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         logger.error(f"Error uploading images: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error uploading images: {str(e)}"
#         ) 