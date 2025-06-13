# api/auth.py
from typing import Any, Dict

import requests


class AuthMixin:
    """인증 및 초기 설정 관련 API 메서드"""

    def login_for_token(self, email: str, password: str) -> str | None:
        login_data = {"username": email, "password": password}
        url = f"{self.base_url}/auth/token"
        try:
            response = requests.post(url, data=login_data, timeout=5)
            response.raise_for_status()
            return response.json().get("access_token")
        except requests.exceptions.RequestException as e:
            print(f"API 로그인 요청 실패: {e}")
            return None

    def check_superuser_exists(self) -> bool:
        url = f"{self.base_url}/admin/superuser-exists"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            if isinstance(response.json(), bool):
                return response.json()
            return True
        except requests.exceptions.RequestException as e:
            print(f"슈퍼유저 존재 여부 확인 실패: {e}")
            return True

    def create_initial_superuser(
        self, email: str, password: str
    ) -> Dict[str, Any] | None:
        url = f"{self.base_url}/admin/initial-superuser"
        payload = {"email": email, "password": password}
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"최초 슈퍼유저 생성 실패: {e}")
            try:
                return e.response.json() if e.response else {"detail": str(e)}
            except:
                return {"detail": str(e)}