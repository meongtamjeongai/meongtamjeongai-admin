# api/user.py
from typing import Any, Dict, List

import requests


class UserMixin:
    """사용자 관리 관련 API 메서드"""

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

    def update_user(
        self, token: str, user_id: int, update_data: Dict[str, Any]
    ) -> bool:
        """[Admin] 사용자 정보를 업데이트합니다. (원본 코드에 따라 추가됨)"""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/users/{user_id}"
        try:
            response = requests.put(url, headers=headers, json=update_data, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"사용자 정보 업데이트 실패: {e}")
            return False

    def delete_user(self, token: str, user_id: int) -> bool:
        """[Admin] 사용자를 삭제합니다. (원본 코드에 따라 추가됨)"""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/users/{user_id}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"사용자 삭제 실패: {e}")
            return False