from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session
from app.db.session import get_session
from app.models.user_model import User
from app.schemas.user_schema import (
    UserCreate, UserResponse, UserVerifyRequest, UserLogin, PasswordReset
)
from app.crud.auth_crud import AuthCRUD
from app.core.rate_limit import rate_limit
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(times=5, minutes=60)
async def register_user(
    user_data: UserCreate = Depends(UserCreate.as_form),
    image: UploadFile = File(None),
    session: Session = Depends(get_session)
):
    """Register a new user with optional profile image."""
    try:
        crud = AuthCRUD(session)
        user = await crud.register_user(user_data.model_dump(), image)
        return UserResponse(
            message="User registered successfully. Please verify your account.",
            user=user
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )

@router.post("/send-verification", response_model=dict)
@rate_limit(times=3, minutes=15)
async def send_verification_code(
    login: str = Form(...),
    session: Session = Depends(get_session)
):
    """Send verification code to user's phone/email."""
    crud = AuthCRUD(session)
    await crud.send_verification_code(login)
    return {"message": "Verification code sent successfully. Please check your phone or email."}

@router.post("/verify", response_model=dict, status_code=status.HTTP_200_OK)
@rate_limit(times=3, minutes=15)
async def verify_user(
    verify_data: UserVerifyRequest = Depends(UserVerifyRequest.as_form),
    session: Session = Depends(get_session)
):
    """Verify user's phone/email."""
    crud = AuthCRUD(session)
    await crud.verify_user(verify_data.login, verify_data.code)
    return {"message": "User verified successfully"}

@router.post("/login", response_model=dict)
@rate_limit(times=5, minutes=15)
async def login(
    login_data: UserLogin = Depends(UserLogin.as_form),
    session: Session = Depends(get_session)
):
    """Login user and return access and refresh tokens."""
    crud = AuthCRUD(session)
    access_token, refresh_token = await crud.login_user(login_data.login, login_data.password)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=dict)
@rate_limit(times=5, minutes=15)
async def refresh_token(
    refresh_token: str,
    session: Session = Depends(get_session)
):
    """Get a new access token using refresh token."""
    crud = AuthCRUD(session)
    access_token = await crud.refresh_access_token(refresh_token)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.patch("/reset-password", response_model=dict, status_code=status.HTTP_201_CREATED)
@rate_limit(times=3, minutes=60)
async def reset_password(
    reset_data: PasswordReset = Depends(PasswordReset.as_form),
    session: Session = Depends(get_session)
):
    """Update user's password."""
    try:
        crud = AuthCRUD(session)
        await crud.reset_password(reset_data.login, reset_data.new_password, reset_data.verification_code)
        return {"message": "Password reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )
