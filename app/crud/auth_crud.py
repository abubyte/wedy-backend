from sqlmodel import Session, select
from datetime import datetime, timedelta
from fastapi import HTTPException, status, UploadFile
from app.models.user_model import User
from app.core.security import create_access_token, get_password_hash, create_tokens, verify_token
from app.core.image_service import ImageService
from app.external_services.email_service import EmailClient
from app.external_services.sms_service import EskizClient
import random
import string
import re
import logging

logger = logging.getLogger(__name__)
image_service = ImageService()

class AuthCRUD:
    def __init__(self, session: Session):
        self.session = session

    def get_user_by_login(self, login: str) -> User:
        user = self.session.exec(
            select(User).where(User.login == login)
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    async def register_user(self, user_data: dict, image: UploadFile | None = None) -> User:
        # Check if user with same login exists
        existing_user = self.session.exec(
            select(User).where(User.login == user_data["login"])
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this login already exists"
            )

        # Create new user
        user_dict = user_data.copy()
        user_dict.update({
            "hashed_password": get_password_hash(user_dict.pop("password")),
        })
        
        user = User(**user_dict)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        # Handle profile image if provided
        if image:
            image_path = image_service.get_image_url(await image_service.save_image(image, "users"))
            user.image_url = image_path
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

        return user

    async def send_verification_code(self, login: str) -> None:
        user = self.get_user_by_login(login)

        # Create verification code
        verification_code = ''.join(random.choices(string.digits, k=6))
        verification_expires = datetime.utcnow() + timedelta(minutes=15)

        user.verification_code = verification_code
        user.verification_code_expires = verification_expires

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        # Send verification code
        logger.info(f"Verification code for user {user.id}: {verification_code}")
        if re.match(r"^\+998\d{9}$", login):
            EskizClient().send_sms(phone=login.removeprefix("+"), message=f'Wedy mobil ilovasi uchun tasdiqlash kodi: {verification_code}')
        elif re.match(r"^[^@]+@[^@]+\.[^@]+$", login):
            subject = "Tasdiqlash kodi"
            body = f"Wedy uchun tasdiqlash kodi: {verification_code}"
            EmailClient().send_email(login, subject, body)

    async def verify_user(self, login: str, code: str) -> None:
        user = self.get_user_by_login(login)
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already verified"
            )
        
        if not user.verification_code or not user.verification_code_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification code found"
            )
        
        if datetime.utcnow() > user.verification_code_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code expired"
            )
        
        if user.verification_code != code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires = None
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

    async def login_user(self, login: str, password: str) -> tuple[str, str]:
        user = self.get_user_by_login(login)
        
        if not user.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect login or password"
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your account first"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.session.add(user)
        self.session.commit()
        
        # Create both access and refresh tokens
        return create_tokens(data={"sub": user.login})

    async def refresh_access_token(self, refresh_token: str) -> str:
        username = verify_token(refresh_token)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = self.get_user_by_login(username)
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new access token
        return create_access_token(data={"sub": user.login})

    async def reset_password(self, login: str, new_password: str, verification_code: str) -> None:
        user = self.get_user_by_login(login)
        
        if not user.verification_code or not user.verification_code_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification code found"
            )
        
        if datetime.utcnow() > user.verification_code_expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code expired"
            )
        
        if user.verification_code != verification_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        user.hashed_password = get_password_hash(new_password)
        user.verification_code = None
        user.verification_code_expires = None
        user.updated_at = datetime.utcnow()
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user) 