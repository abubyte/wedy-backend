from sqlmodel import SQLModel, Field
from typing import Optional


class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = Field(default=None)
    image_url: str = Field(default=None)