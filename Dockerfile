# streamlit_admin/Dockerfile

FROM python:3.13-slim

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 먼저 복사 및 패키지 설치 (빌드 캐시 효율성 증대)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 코드 전체 복사
# .dockerignore 파일에 의해 불필요한 파일은 제외됩니다.
COPY . .

# Streamlit 기본 포트인 8501 노출
EXPOSE 8501

# 컨테이너 실행 시 Streamlit 앱 실행
# --server.enableCORS=false 옵션은 개발 환경에서 CORS 문제를 방지하는 데 도움이 될 수 있습니다.
CMD ["streamlit", "run", "admin_app.py", "--server.port=8501", "--server.address=0.0.0.0"]