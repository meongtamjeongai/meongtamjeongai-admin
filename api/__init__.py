# api/__init__.py
import os

from .auth import AuthMixin
from .conversation import ConversationMixin
from .persona import PersonaMixin
from .phishing import PhishingMixin
from .storage import StorageMixin
from .user import UserMixin


class ApiClient(
    AuthMixin,
    ConversationMixin,
    PersonaMixin,
    PhishingMixin,
    StorageMixin,
    UserMixin,
):
    """
    FastAPI 백엔드와 통신하기 위한 클라이언트.
    각 기능별 Mixin 클래스를 상속받아 구성됩니다.
    """

    def __init__(self):
        self.base_url = os.getenv("FASTAPI_API_BASE_URL", "http://app:80/api/v1")
