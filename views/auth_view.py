# views/auth_view.py
import os
import time

import streamlit as st

from api import ApiClient


def render_login_page(api_client: ApiClient):
    """
    로그인 페이지 UI를 렌더링하고, Placeholder Pattern을 사용해 로그인 시도 시
    폼 중복 표시 버그를 방지합니다.
    """
    st.subheader("관리자 로그인")

    is_dev_mode = os.getenv("APP_ENV", "dev") == "dev"
    if is_dev_mode:
        st.info("ℹ️ 개발 모드: 로그인 정보가 자동으로 채워졌습니다.")

    form_placeholder = st.empty()

    with form_placeholder.container():
        with st.form("login_form"):
            default_email = "admin@example.com" if is_dev_mode else ""
            default_password = "adminpassword" if is_dev_mode else ""

            email = st.text_input("이메일", value=default_email)
            password = st.text_input(
                "비밀번호", type="password", value=default_password
            )
            submitted = st.form_submit_button("로그인")

    if submitted:
        form_placeholder.empty()

        with st.spinner("로그인 중..."):
            token = api_client.login_for_token(email, password)
            if token:
                st.session_state.jwt_token = token
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error(
                    "로그인에 실패했습니다. 이메일, 비밀번호 또는 슈퍼유저 권한을 확인해주세요."
                )
                time.sleep(2)
                st.rerun()


def render_initial_setup_page(api_client: ApiClient):
    """최초 관리자 계정 생성 페이지 UI를 렌더링합니다."""
    st.subheader("초기 관리자 계정 생성")
    st.info("시스템에 관리자 계정이 없습니다. 최초의 슈퍼유저 계정을 생성해주세요.")
    with st.form("setup_form"):
        email = st.text_input("관리자 이메일")
        password = st.text_input("관리자 비밀번호", type="password")
        confirm_password = st.text_input("비밀번호 확인", type="password")
        if st.form_submit_button("계정 생성"):
            if password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
            elif not email or not password:
                st.error("이메일과 비밀번호를 모두 입력해주세요.")
            else:
                result = api_client.create_initial_superuser(email, password)
                if result and "id" in result:
                    st.success(
                        f"관리자 계정 '{result['email']}'이(가) 성공적으로 생성되었습니다."
                    )
                    st.info("이제 로그인 페이지로 이동합니다.")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(
                        f"계정 생성 실패: {result.get('detail', '알 수 없는 오류')}"
                    )