# streamlit_admin/db_models/conversation.py

from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 상대 경로 임포트로 수정
from .base import Base

if TYPE_CHECKING:
    # 상대 경로 임포트로 수정
    from .message import Message  # noqa: F401
    from .persona import Persona  # noqa: F401
    from .user import User  # noqa: F401


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    persona_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )
    last_message_at: Mapped[DateTime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        server_default=func.now(),
        server_onupdate=func.now(),
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    persona: Mapped["Persona"] = relationship(
        "Persona", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, persona_id={self.persona_id}, title='{self.title}')>"
