# api/persona.py
from typing import Any, Dict, List

import requests


class PersonaMixin:
    """페르소나 관리 관련 API 메서드"""

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
        self,
        token: str,
        name: str,
        system_prompt: str,
        description: str | None,
        profile_image_key: str | None,
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/personas/"
        payload = {
            "name": name,
            "system_prompt": system_prompt,
            "description": description,
            "is_public": True,
            "profile_image_key": profile_image_key,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"페르소나 생성 실패: {e}")
            return None

    def delete_persona(self, token: str, persona_id: int) -> bool:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/personas/{persona_id}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"페르소나 삭제 실패: {e}")
            return False

    def update_persona(
        self, token: str, persona_id: int, update_data: Dict[str, Any]
    ) -> bool:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/personas/{persona_id}"
        try:
            response = requests.put(url, headers=headers, json=update_data, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"페르소나 업데이트 실패: {e}")
            return False