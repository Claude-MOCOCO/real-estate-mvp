import uuid

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Memo(UUIDMixin, TimestampMixin, Base):
    """메모 테이블 (파싱 실패 시 임시 저장)"""

    __tablename__ = "memos"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="memos")  # noqa: F821
