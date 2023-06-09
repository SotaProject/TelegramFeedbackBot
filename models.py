from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from db_utils import Base as BaseModel
import datetime


def get_datetime_now():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


class User(BaseModel):
    __tablename__ = "users"
    tid: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True, primary_key=True
    )
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    reputation: Mapped[int] = mapped_column(Integer, default=0)
    ban: Mapped[bool] = mapped_column(Boolean, default=False)
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class FeedbackMessage(BaseModel):
    __tablename__ = "feedback_messages"
    id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, autoincrement=True, primary_key=True
    )
    from_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    from_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    to_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    to_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String)
