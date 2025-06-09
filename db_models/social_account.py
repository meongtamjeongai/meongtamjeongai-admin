# streamlit_admin/db_models/social_account.py

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 상대 경로 임포트로 수정
from .base import Base

if TYPE_CHECKING:
    # 상대 경로 임포트로 수정
    from .user import User  # noqa: F401


class SocialProvider(str, enum.Enum):
    FIREBASE_GOOGLE = "firebase_google"
    FIREBASE_ANONYMOUS = "firebase_anonymous"
    GUEST = "guest"


class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[SocialProvider] = mapped_column(
        SQLAlchemyEnum(
            SocialProvider, name="socialproviderenum", create_constraint=True
        ),
        nullable=False,
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="social_accounts")

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_provider_user_id_on_social_accounts",
        ),
    )

    def __repr__(self):
        return f"<SocialAccount(id={self.id}, user_id={self.user_id}, provider='{self.provider.value}', provider_user_id='{self.provider_user_id}')>"
