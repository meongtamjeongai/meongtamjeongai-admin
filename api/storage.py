# api/storage.py
import logging
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


class StorageMixin:
    """S3 및 Presigned URL 관련 API 메서드"""

    def get_presigned_url_for_upload(
        self, token: str, filename: str, category: str
    ) -> Dict[str, Any] | None:
        """파일 업로드를 위한 Presigned URL을 백엔드로부터 받아옵니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/storage/presigned-url/upload"
        params = {"category": category}
        payload = {"filename": filename}
        logger.info(
            f"🚀 Presigned URL 요청 시작: URL={url}, Params={params}, Payload={payload}"
        )
        try:
            response = requests.post(
                url, headers=headers, params=params, json=payload, timeout=10
            )
            response.raise_for_status()
            logger.info(
                f"✅ Presigned URL 요청 성공: Status={response.status_code}, Response={response.json()}"
            )
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            try:
                error_detail = e.response.json()
            except requests.exceptions.JSONDecodeError:
                error_detail = e.response.text
            logger.error(
                f"🔥 Presigned URL 요청 실패 (HTTPError): Status={status_code}, Detail={error_detail}",
                exc_info=True,
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(
                f"🔥 Presigned URL 요청 실패 (RequestException): Error={e}", exc_info=True
            )
            return None

    def upload_file_to_s3(
        self, presigned_url: str, file_data: bytes, content_type: str
    ) -> bool:
        """주어진 Presigned URL로 실제 파일 데이터를 PUT 요청으로 업로드합니다."""
        headers = {"Content-Type": content_type}
        try:
            response = requests.put(
                presigned_url, data=file_data, headers=headers, timeout=60
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"S3 파일 업로드 실패: {e}")
            return False

    def delete_s3_object(self, token: str, object_key: str) -> bool:
        """S3에 저장된 객체를 삭제합니다."""
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}/storage/object"
        params = {"object_key": object_key}
        try:
            response = requests.delete(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            logger.info(f"✅ S3 객체 삭제 요청 성공: Key={object_key}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"🔥 S3 객체 삭제 요청 실패: Key={object_key}, Error={e}")
            return False

    def get_presigned_url_for_download(self, object_key: str) -> str | None:
        """파일 조회를 위한 Presigned URL을 백엔드로부터 받아옵니다."""
        url = f"{self.base_url}/storage/presigned-url/download"
        params = {"object_key": object_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json().get("url")
        except requests.exceptions.RequestException as e:
            print(f"다운로드용 Presigned URL 요청 실패: {e}")
            return None