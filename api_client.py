# api_client.py
import os
import requests
from typing import Dict, Any, List

class ApiClient:
    """
    FastAPI 백엔드와 통신하기 위한 클라이언트.
    """
    def __init__(self):
        # 환경 변수에서 베이스 URL을 가져옴. 없으면 로컬 기본값 사용.
        self.base_url = os.getenv("FASTAPI_API_BASE_URL", "http://localhost:8000/api/v1")

    def login_for_token(self, email: str, password: str) -> str | None:
        """
        이메일과 비밀번호로 로그인을 시도하고, 성공 시 JWT 액세스 토큰을 반환합니다.
        """
        login_data = {
            'username': email, # FastAPI의 OAuth2PasswordRequestForm은 'username' 필드를 사용
            'password': password
        }
        # ⭐️ 중요: FastAPI의 기본 로그인 엔드포인트는 /auth/token 입니다.
        # 관리자 로그인을 위해 별도 엔드포인트를 만들거나, 기존 것을 활용합니다.
        # 여기서는 기존 로그인 엔드포인트를 사용한다고 가정합니다.
        url = f"{self.base_url}/auth/token" # FastAPI의 기본 로그인 URL
        
        try:
            response = requests.post(url, data=login_data)
            response.raise_for_status()  # 2xx 상태 코드가 아니면 예외 발생
            
            # FastAPI의 슈퍼유저 검증은 /auth/token이 아닌,
            # /admin/** 엔드포인트 접근 시에 이루어집니다.
            # 따라서 여기서는 토큰만 먼저 받아옵니다.
            return response.json().get("access_token")
        except requests.exceptions.RequestException as e:
            print(f"API 로그인 요청 실패: {e}")
            return None

    def get_all_users(self, token: str) -> List[Dict[str, Any]] | None:
        """
        관리자용 엔드포인트에서 모든 사용자 목록을 가져옵니다.
        """
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/users"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # 401 Unauthorized (슈퍼유저 아님) 또는 403 Forbidden 등의 에러가 여기서 잡힙니다.
            print(f"사용자 목록 조회 실패: {e}")
            if e.response is not None:
                print(f"응답 내용: {e.response.text}")
            return None
        
    def update_user(self, token: str, user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        관리자가 특정 사용자의 정보를 업데이트합니다.
        """
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/users/{user_id}"
        
        try:
            response = requests.put(url, headers=headers, json=update_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"사용자 정보 업데이트 실패 (ID: {user_id}): {e}")
            if e.response is not None:
                print(f"응답 내용: {e.response.text}")
            return None

    def delete_user(self, token: str, user_id: int) -> Dict[str, Any] | None:
        """
        관리자가 특정 사용자를 삭제합니다.
        """
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/users/{user_id}"
        
        try:
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"사용자 삭제 실패 (ID: {user_id}): {e}")
            if e.response is not None:
                print(f"응답 내용: {e.response.text}")
            return None