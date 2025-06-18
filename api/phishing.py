# api/phishing.py
import json
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

    def analyze_image_for_phishing(
        self, token: str, image_base64: str
    ) -> Dict[str, Any] | None:
        """Base64로 인코딩된 이미지를 전송하여 피싱 위험도 분석을 요청합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/phishing/analyze-image"
        payload = {"image_base64": image_base64}
        try:
            # 이미지 분석은 시간이 걸릴 수 있으므로 timeout을 넉넉하게 설정
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"이미지 분석 API 요청 실패: {e}")
            # 서버에서 보낸 에러 메시지가 있다면 반환
            if e.response is not None:
                try:
                    return e.response.json()
                except json.JSONDecodeError:
                    return {"detail": e.response.text}
            return None
