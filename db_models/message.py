# streamlit_admin/db_models/message.py

import enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 상대 경로 임포트로 수정
from .base import Base

if TYPE_CHECKING:
    # 상대 경로 임포트로 수정
    from .conversation import Conversation  # noqa: F401


class SenderType(str, enum.Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    conversation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_type: Mapped[SenderType] = mapped_column(
        SQLAlchemyEnum(SenderType, name="sendertypeenum"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    gemini_token_usage: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now(), index=True
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_type='{self.sender_type.value}')>"
