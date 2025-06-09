from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.models.user_model import UserRole
from app.db.session import  get_session
from app.models.user_model import User
from app.core.config import settings


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