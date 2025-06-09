# fastapi_backend/app/models/base.py
# 모든 SQLAlchemy 모델의 기반이 되는 Base 클래스 및 공통 필드 정의 (선택적)

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    모든 SQLAlchemy 모델이 상속할 기본 클래스입니다.
    타입 어노테이션 기반의 SQLAlchemy 2.0 스타일을 따릅니다.
    """

    pass


# 만약 모든 테이블에 공통적으로 들어갈 컬럼 (예: id, created_at, updated_at)이 있다면,
# Base 클래스에 직접 정의하거나, 믹스인(Mixin) 클래스를 만들어 상속받게 할 수 있습니다.
# 여기서는 간단히 Base만 정의하고, 각 모델에서 필요에 따라 컬럼을 추가합니다.

# 예시: 공통 ID 컬럼 (모든 모델에서 id를 기본 키로 사용한다면)
# class BaseWithId(DeclarativeBase):
#     id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)

# 예시: 공통 타임스탬프 믹스인
# class TimestampMixin:
#     created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), server_default=func.now())
#     updated_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), server_default=func.now(), server_onupdate=func.now())

# 사용 시: class User(Base, TimestampMixin): ...
