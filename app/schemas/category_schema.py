from fastapi import Form
from pydantic import BaseModel
from typing import Optional

class CategoryCreate(BaseModel):
    name: str
    description: str
    
    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        description: str = Form(...),
    ):
        return cls(name=name, description=description)

class CategoryRead(BaseModel):
    id: int
    name: str
    description: str
    image_url: str

    class Config:
        from_attributes = True

class CategoryUpdate(BaseModel):
    name: str
    description: str
    
    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        description: str = Form(...),
    ):
        return cls(name=name, description=description) 