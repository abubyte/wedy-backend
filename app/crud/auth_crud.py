from sqlmodel import Session, select
from datetime import datetime, timedelta
from fastapi import HTTPException, status, UploadFile
from app.models.user_model import User
from app.models.tariff_model import Tariff
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

        # Get free tariff
        free_tariff = self.session.exec(
            select(Tariff).where(Tariff.price == 0)
        ).first()
        
        if not free_tariff:
            # Create free tariff if it doesn't exist
            free_tariff = Tariff(
                name="Free",
                description="Basic free tariff with limited features",
                price=0,
                duration_days=30,  # 30 days trial
                is_active=True,
                search_priority=0,
                has_website=False,
                max_social_medias=2,
                max_description_chars=200,
                max_phone_numbers=1,
                max_images=3,
                created_at=datetime.utcnow()
            )
            self.session.add(free_tariff)
            self.session.commit()
            self.session.refresh(free_tariff)

        # Create new user with free tariff
        user_dict = user_data.copy()
        user_dict.update({
            "hashed_password": get_password_hash(user_dict.pop("password")),
            "tariff_id": free_tariff.id,
            "tariff_expires_at": datetime.utcnow() + timedelta(days=free_tariff.duration_days)
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
        try:
            if re.match(r"^\+998\d{9}$", login):
                logger.info(f"Sending SMS verification code to {login}")
                EskizClient().send_sms(phone=login.removeprefix("+"), message=f'Wedy mobil ilovasi uchun tasdiqlash kodi: {verification_code}')
                logger.info(f"SMS verification code sent successfully to {login}")
            elif re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", login):
                logger.info(f"Sending email verification code to {login}")
                subject = "Tasdiqlash kodi"
                body = f"Wedy uchun tasdiqlash kodi: {verification_code}"
                email_sent = EmailClient().send_email(login, subject, body)
                if not email_sent:
                    logger.error(f"Failed to send email verification code to {login}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to send verification email. Please try again later."
                    )
                logger.info(f"Email verification code sent successfully to {login}")
            else:
                logger.error(f"Invalid login format: {login}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid login format. Please use a valid phone number (+998XXXXXXXXX) or email address."
                )
        except HTTPException:
            # Re-raise HTTPExceptions to preserve status codes
            raise
        except Exception as e:
            logger.error(f"Failed to send verification code to {login}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification code. Please try again later."
            )

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