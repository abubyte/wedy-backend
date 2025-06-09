from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session
from typing import List, Optional

from app.db.session import get_session
from app.models import User
from app.dependencies import get_current_user
from app.crud.interaction_crud import InteractionCRUD
from app.schemas.interaction_schemas import (
    ReviewCreate,
    ReviewUpdate,
    ReviewResponse,
    ReviewListResponse,
    LikeResponse,
    ViewResponse
)

router = APIRouter(prefix="/interactions", tags=["interactions"])

# Review endpoints
@router.post("/cards/{card_id}/reviews", response_model=ReviewResponse)
async def create_review(
    card_id: int,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new review for a card."""
    try:
        crud = InteractionCRUD(session)
        review = await crud.create_review(
            card_id=card_id,
            user_id=current_user.id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        return review
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating review: {str(e)}"
        )

@router.get("/cards/{card_id}/reviews", response_model=ReviewListResponse)
async def list_reviews(
    card_id: int,
    skip: int = 0,
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """List all reviews for a card with pagination."""
    try:
        crud = InteractionCRUD(session)
        total = crud.get_total_reviews(card_id)
        reviews = crud.get_reviews(card_id, skip, limit)
        return ReviewListResponse(
            total=total,
            reviews=reviews,
            page=(skip // limit) + 1,
            size=limit
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing reviews: {str(e)}"
        )

@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a review."""
    try:
        crud = InteractionCRUD(session)
        review = await crud.update_review(
            review_id=review_id,
            user_id=current_user.id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        return review
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating review: {str(e)}"
        )

@router.delete("/reviews/{review_id}")
async def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a review."""
    try:
        crud = InteractionCRUD(session)
        await crud.delete_review(review_id, current_user.id)
        return {"message": "Review deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting review: {str(e)}"
        )

# Like endpoints
@router.post("/cards/{card_id}/like", response_model=dict)
async def toggle_like(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Toggle like status for a card."""
    try:
        crud = InteractionCRUD(session)
        is_liked = await crud.toggle_like(card_id, current_user.id)
        return {"is_liked": is_liked}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error toggling like: {str(e)}"
        )

@router.get("/users/me/likes", response_model=List[LikeResponse])
async def get_user_likes(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all likes by the current user."""
    try:
        crud = InteractionCRUD(session)
        return crud.get_user_likes(current_user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user likes: {str(e)}"
        )

# View endpoints
@router.post("/cards/{card_id}/view", response_model=ViewResponse)
async def add_view(
    card_id: int,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Add a view to a card."""
    try:
        crud = InteractionCRUD(session)
        ip_address = request.client.host if request.client else None
        view = await crud.add_view(
            card_id=card_id,
            user_id=current_user.id if current_user else None,
            ip_address=ip_address
        )
        return view
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding view: {str(e)}"
        )

@router.get("/cards/{card_id}/views", response_model=List[ViewResponse])
async def get_card_views(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all views for a card (admin only)."""
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can view this information"
            )
        crud = InteractionCRUD(session)
        return crud.get_card_views(card_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting card views: {str(e)}"
        ) 