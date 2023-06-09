import contextlib
import uuid

from sqlalchemy.dialects.postgresql import UUID as _UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import CHAR, TypeDecorator

from utils import get_env_var

engine = create_async_engine(get_env_var("DB_URL"))


class Base(DeclarativeBase):
    pass


# noinspection PyAbstractClass
class UUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    http://docs.sqlalchemy.org/en/latest/core/custom_types.html#backend-agnostic-guid-type
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    # noinspection PyUnresolvedReferences
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


@contextlib.asynccontextmanager
async def session_scope(autocommit=True):
    async with AsyncSession(engine) as session:
        try:
            yield session

            if autocommit:
                await session.commit()
        except BaseException:
            await session.rollback()
            raise


async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
