# streamlit_admin/api_client.py

import os
from typing import Any, Dict, List

import requests


class ApiClient:
    """
    FastAPI 백엔드와 통신하기 위한 클라이언트.
    """

    def __init__(self):
        self.base_url = os.getenv("FASTAPI_API_BASE_URL", "http://app:8000/api/v1")

    # --- 인증 API ---
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

    def create_persona(
        self, token: str, name: str, system_prompt: str, description: str | None
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/personas/"
        payload = {
            "name": name,
            "system_prompt": system_prompt,
            "description": description,
            "is_public": True,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"페르소나 생성 실패: {e}")
            return None

    # --- 대화방 관리 API ---
    def create_conversation(
        self, token: str, persona_id: int, title: str | None
    ) -> Dict[str, Any] | None:
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

    # 👇 관리자용 대화방 생성 함수 추가
    def create_conversation_admin(
        self, token: str, user_id: int, persona_id: int, title: str | None
    ) -> Dict[str, Any] | None:
        """[Admin] 관리자가 특정 사용자와 페르소나를 지정하여 새 대화방을 생성합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations"
        payload = {"user_id": user_id, "persona_id": persona_id, "title": title}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방 생성 실패: {e}")
            # 에러 응답이 JSON 형태일 경우, 그 내용을 반환하여 UI에 표시할 수 있도록 함
            if e.response:
                try:
                    return e.response.json()
                except ValueError:
                    return {"detail": e.response.text}
            return None

    # --- ⭐️ 피싱 정보 API (신규) ⭐️ ---

    def get_phishing_categories(self) -> List[Dict[str, Any]] | None:
        """모든 피싱 유형 목록을 조회합니다."""
        url = f"{self.base_url}/phishing/categories"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"피싱 유형 목록 조회 실패: {e}")
            return None

    def get_all_phishing_cases(self, token: str) -> List[Dict[str, Any]] | None:
        """[Admin] 모든 피싱 사례 목록을 조회합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        # 👇 [수정] limit 값을 백엔드 허용 범위인 200으로 변경
        url = f"{self.base_url}/phishing/cases?limit=200"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # 디버깅 코드는 그대로 두거나, 이제 원인을 알았으니 제거해도 좋습니다.
            print("=" * 50)
            print("피싱 사례 목록 조회(GET) API 요청 실패!")
            if e.response is not None:
                print(f"Status Code: {e.response.status_code}")
                print(f"Response Body: {e.response.text}")
            else:
                print(f"Request Error: {e}")
            print("=" * 50)
            return None

    def create_phishing_case(
        self, token: str, case_data: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """[Admin] 새 피싱 사례를 생성합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/phishing-cases"
        try:
            response = requests.post(url, headers=headers, json=case_data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # 👇 [디버깅] 에러 발생 시 상세 내용을 터미널에 출력
            print("=" * 50)
            print("피싱 사례 생성 API 요청 실패!")
            if e.response is not None:
                print(f"Status Code: {e.response.status_code}")
                print(f"Response Body: {e.response.text}")  # 가장 중요한 정보
            else:
                print(f"Request Error: {e}")
            print("=" * 50)

            return e.response.json() if e.response else None

    def update_phishing_case(
        self, token: str, case_id: int, case_data: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """[Admin] 기존 피싱 사례를 수정합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/phishing-cases/{case_id}"
        try:
            response = requests.put(url, headers=headers, json=case_data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"피싱 사례 수정 실패: {e}")
            return e.response.json() if e.response else None

    def delete_phishing_case(self, token: str, case_id: int) -> bool:
        """[Admin] 피싱 사례를 삭제합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/phishing-cases/{case_id}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"피싱 사례 삭제 실패: {e}")
            return False

    # --- ⭐️ 대화방 관리 API (신규: 관리자용) ⭐️ ---
    def get_all_conversations_admin(
        self, token: str, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]] | None:
        """[Admin] 시스템의 모든 대화방 목록을 조회합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations"
        params = {"skip": skip, "limit": limit}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방 목록 조회 실패: {e}")
            return None

    def get_messages_for_conversation_admin(
        self, token: str, conversation_id: int
    ) -> List[Dict[str, Any]] | None:
        """[Admin] 특정 대화방의 메시지 목록을 조회합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations/{conversation_id}/messages"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"관리자용 메시지 목록 조회 실패: {e}")
            return None

    def delete_conversation_admin(self, token: str, conversation_id: int) -> bool:
        """[Admin] 특정 대화방을 삭제합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations/{conversation_id}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방 삭제 실패: {e}")
            return False

    # --- 메시지 API ---
    def send_message(
        self, token: str, conversation_id: int, content: str
    ) -> Dict[str, Any] | None:
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
