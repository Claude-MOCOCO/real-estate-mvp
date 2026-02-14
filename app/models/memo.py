import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, TimestampMixin, UUIDMixin


class Memo(UUIDMixin, TimestampMixin, Base):
    """메모 테이블 (파싱 실패 시 임시 저장)"""

    __tablename__ = "memos"
    __table_args__ = (
        Index("ix_memos_agent_resolved", "agent_id", "resolved"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="memos")  # noqa: F821

    @validates("content")
    def validate_content(self, key: str, value: str) -> str:
        if len(value) > 5000:
            raise ValueError("메모 내용은 5000자를 초과할 수 없습니다.")
        return value
