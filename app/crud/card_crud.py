from typing import List, Optional
from sqlmodel import Session, select
from sqlalchemy import func
from fastapi import HTTPException, status, UploadFile
from app.models import Card, Category, User
from app.models.card_model import CardRegion
from app.schemas.card_schema import CardCreate, CardUpdate
from app.core.image_service import ImageService

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

    async def create_card(self, card_data: CardCreate, images: List[UploadFile]) -> Card:
        # Validate all fields
        self._validate_category_id(card_data.category_id)
        self._validate_user_id(card_data.user_id)
        self._validate_price(card_data.price, card_data.discount_price)
        self._validate_location(card_data.location_lat, card_data.location_long)
        self._validate_phone_numbers(card_data.phone_numbers)

        # Create card instance
        card = Card(**card_data.model_dump())
        
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
        return card

    def get_total_cards(
        self,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[CardRegion] = None,
        category_id: Optional[int] = None,
        min_rating: Optional[float] = None,
        is_featured: Optional[bool] = None
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

        return self.session.exec(query).one()

    def get_cards(
        self,
        skip: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        location: Optional[CardRegion] = None,
        category_id: Optional[int] = None,
        min_rating: Optional[float] = None,
        is_featured: Optional[bool] = None
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

        return self.session.exec(
            query
            .offset(skip)
            .limit(limit)
        ).all()

    def get_card_by_id(self, card_id: int) -> Card:
        return self._validate_card_id(card_id)

    async def update_card(self, card_id: int, update_data: CardUpdate, images: List[UploadFile]) -> Card:
        card = self._validate_card_id(card_id)
        update_data_dict = update_data.model_dump(exclude_unset=True)
        
        # Validate updated fields
        if "category_id" in update_data_dict:
            self._validate_category_id(update_data_dict["category_id"])
        
        if "user_id" in update_data_dict:
            self._validate_user_id(update_data_dict["user_id"])
        
        if "price" in update_data_dict or "discount_price" in update_data_dict:
            self._validate_price(
                update_data_dict.get("price", card.price),
                update_data_dict.get("discount_price", card.discount_price)
            )
        
        if "location_lat" in update_data_dict or "location_long" in update_data_dict:
            self._validate_location(
                update_data_dict.get("location_lat", card.location_lat),
                update_data_dict.get("location_long", card.location_long)
            )
        
        if "phone_numbers" in update_data_dict:
            self._validate_phone_numbers(update_data_dict["phone_numbers"])

        # Validate images if provided
        if images:
            if not isinstance(images, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Images must be a list"
                )
            
            for image in images:
                if not isinstance(image, UploadFile):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid image file"
                    )
                if not image.content_type or not image.content_type.startswith('image/'):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File must be an image"
                    )

        for key, value in update_data_dict.items():
            if key == "phone_numbers" and value is not None:
                card.phone_numbers = value
            elif key == "social_media" and value is not None:
                card.social_media = value
            else:
                setattr(card, key, value)

        if images:
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
                    image_path = image_service.get_image_url(
                        await image_service.save_image(image, "cards")
                    )
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
        return card

    async def delete_card(self, card_id: int) -> None:
        card = self._validate_card_id(card_id)
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