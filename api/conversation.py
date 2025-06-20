# api/conversation.py
from typing import Any, Dict, List

import requests


class ConversationMixin:
    """대화방 및 메시지 관련 API 메서드"""

    # ✅ [추가] 특정 카테고리(DB 우선)로 대화방을 생성하는 관리자용 API 함수
    def create_conversation_with_category_admin(
        self,
        token: str,
        user_id: int,
        persona_id: int,
        category_code: str,
        title: str | None,
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations/with-category"
        payload = {
            "user_id": user_id,
            "persona_id": persona_id,
            "category_code": category_code,
            "title": title,
        }
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=20
            )  # AI 생성 가능성으로 타임아웃 증가
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방(카테고리 지정) 생성 실패: {e}")
            return self._handle_error_response(e)

    # ✅ [추가] 특정 카테고리(AI 생성)로 대화방을 생성하는 관리자용 API 함수
    def create_conversation_with_ai_case_admin(
        self,
        token: str,
        user_id: int,
        persona_id: int,
        category_code: str,
        title: str | None,
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations/with-ai-case"
        payload = {
            "user_id": user_id,
            "persona_id": persona_id,
            "category_code": category_code,
            "title": title,
        }
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=20
            )  # AI 생성 타임아웃 증가
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방(AI 생성) 생성 실패: {e}")
            return self._handle_error_response(e)

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

    def create_conversation_admin(
        self, token: str, user_id: int, persona_id: int, title: str | None
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations"
        payload = {"user_id": user_id, "persona_id": persona_id, "title": title}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방 생성 실패: {e}")
            if e.response:
                try:
                    return e.response.json()
                except ValueError:
                    return {"detail": e.response.text}
            return None

    def get_all_conversations_admin(
        self, token: str, skip: int = 0, limit: int = 100
    ) -> List[Dict[str, Any]] | None:
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
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/conversations/{conversation_id}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"관리자용 대화방 삭제 실패: {e}")
            return False

    def send_message(
        self,
        token: str,
        conversation_id: int,
        content: str,
        image_base64: str | None = None,
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/conversations/{conversation_id}/messages/"

        # --- 페이로드 구성 로직 ---
        payload = {"content": content}
        if image_base64:
            payload["image_base64"] = image_base64

        try:
            # 이미지 데이터는 클 수 있으므로 timeout을 60초로 늘립니다.
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"메시지 전송 실패: {e}")
            return None

    # 헬퍼 함수 추가 (에러 응답 공통 처리)
    def _handle_error_response(self, e: requests.exceptions.RequestException):
        if e.response:
            try:
                return e.response.json()
            except ValueError:
                return {"detail": e.response.text}
        return {"detail": str(e)}
