from fastapi.params import Depends
from sqlmodel import Session, select, delete
from sqlalchemy import func
from datetime import datetime, timedelta
from fastapi import HTTPException, status, UploadFile
from app.db.session import get_session
from app.models.user_model import User, UserRole
from app.models.tariff_model import Tariff
from app.core.image_service import ImageService
import re

image_service = ImageService()

class UserCRUD:
    def __init__(self, session: Session):
        self.session = session

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

    def _validate_name(self, name: str, field_name: str) -> None:
        """Validate name fields (firstname, lastname)."""
        if not isinstance(name, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be a string"
            )
        
        if not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be empty"
            )
        
        if len(name) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be less than 50 characters"
            )

    def _validate_phone(self, phone: str) -> None:
        """Validate phone number or email format."""
        if not isinstance(phone, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number or email must be a string"
            )
        
        if not phone.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number or email cannot be empty"
            )
        
        # Uzbek phone number format: +998XXXXXXXXX
        phone_pattern = r'^\+998\d{9}$'
        # Simple email pattern
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        if not (re.match(phone_pattern, phone) or re.match(email_pattern, phone)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login format. Must be +998XXXXXXXXX or a valid email address."
            )

    def _validate_password(self, password: str) -> None:
        """Validate password strength."""
        if not isinstance(password, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be a string"
            )
        
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        if not re.search(r'[A-Z]', password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one uppercase letter"
            )
        
        if not re.search(r'[a-z]', password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one lowercase letter"
            )
        
        if not re.search(r'\d', password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain at least one number"
            )

    def _validate_role(self, role: str) -> None:
        """Validate user role."""
        if not isinstance(role, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be a string"
            )
        
        try:
            UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(r.value for r in UserRole)}"
            )

    def _validate_tariff(self, tariff_id: int) -> None:
        """Validate user tariff."""
        tariff = self.session.exec(select(Tariff).where(Tariff.id == tariff_id)).first()

        try:
            if not tariff:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tariff with id: {tariff_id} does not exists"
                )
        
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tariff with id: {tariff_id} does not exists"
            )

    def _validate_image(self, image: UploadFile | None) -> None:
        """Validate profile image."""
        if image is not None:
          
            
            # if not image.content_type or not image.content_type.startswith('image/'):
            #     raise HTTPException(
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         detail="File must be an image"
            #     )
            
            # Check file size (max 5MB)
            if image.size and image.size > 5 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image size must be less than 5MB"
                )

    def get_total_users(self) -> int:
        return self.session.exec(select(func.count()).select_from(User)).one()

    def get_users(self, skip: int = 0, limit: int = 10) -> list[User]:
        if not isinstance(skip, int) or skip < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skip must be a non-negative integer"
            )
        
        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be a positive integer between 1 and 100"
            )
        
        return self.session.exec(
            select(User)
            .offset(skip)
            .limit(limit)
        ).all()

    def get_user_by_id(self, user_id: int) -> User:
        return self._validate_user_id(user_id)

    async def update_user(self, user: User, update_data: dict, image: UploadFile | None = None) -> User:
        # Validate image if provided
        self._validate_image(image)
        
        # Validate update data
        for key, value in update_data.items():
            if key == "firstname":
                self._validate_name(value, "First name")
            elif key == "lastname":
                self._validate_name(value, "Last name")
        
        for key, value in update_data.items():
            setattr(user, key, value)
        
        # Handle profile image
        if image is not None:
            if user.image_url:
                await image_service.delete_image(user.image_url)
            
            if image:
                image_path = image_service.get_image_url(await image_service.save_image(image, "users"))
                user.image_url = image_path
            else:
                user.image_url = None
        
        user.updated_at = datetime.utcnow()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    async def delete_user(self, user: User) -> None:
        # Delete profile image if exists
        if user.image_url:
            await image_service.delete_image(user.image_url)
        # Delete related reviews, likes, and views
        from app.models.interaction_model import Review, Like, View
        self.session.exec(delete(Review).where(Review.user_id == user.id))
        self.session.exec(delete(Like).where(Like.user_id == user.id))
        self.session.exec(delete(View).where(View.user_id == user.id))
        self.session.commit()
        self.session.delete(user)
        self.session.commit()

    def update_user_role(self, user: User, role: UserRole) -> User:
        self._validate_role(role.value)
        user.role = role
        user.updated_at = datetime.utcnow()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user 
    
    def update_user_tariff(self, user: User, tariff_id: int) -> User:
        self._validate_tariff(tariff_id=tariff_id)
        
        # Get the tariff to access its duration
        tariff = self.session.get(Tariff, tariff_id)
        if not tariff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tariff with ID {tariff_id} not found"
            )
            
        # Calculate expiry date based on tariff duration
        expiry_date = datetime.utcnow() + timedelta(days=tariff.duration_days)
        
        user.tariff_id = tariff_id
        user.tariff_expires_at = expiry_date
        user.updated_at = datetime.utcnow()
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user