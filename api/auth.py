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

    def get_server_version(self) -> Dict[str, Any] | None:
        """백엔드 서버의 버전 정보를 조회합니다."""
        url = f"{self.base_url.replace('/api/v1', '')}/version"
        try:
            response = requests.get(url, timeout=3)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"서버 버전 조회 실패: {e}")
            return None
        
    def check_superuser_exists(self) -> bool:
        """
        슈퍼유저 존재 여부를 확인합니다.
        성공 시 bool 값을 반환하고, API 통신 실패 시 RequestException을 발생시킵니다.
        """
        url = f"{self.base_url}/admin/superuser-exists"
        try:
            response = requests.get(url, timeout=5)
            # HTTP 상태 코드가 2xx가 아니면 예외 발생
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, bool):
                # API가 예상치 못한 형식의 응답을 준 경우도 에러로 처리
                raise ValueError(f"API로부터 boolean이 아닌 응답을 받았습니다: {data}")
            return data
        except requests.exceptions.RequestException as e:
            # ✅ 수정: 예외를 잡은 후, 로그만 남기고 다시 발생시켜 호출자에게 알림
            print(f"API 통신 실패 (check_superuser_exists): {e}")
            raise e

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