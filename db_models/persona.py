# streamlit_admin/db_models/persona.py

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 상대 경로 임포트로 수정
from .base import Base

if TYPE_CHECKING:
    # 상대 경로 임포트로 수정
    from .conversation import Conversation  # noqa: F401
    from .user import User  # noqa: F401


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    profile_image_url: Mapped[str] = mapped_column(String(2048), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User", back_populates="created_personas", foreign_keys=[created_by_user_id]
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="persona", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Persona(id={self.id}, name='{self.name}')>"   