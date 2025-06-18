from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlmodel import Session
from app.db.session import get_session
from app.models.user_model import User, UserRole
from app.schemas.user_schema import (
    UserRead, UserUpdate, UserResponse,
    UserListResponse, UserRoleUpdate
)
from app.dependencies import get_current_user, get_admin_user
from app.crud.user_crud import UserCRUD
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List all users (admin only)."""
    try:
        crud = UserCRUD(session)
        total = crud.get_total_users()
        users = crud.get_users(skip, limit)
        
        return UserListResponse(
            total=total,
            users=users,
            page=(skip // limit) + 1,
            size=limit
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )

@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get a user by ID (self or admin)."""
    try:
        crud = UserCRUD(session)
        user = crud.get_user_by_id(user_id)
        
        if current_user.id != user_id and current_user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this user"
            )
        return user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user: {str(e)}"
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate = Depends(UserUpdate.as_form),
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a user with optional profile image (self or admin)."""
    crud = UserCRUD(session)
    user = crud.get_user_by_id(user_id)
    
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    update_data = user_data.model_dump(exclude_unset=True)
    updated_user = await crud.update_user(user, update_data, image)
    
    return UserResponse(
        message="User updated successfully",
        user=updated_user
    )

@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a user (self or admin)."""
    crud = UserCRUD(session)
    user = crud.get_user_by_id(user_id)
        
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )
    
    await crud.delete_user(user)
    return {"message": "User deleted successfully"}

@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update a user's role (admin only)."""
    try:
        crud = UserCRUD(session)
        user = crud.get_user_by_id(user_id)
        updated_user = crud.update_user_role(user, role_data.role)
        
        return UserResponse(
            message="User role updated successfully",
            user=updated_user
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )

@router.patch("/{user_id}/tariff/{tariff_id}", response_model=UserResponse)
async def update_user_tariff(
    user_id: int,
    tariff_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update a user's tariff (admin only)."""
    try:
        crud = UserCRUD(session)
        user = crud.get_user_by_id(user_id)
        updated_user = crud.update_user_tariff(user, tariff_id)
        
        return UserResponse(
            message="User tariff updated successfully",
            user=updated_user
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user tariff: {str(e)}"
        )