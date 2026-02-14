import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.schemas.property import PropertyStatus


class Property(UUIDMixin, TimestampMixin, Base):
    """매물 테이블 (하이브리드 구조: 정형 컬럼 + JSONB)"""

    __tablename__ = "properties"
    __table_args__ = (
        Index("ix_properties_agent_status", "agent_id", "status"),
        Index("ix_properties_agent_status_type", "agent_id", "status", "transaction_type"),
        Index("ix_properties_agent_status_gugun", "agent_id", "status", "address_gugun"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )

    # 정형 컬럼 (자주 필터링되는 핵심 필드)
    transaction_type: Mapped[str | None] = mapped_column(String(10))  # 매매/전세/월세
    price_main: Mapped[int | None] = mapped_column(BigInteger)  # 주 가격 (원)
    price_monthly: Mapped[int | None] = mapped_column(BigInteger)  # 월세 (원)
    area_pyeong: Mapped[float | None] = mapped_column(Numeric(6, 1))  # 평수
    address_sido: Mapped[str | None] = mapped_column(String(20))
    address_gugun: Mapped[str | None] = mapped_column(String(20))
    address_dong: Mapped[str | None] = mapped_column(String(30))
    building_name: Mapped[str | None] = mapped_column(String(50))

    # JSONB (유연한 추가 정보)
    extra: Mapped[dict] = mapped_column(JSONB, server_default="{}", default=dict)

    # 원문 보존 (파싱 검증용)
    raw_input: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(10), server_default=PropertyStatus.ACTIVE.value, default=PropertyStatus.ACTIVE.value
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="properties")  # noqa: F821
