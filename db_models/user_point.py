# streamlit_admin/db_models/user_point.py

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 상대 경로 임포트로 수정
from .base import Base

if TYPE_CHECKING:
    # 상대 경로 임포트로 수정
    from .user import User  # noqa: F401


class UserPoint(Base):
    __tablename__ = "user_points"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_point")

    def __repr__(self):
        return f"<UserPoint(user_id={self.user_id}, points={self.points})>"
