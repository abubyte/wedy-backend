from sqlalchemy import or_
from sqlmodel import Session, select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.interaction_models import Review, Like, View
from app.models.card_model import Card
from app.models.user_model import User
from app.schemas.interaction_schemas import ReviewResponse

class InteractionCRUD:
    def __init__(self, session: Session):
        self.session = session

    def _validate_card_id(self, card_id: int) -> Card:
        """Validate card ID and return card if exists."""
        if not isinstance(card_id, int) or card_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid card ID. Must be a positive integer."
            )
        
        card = self.session.get(Card, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card with ID {card_id} not found"
            )
        return card

    def _validate_user_id(self, user_id: int) -> User:
        """Validate user ID and return user if exists."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID. Must be a positive integer."
            )
        
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user

    def _validate_review_id(self, review_id: int) -> Review:
        """Validate review ID and return review if exists."""
        if not isinstance(review_id, int) or review_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid review ID. Must be a positive integer."
            )
        
        review = self.session.get(Review, review_id)
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with ID {review_id} not found"
            )
        return review

    def _validate_rating(self, rating: float) -> None:
        """Validate rating value."""
        if not isinstance(rating, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be a number"
            )
        
        if rating < 1 or rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )

    def _validate_comment(self, comment: Optional[str]) -> None:
        """Validate review comment."""
        if comment is not None:
            if not isinstance(comment, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Comment must be a string"
                )
            
            if len(comment) > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Comment must be less than 1000 characters"
                )

    def _validate_ip_address(self, ip_address: str) -> None:
        """Validate IP address format."""
        if not isinstance(ip_address, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IP address must be a string"
            )
        
        # Basic IP address format validation
        parts = ip_address.split('.')
        if len(parts) != 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address format"
            )
        
        for part in parts:
            try:
                num = int(part)
                if num < 0 or num > 255:
                    raise ValueError
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid IP address format"
                )

    # Review Operations
    async def create_review(self, card_id: int, user_id: int, rating: float, comment: Optional[str] = None) -> ReviewResponse:
        # Validate inputs
        card = self._validate_card_id(card_id)
        user = self._validate_user_id(user_id)
        self._validate_rating(rating)
        self._validate_comment(comment)
        
        # Check if user has already reviewed this card
        existing_review = self.session.exec(
            select(Review).where(
                Review.card_id == card_id,
                Review.user_id == user_id
            )
        ).first()
        
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this card"
            )
        
        # Create review
        review = Review(
            card_id=card_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            # Add the new review
            self.session.add(review)
            self.session.flush()  # Flush to get the review ID
            
            # Get all reviews including the new one
            all_reviews = self.session.exec(
                select(Review).where(Review.card_id == card_id)
            ).all()
            
            # Calculate total rating and count unique user reviews
            total_rating = sum(r.rating for r in all_reviews)
            unique_user_reviews = len(set(r.user_id for r in all_reviews))  # Count unique users who reviewed
            card.rating = total_rating / len(all_reviews)
            card.rating_count = unique_user_reviews  # Use unique user count
            
            self.session.add(card)
            self.session.commit()
            self.session.refresh(review)
            
            # Return review with user information
            return ReviewResponse(
                **review.dict(),
                user_firstname=user.firstname,
                user_lastname=user.lastname
            )
        except Exception as e:
            self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating review: {str(e)}"
            )

    def get_reviews(
        self,
        card_id: int,
        skip: int = 0,
        limit: int = 10
    ) -> List[Review]:
        reviews = self.session.exec(
            select(Review, User)
            .join(User)
            .where(Review.card_id == card_id)
            .offset(skip)
            .limit(limit)
            .order_by(Review.created_at.desc())
        ).all()
        
        return [
            ReviewResponse(
                **review[0].dict(),
                user_firstname=review[1].firstname,
                user_lastname=review[1].lastname
            )
            for review in reviews
        ]

    def get_total_reviews(self, card_id: int) -> int:
        return self.session.exec(
            select(func.count()).select_from(Review).where(Review.card_id == card_id)
        ).first()

    async def update_review(
        self,
        review_id: int,
        user_id: int,
        rating: Optional[float] = None,
        comment: Optional[str] = None
    ) -> Review:
        review = self._validate_review_id(review_id)
        self._validate_user_id(user_id)
        
        if review.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own reviews"
            )

        if rating is not None:
            self._validate_rating(rating)
            review.rating = rating
        if comment is not None:
            self._validate_comment(comment)
            review.comment = comment
        
        review.updated_at = datetime.utcnow()
        
        # Update card's average rating
        card = self._validate_card_id(review.card_id)
        reviews = self.session.exec(
            select(Review).where(Review.card_id == review.card_id)
        ).all()
        
        # Calculate total rating and count unique user reviews
        total_rating = sum(r.rating for r in reviews)
        unique_user_reviews = len(set(r.user_id for r in reviews))  # Count unique users who reviewed
        card.rating = total_rating / len(reviews)
        card.rating_count = unique_user_reviews  # Use unique user count instead of total reviews
        
        self.session.add(card)
        self.session.add(review)
        self.session.commit()
        self.session.refresh(review)
        return review

    async def delete_review(self, review_id: int, user_id: int) -> None:
        review = self._validate_review_id(review_id)
        self._validate_user_id(user_id)
        
        if review.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own reviews"
            )

        # Get the card before deleting the review
        card = self._validate_card_id(review.card_id)
        
        # Delete the review
        self.session.delete(review)
        self.session.commit()
        
        # Get remaining reviews after deletion
        remaining_reviews = self.session.exec(
            select(Review).where(Review.card_id == card.id)
        ).all()
        
        # Update card's rating and count
        if remaining_reviews:
            total_rating = sum(r.rating for r in remaining_reviews)
            card.rating = total_rating / len(remaining_reviews)
            card.rating_count = len(remaining_reviews)
        else:
            card.rating = 0.0
            card.rating_count = 0
        
        self.session.add(card)
        self.session.commit()

    # Like Operations
    async def toggle_like(self, card_id: int, user_id: int) -> bool:
        card = self._validate_card_id(card_id)
        user = self._validate_user_id(user_id)
        
        existing_like = self.session.exec(
            select(Like).where(
                and_(Like.card_id == card_id, Like.user_id == user_id)
            )
        ).first()

        if existing_like:
            self.session.delete(existing_like)
            card.like_count = max(0, card.like_count - 1)
            self.session.add(card)
            self.session.commit()
            return False
        else:
            like = Like(
                card_id=card_id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            self.session.add(like)
            card.like_count += 1
            self.session.add(card)
            self.session.commit()
            return True

    def get_user_likes(self, user_id: int) -> List[Like]:
        return self.session.exec(
            select(Like).where(Like.user_id == user_id)
        ).all()

    # View Operations
    async def add_view(self, card_id: int, user_id: Optional[int] = None, ip_address: Optional[str] = None) -> View:
        card = self._validate_card_id(card_id)
        if user_id:
            self._validate_user_id(user_id)
        if ip_address:
            self._validate_ip_address(ip_address)
        
        # Check if this is a duplicate view (same user/IP within last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        existing_view = self.session.exec(
            select(View).where(
                and_(
                    View.card_id == card_id,
                    View.created_at > one_hour_ago,
                    or_(
                        View.user_id == user_id,
                        View.ip_address == ip_address
                    )
                )
            )
        ).first()

        if existing_view:
            return existing_view

        view = View(
            card_id=card_id,
            user_id=user_id,
            ip_address=ip_address
        )
        self.session.add(view)
        
        # Update card's view count
        card.view_count += 1
        
        self.session.commit()
        self.session.refresh(view)
        return view

    def get_card_views(self, card_id: int) -> List[View]:
        return self.session.exec(
            select(View).where(View.card_id == card_id)
        ).all() 