import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

def generate_uuid() -> str:
    return str(uuid.uuid4())
