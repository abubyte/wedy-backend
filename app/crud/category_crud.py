from sqlalchemy import func
from sqlmodel import Session, select
from fastapi import HTTPException, UploadFile, status
from app.core.image_service import ImageService
from app.models import Category
from typing import Optional

from app.models.card_model import Card

image_service = ImageService()

class CategoryCRUD:
    def __init__(self, session: Session):
        self.session = session

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
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {category_id} not found"
            )
        return category

    def _validate_name(self, name: str) -> None:
        """Validate category name."""
        if not isinstance(name, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name must be a string"
            )
        
        if not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name cannot be empty"
            )
        
        if len(name) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name must be less than 100 characters"
            )
        
        # Check for duplicate category names
        existing = self.session.exec(
            select(Category).where(Category.name == name)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{name}' already exists"
            )

    def _validate_description(self, description: Optional[str]) -> None:
        """Validate category description."""
        if description is not None:
            if not isinstance(description, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category description must be a string"
                )
            
            if len(description) > 500:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category description must be less than 500 characters"
                )

    def _validate_image(self, image: UploadFile | None) -> None:
        """Validate category image."""
        if image is not None:
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
            
            # Check file size (max 5MB)
            if image.size and image.size > 5 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image size must be less than 5MB"
                )

    async def create_category(self, category_data: dict, image: UploadFile | None = None) -> Category:
        # Validate input data
        if "name" not in category_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category name is required"
            )
        
        self._validate_name(category_data["name"])
        self._validate_description(category_data.get("description"))
        self._validate_image(image)
        
        category = Category(**category_data)
        
        # Handle profile image if provided
        if image:
            image_path = image_service.get_image_url(await image_service.save_image(image, "categories"))
            category.image_url = image_path
        
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    def get_categories(self) -> list[Category]:
        return self.session.exec(select(Category)).all()

    def get_category_by_id(self, category_id: int) -> Category:
        return self._validate_category_id(category_id)

    async def update_category(self, category_id: int, update_data: dict, image: UploadFile | None = None) -> Category:
        category = self._validate_category_id(category_id)
        
        # Validate update data
        if "name" in update_data:
            # Don't check for duplicates if name hasn't changed
            if update_data["name"] != category.name:
                self._validate_name(update_data["name"])
        
        if "description" in update_data:
            self._validate_description(update_data["description"])
        
        self._validate_image(image)
        
        # Update fields
        for key, value in update_data.items():
            setattr(category, key, value)
            
        # Handle profile image
        if image is not None:
            if category.image_url:
                await image_service.delete_image(category.image_url)
            
            if image:
                image_path = image_service.get_image_url(await image_service.save_image(image, "categories"))
                category.image_url = image_path
            else:
                category.image_url = None
            
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category

    async def delete_category(self, category_id: int) -> None:
        category = self._validate_category_id(category_id)
        
        # Check if category has associated cards
        cards_count = self.session.exec(
            select(func.count()).select_from(Card).where(Card.category_id == category_id)
        ).first()
        
        if cards_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category with ID {category_id} because it has {cards_count} associated cards"
            )
        
        if category.image_url:
            await image_service.delete_image(category.image_url)
            
        self.session.delete(category)
        self.session.commit() 