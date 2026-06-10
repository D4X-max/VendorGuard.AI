from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Generic async repository.
    Subclass this and pass the SQLAlchemy model type.
    All methods are RLS-safe because the session already
    has SET LOCAL app.current_tenant_id applied by the dependency.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 20) -> tuple[List[ModelType], int]:
        count_result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(self.model)
            .order_by(self.model.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, id) -> bool:
        obj = await self.get_by_id(id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.flush()
        return True