from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status
from app.models.tariff_model import Tariff
from app.schemas.tariff_schema import TariffCreate, TariffUpdate
import logging

logger = logging.getLogger(__name__)

class TariffCRUD:
    def __init__(self, session: Session):
        self.session = session

    async def get_tariff_by_id(self, tariff_id: int) -> Tariff:
        tariff = self.session.get(Tariff, tariff_id)
        if not tariff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tariff not found"
            )
        return tariff

    async def get_tariffs(
        self,
        skip: int = 0,
        limit: int = 10,
        active_only: bool = False
    ) -> List[Tariff]:
        query = select(Tariff)
        if active_only:
            query = query.where(Tariff.is_active == True)
        query = query.offset(skip).limit(limit)
        return list(self.session.exec(query))

    async def get_total_tariffs(self, active_only: bool = False) -> int:
        query = select(Tariff)
        if active_only:
            query = query.where(Tariff.is_active == True)
        return len(list(self.session.exec(query)))

    async def create_tariff(
        self,
        tariff_data: TariffCreate,
        current_user_id: int
    ) -> Tariff:
        tariff = Tariff(
            **tariff_data.model_dump(),
            created_by_id=current_user_id
        )
        self.session.add(tariff)
        self.session.commit()
        self.session.refresh(tariff)
        return tariff

    async def update_tariff(
        self,
        tariff: Tariff,
        tariff_data: TariffUpdate
    ) -> Tariff:
        update_data = tariff_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tariff, field, value)
        tariff.updated_at = datetime.utcnow()
        self.session.add(tariff)
        self.session.commit()
        self.session.refresh(tariff)
        return tariff

    async def delete_tariff(self, tariff: Tariff) -> None:
        self.session.delete(tariff)
        self.session.commit() 