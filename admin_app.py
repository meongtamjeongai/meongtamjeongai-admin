# admin_app.py
import os

import streamlit as st

from api import ApiClient
from views.auth_view import render_initial_setup_page, render_login_page
from views.conversation_view import render_conversation_test_page
from views.persona_view import render_persona_management_page
from views.phishing_view import render_phishing_case_management_page
from views.user_view import render_user_management_page


def render_main_app(api_client: ApiClient, token: str):
    """로그인 성공 후 보여질 메인 애플리케이션 UI를 렌더링합니다."""
    st.sidebar.title("🐶 멍탐정 관리 메뉴")
    st.sidebar.success("관리자 모드로 로그인됨")

    page_options = {
        "사용자 관리": render_user_management_page,
        "페르소나 관리": render_persona_management_page,
        "대화방 관리 및 테스트": render_conversation_test_page,
        "피싱 사례 관리": render_phishing_case_management_page,
    }

    selected_page = st.sidebar.radio("페이지 선택:", list(page_options.keys()))

    if st.sidebar.button("로그아웃"):
        st.cache_data.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # 선택된 페이지 렌더링 함수를 호출합니다.
    page_options[selected_page](api_client, token)


def main():
    """애플리케이션의 메인 진입점입니다."""
    st.set_page_config(page_title="멍탐정 관리자", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    api_client = ApiClient()

    if st.session_state.logged_in and "jwt_token" in st.session_state:
        render_main_app(api_client, st.session_state.jwt_token)
    else:
        st.title("🐶 멍탐정 관리자 페이지")

        @st.cache_data(ttl=10)
        def get_superuser_existence():
            return api_client.check_superuser_exists()

        superuser_exists = get_superuser_existence()

        if not superuser_exists:
            is_signup_mode_enabled = os.getenv("SECRET_SIGNUP_MODE", "true") == "true"
            if is_signup_mode_enabled:
                render_initial_setup_page(api_client)
            else:
                st.error(
                    "🚨 시스템에 관리자 계정이 없지만, 신규 계정 생성 모드가 비활성화되어 있습니다."
                )
                st.warning(
                    "백엔드 배포 환경 변수에서 `SECRET_SIGNUP_MODE`를 `true`로 설정하고 관리자 앱을 재배포해주세요."
                )
        else:
            render_login_page(api_client)


if __name__ == "__main__":
    main()