from fastapi import Depends, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select
from typing import List, Optional

from app.models.user_model import UserRole
from app.db.session import get_session
from app.models.user_model import User
from app.core.config import settings
from app.models.tariff_model import Tariff
from app.models.card_model import Card
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """Decode JWT token, verify, and return the User from DB."""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT with SECRET_KEY and ALGORITHM
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        login: str = payload.get("sub")
        
        # Check token claims
        if login is None:
            raise credentials_exception
        
        # Fetch user by login
        user = session.exec(select(User).where(User.login == login)).first()
        
        if user is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    return user

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the user is an admin."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for non-admin users"
        )
    return current_user

async def get_user_tariff(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> Optional[Tariff]:
    """Get the current user's active tariff."""
    if not current_user.tariff_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active tariff found. Please subscribe to a tariff."
        )
    
    tariff = session.get(Tariff, current_user.tariff_id)
    if not tariff or not tariff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your tariff is not active. Please subscribe to a valid tariff."
        )
    
    return tariff

class TariffValidator:
    def __init__(self, tariff: Tariff = Depends(get_user_tariff)):
        self.tariff = tariff

    def validate_social_media(self, social_media: dict) -> None:
        """Validate social media links against tariff limits."""
        if len(social_media) > self.tariff.max_social_medias:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your tariff allows only {self.tariff.max_social_medias} social media links"
            )

    def validate_description(self, description: str) -> None:
        """Validate description length against tariff limits."""
        if len(description) > self.tariff.max_description_chars:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your tariff allows only {self.tariff.max_description_chars} characters in description"
            )

    def validate_phone_numbers(self, phone_numbers: list) -> None:
        """Validate phone numbers count against tariff limits."""
        if len(phone_numbers) > self.tariff.max_phone_numbers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your tariff allows only {self.tariff.max_phone_numbers} phone numbers"
            )

    def validate_images(self, images: list) -> None:
        """Validate images count against tariff limits."""
        if len(images) > self.tariff.max_images:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your tariff allows only {self.tariff.max_images} images"
            )

    def validate_website(self, has_website: bool) -> None:
        """Validate website feature against tariff limits."""
        if has_website and not self.tariff.has_website:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your tariff does not include website feature"
            )

    def validate_card(self, card: Card, images: list, phone_numbers: list) -> None:
        """Validate all card features against tariff limits."""
        self.validate_social_media(card.social_media)
        self.validate_description(card.description)
        self.validate_phone_numbers(phone_numbers)
        self.validate_images(images)
        self.validate_website(card.has_website if hasattr(card, 'has_website') else False)