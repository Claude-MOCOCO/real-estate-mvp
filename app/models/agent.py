from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Agent(UUIDMixin, TimestampMixin, Base):
    """공인중개사(사용자) 테이블"""

    __tablename__ = "agents"

    kakao_user_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(50))

    properties: Mapped[list["Property"]] = relationship(  # noqa: F821
        back_populates="agent", lazy="select"
    )
    memos: Mapped[list["Memo"]] = relationship(  # noqa: F821
        back_populates="agent", lazy="select"
    )
