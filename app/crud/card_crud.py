from typing import List, Optional
from sqlmodel import Session, asc, desc, or_, select
from sqlalchemy import func, delete
from fastapi import HTTPException, Query, status, UploadFile
from app.models import Card, Category, User
from app.models.card_model import CardRegion, SortField, SortOrder
from app.schemas.card_schema import CardCreate, CardUpdate
from app.core.image_service import ImageService
from app.models.interaction_model import Review, Like, View
import logging

image_service = ImageService()

class CardCRUD:
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

    def _validate_category_id(self, category_id: int) -> Category:
        """Validate category ID and return category if exists."""
        if not isinstance(category_id, int) or category_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID. Must be a positive integer."
            )
        
        category = self.session.get(Category, category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {category_id} does not exist"
            )
        return category

    def _validate_user_id(self, user_id: Optional[int]) -> Optional[User]:
        """Validate user ID and return user if exists."""
        if user_id is None:
            return None
            
        if not isinstance(user_id, int) or user_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID. Must be a positive integer."
            )
        
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with ID {user_id} does not exist"
            )
        return user

    def _validate_price(self, price: float, discount_price: Optional[float] = None) -> None:
        """Validate price and discount price."""
        if not isinstance(price, (int, float)) or price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be a non-negative number"
            )
        
        if discount_price is not None:
            if not isinstance(discount_price, (int, float)) or discount_price < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Discount price must be a non-negative number"
                )
            if discount_price > price:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Discount price cannot be greater than regular price"
                )

    def _validate_location(self, lat: float, long: float) -> None:
        """Validate location coordinates."""
        if not isinstance(lat, (int, float)) or not isinstance(long, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Location coordinates must be numbers"
            )
        
        if not (-90 <= lat <= 90) or not (-180 <= long <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid location coordinates. Latitude must be between -90 and 90, longitude between -180 and 180"
            )

    def _validate_phone_numbers(self, phone_numbers: List[str]) -> None:
        """Validate phone numbers format."""
        if not isinstance(phone_numbers, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone numbers must be a list"
            )
        
        for phone in phone_numbers:
            if not isinstance(phone, str) or not phone.startswith('+'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone numbers must be strings starting with '+'"
                )

    async def create_card(self, card_data: CardCreate, images: List[UploadFile], user_id: int) -> Card:
        # Validate all fields
        self._validate_category_id(card_data.category_id)
        self._validate_user_id(user_id)
        self._validate_price(card_data.price, card_data.discount_price)
        self._validate_location(card_data.location_lat, card_data.location_long)
        self._validate_phone_numbers(card_data.phone_numbers)

        # Debug logging for social media
        logger = logging.getLogger(__name__)
        logger.info(f"Creating card with social_media: {card_data.social_media}")

        # Create card instance
        card_data_dict = card_data.model_dump()
        card_data_dict["user_id"] = user_id
        card = Card(**card_data_dict)
        
        # Explicitly set phone numbers to ensure they are saved
        if card_data.phone_numbers:
            card.phone_numbers = card_data.phone_numbers
        
        # Explicitly set social media to ensure it is saved
        if card_data.social_media is not None:
            card.social_media = card_data.social_media
            logger.info(f"Set card.social_media to: {card.social_media}")
            logger.info(f"card.social_media_json is now: {card.social_media_json}")
        
        # Handle images if provided
        if images:
            if not isinstance(images, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Images must be a list"
                )
            
            image_paths = []
            for image in images:
                try:
                    if not image:
                        continue
                        
                    if not image.content_type or not image.content_type.startswith('image/'):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File must be an image. Got content type: {image.content_type}"
                        )
                    
                    # Save image and get URL
                    image_path = await image_service.save_image(image, "cards")
                    if image_path:
                        image_path = image_service.get_image_url(image_path)
                        if image_path:
                            image_paths.append(image_path)
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Error processing image {getattr(image, 'filename', 'unknown')}: {str(e)}"
                    )
            
            card.image_urls = image_paths

        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        
        # Debug logging after save
        logger.info(f"Card saved with social_media_json: {card.social_media_json}")
        logger.info(f"Card.social_media property returns: {card.social_media}")
        
        return card

    async def get_total_cards(
        self,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[CardRegion] = None,
        category_id: Optional[int] = None,
        min_rating: Optional[float] = None,
        is_featured: Optional[bool] = None,
        user_id: Optional[int] = None
    ) -> int:
        query = select(func.count()).select_from(Card)

        if min_price is not None:
            query = query.where(Card.price >= min_price)
        if max_price is not None:
            query = query.where(Card.price <= max_price)
        if location is not None:
            query = query.where(Card.region == location)
        if category_id is not None:
            query = query.where(Card.category_id == category_id)
        if min_rating is not None:
            query = query.where(Card.rating >= min_rating)
        if is_featured is not None:
            query = query.where(Card.is_featured == is_featured)
        if user_id is not None:
            query = query.where(Card.user_id == user_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Card.name.ilike(search_term),
                    Card.description.ilike(search_term)
                )
            )
        
        return self.session.exec(query).one()

    async def get_cards(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[CardRegion] = None,
        category_id: Optional[int] = None,
        min_rating: Optional[float] = None,
        is_featured: Optional[bool] = None,
        sort_by: Optional[SortField] = None,
        sort_order: Optional[SortOrder] = None,
        user_id: Optional[int] = None
    ) -> List[Card]:
        query = select(Card)

        if min_price is not None:
            query = query.where(Card.price >= min_price)
        if max_price is not None:
            query = query.where(Card.price <= max_price)
        if location is not None:
            query = query.where(Card.region == location)
        if category_id is not None:
            query = query.where(Card.category_id == category_id)
        if min_rating is not None:
            query = query.where(Card.rating >= min_rating)
        if is_featured is not None:
            query = query.where(Card.is_featured == is_featured)
        if user_id is not None:
            query = query.where(Card.user_id == user_id)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Card.name.ilike(search_term),
                    Card.description.ilike(search_term)
                )
            )
        
        sort_column = getattr(Card, sort_by.value)
        query = query.order_by(desc(sort_column) if sort_order == SortOrder.desc else asc(sort_column))

        return self.session.exec(
            query
            .offset(skip)
            .limit(limit)
        ).all()

    async def get_card_by_id(self, card_id: int) -> Card:
        return self._validate_card_id(card_id)

    async def update_card(self, card_id: int, update_data: CardUpdate, images: List[UploadFile], user_id: int) -> Card:
        card = self._validate_card_id(card_id)
        
        # Debug logging for social media
        logger = logging.getLogger(__name__)
        logger.info(f"Updating card {card_id} with social_media: {update_data.social_media}")
        
        # Validate updated fields
        if "category_id" in update_data.model_dump(exclude_unset=True):
            self._validate_category_id(update_data.category_id)
        
        if "user_id" in update_data.model_dump(exclude_unset=True):
            self._validate_user_id(update_data.user_id)
        
        if "price" in update_data.model_dump(exclude_unset=True) or "discount_price" in update_data.model_dump(exclude_unset=True):
            self._validate_price(
                update_data.price if update_data.price is not None else card.price,
                update_data.discount_price if update_data.discount_price is not None else card.discount_price
            )
        
        if "location_lat" in update_data.model_dump(exclude_unset=True) or "location_long" in update_data.model_dump(exclude_unset=True):
            self._validate_location(
                update_data.location_lat if update_data.location_lat is not None else card.location_lat,
                update_data.location_long if update_data.location_long is not None else card.location_long
            )
        
        if "phone_numbers" in update_data.model_dump(exclude_unset=True):
            self._validate_phone_numbers(update_data.phone_numbers)

        # Update card fields
        update_data_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_data_dict.items():
            if key == "phone_numbers" and value is not None:
                card.phone_numbers = value
            elif key == "social_media" and value is not None:
                card.social_media = value
                logger.info(f"Set card.social_media to: {card.social_media}")
                logger.info(f"card.social_media_json is now: {card.social_media_json}")
            else:
                setattr(card, key, value)

        # Handle images if provided
        if images:
            if not isinstance(images, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Images must be a list"
                )
            
            valid_images = []
            for image in images:
                if (image and 
                    hasattr(image, 'filename') and 
                    image.filename and 
                    image.filename.strip() and
                    image.size > 0):
                    valid_images.append(image)
            
            if valid_images:
                # Delete old images
                if card.image_urls:
                    old_images = card.image_urls
                    await image_service.delete_images(old_images)
                
                # Save new images
                image_paths = []
                for image in valid_images:
                    image_path = await image_service.save_image(image, "cards")
                    if image_path:
                        image_path = image_service.get_image_url(image_path)
                        if image_path:
                            image_paths.append(image_path)
                card.image_urls = image_paths
            else:
                if card.image_urls:
                    old_images = card.image_urls
                    await image_service.delete_images(old_images)
                card.image_urls = []

        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        
        # Debug logging after save
        logger.info(f"Card updated with social_media_json: {card.social_media_json}")
        logger.info(f"Card.social_media property returns: {card.social_media}")
        
        return card

    async def delete_card(self, card_id: int) -> None:
        card = self._validate_card_id(card_id)
        # Delete related reviews, likes, and views
        self.session.exec(delete(Review).where(Review.card_id == card_id))
        self.session.exec(delete(Like).where(Like.card_id == card_id))
        self.session.exec(delete(View).where(View.card_id == card_id))
        self.session.commit()
        # Delete images if any
        if card.image_urls:
            for url in card.image_urls:
                await image_service.delete_image(url)
        self.session.delete(card)
        self.session.commit()

    async def toggle_card_featured(self, card_id: int) -> Card:
        card = self._validate_card_id(card_id)
        card.is_featured = not card.is_featured
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card 