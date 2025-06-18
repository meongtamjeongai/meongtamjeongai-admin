# api/phishing.py
from typing import Any, Dict, List

import requests


class PhishingMixin:
    """피싱 정보 관련 API 메서드"""

    def get_phishing_categories(self) -> List[Dict[str, Any]] | None:
        url = f"{self.base_url}/phishing/categories"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"피싱 유형 목록 조회 실패: {e}")
            return None

    def get_all_phishing_cases(self, token: str) -> List[Dict[str, Any]] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/phishing/cases?limit=200"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"피싱 사례 목록 조회 실패: {e}")
            return None

    def create_phishing_case(
        self, token: str, case_data: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/phishing-cases"
        try:
            response = requests.post(url, headers=headers, json=case_data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"피싱 사례 생성 실패: {e}")
            return e.response.json() if e.response else None

    def update_phishing_case(
        self, token: str, case_id: int, case_data: Dict[str, Any]
    ) -> Dict[str, Any] | None:
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
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/admin/phishing-cases/{case_id}"
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"피싱 사례 삭제 실패: {e}")
            return False

    def get_phishing_case_by_id(
        self, token: str, case_id: int
    ) -> Dict[str, Any] | None:
        """ID를 사용하여 특정 피싱 사례의 상세 정보를 조회합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/phishing/cases/{case_id}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"피싱 사례 상세 조회 실패 (ID: {case_id}): {e}")
            return None
