# streamlit_admin/api_client.py

import os
import requests
from typing import Dict, Any, List

class ApiClient:
    """
    FastAPI 백엔드와 통신하기 위한 클라이언트.
    """
    def __init__(self):
        self.base_url = os.getenv("FASTAPI_API_BASE_URL", "http://localhost:8000/api/v1")

    # --- 인증 API ---
    def login_for_token(self, email: str, password: str) -> str | None:
        login_data = {'username': email, 'password': password}
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

    def create_initial_superuser(self, email: str, password: str) -> Dict[str, Any] | None:
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

    # --- 사용자 관리 API ---
    def get_all_users(self, token: str) -> List[Dict[str, Any]] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/users"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"사용자 목록 조회 실패: {e}")
            return None

    # --- 페르소나 관리 API ---
    def get_personas(self, token: str) -> List[Dict[str, Any]] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/personas/"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"페르소나 목록 조회 실패: {e}")
            return None

    def create_persona(self, token: str, name: str, system_prompt: str, description: str | None) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/personas/"
        payload = {
            "name": name,
            "system_prompt": system_prompt,
            "description": description,
            "is_public": True
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"페르소나 생성 실패: {e}")
            return None

    # --- 대화방 관리 API ---
    def create_conversation(self, token: str, persona_id: int, title: str | None) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/conversations/"
        payload = {"persona_id": persona_id}
        if title:
            payload["title"] = title
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"대화방 생성 실패: {e}")
            return None

    # --- 메시지 API ---
    def send_message(self, token: str, conversation_id: int, content: str) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/conversations/{conversation_id}/messages/"
        payload = {"content": content}
        try:
            # AI 응답은 시간이 걸릴 수 있으므로 타임아웃을 길게 설정
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"메시지 전송 실패: {e}")
            return None