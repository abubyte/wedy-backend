from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session
from typing import List

from app.db.session import get_session
from app.schemas.category_schema import CategoryCreate, CategoryRead, CategoryUpdate
from app.dependencies import get_admin_user, get_current_user
from app.models import User, Category # Import Category model
from app.crud.category_crud import CategoryCRUD

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("", response_model=CategoryRead)
async def create_category(
    category_data: CategoryCreate = Depends(CategoryCreate.as_form),
    image: UploadFile = File(None),
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Create a new category (admin only)."""
    crud = CategoryCRUD(session)
    category = await crud.create_category(category_data.model_dump(), image)
    return category

@router.get("", response_model=List[CategoryRead])
async def list_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all categories (all users)."""
    crud = CategoryCRUD(session)
    categories = crud.get_categories()
    return categories

@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a category by ID (all users)."""
    crud = CategoryCRUD(session)
    category = crud.get_category_by_id(category_id)
    return category

@router.put("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate = Depends(CategoryUpdate.as_form),
    image: UploadFile = File(None),
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Update a category (admin only)."""
    crud = CategoryCRUD(session)
    category = await crud.update_category(category_id, category_data.model_dump(exclude_unset=True), image)
    return category

@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    current_user: User = Depends(get_admin_user),
    session: Session = Depends(get_session)
):
    """Delete a category (admin only)."""
    crud = CategoryCRUD(session)
    crud.delete_category(category_id)
    return {"message": "Category deleted"} 