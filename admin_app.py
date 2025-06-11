# streamlit_admin/admin_app.py

import streamlit as st
import json
import os
import time
from api_client import ApiClient

# ===================================================================
# Helper Functions
# ===================================================================

def display_api_result(result_data):
    """API 응답 결과를 st.json 또는 st.text로 예쁘게 표시하는 함수"""
    if result_data is None:
        st.info("API 호출 결과가 없습니다 (None 반환).")
        return

    if isinstance(result_data, (dict, list)):
        try:
            # JSON 뷰어로 예쁘게 표시
            st.json(result_data)
        except Exception:
            # JSON 변환 실패 시 텍스트로 표시
            st.text(str(result_data))
    else:
        st.text(str(result_data))

def section_title(title):
    """페이지 내 섹션 제목을 위한 헬퍼 함수"""
    st.markdown(f"### {title}")
    st.divider()

# ===================================================================
# Page Rendering Functions
# ===================================================================

def render_user_management_page(api_client, token):
    st.header("사용자 관리")
    
    users = api_client.get_all_users(token=token)
    if users is None:
        st.error("사용자 목록을 가져오는데 실패했습니다. 슈퍼유저 권한을 확인해주세요.")
        return

    if not users:
        st.warning("조회된 사용자가 없습니다.")
    else:
        st.write(f"총 {len(users)}명의 사용자가 조회되었습니다.")
        for user in users:
            with st.container(border=True):
                cols = st.columns([1, 3, 3, 2, 1])
                cols[0].write(f"**ID: {user['id']}**")
                cols[1].write(f"📧 {user.get('email') or 'N/A'}")
                cols[2].write(f"👤 {user.get('username') or 'N/A'}")
                cols[3].write("✅ Active" if user['is_active'] else "❌ Inactive")
                cols[4].write("👑" if user['is_superuser'] else ("👻" if user['is_guest'] else "👤"))
    
    # 수정/삭제 기능은 추후 확장 가능

def render_persona_management_page(api_client, token):
    st.header("페르소나 관리")

    # --- 페르소나 목록 조회 ---
    section_title("페르소나 목록 조회")
    if st.button("모든 페르소나 조회하기"):
        with st.spinner("페르소나 목록을 불러오는 중..."):
            personas = api_client.get_personas(token)
            display_api_result(personas)

    # --- 새 페르소나 생성 ---
    section_title("새 페르소나 생성")
    with st.form("create_persona_form"):
        st.write("AI에게 부여할 새로운 역할을 정의합니다.")
        name = st.text_input("이름*", placeholder="예: 고양이 집사 츄르")
        system_prompt = st.text_area("시스템 프롬프트*", height=150, placeholder="예: 너는 고양이를 매우 사랑하는 고양이 집사야. 모든 대답을 고양이처럼 '냥~'으로 끝내야 해.")
        description = st.text_input("설명", placeholder="예: 세상의 모든 고양이를 사랑하는 츄르")
        
        submitted = st.form_submit_button("페르소나 생성")
        if submitted:
            if name and system_prompt:
                with st.spinner("새 페르소나를 생성하는 중..."):
                    new_persona = api_client.create_persona(token, name, system_prompt, description)
                    if new_persona:
                        st.success("페르소나가 성공적으로 생성되었습니다!")
                        display_api_result(new_persona)
                    else:
                        st.error("페르소나 생성에 실패했습니다.")
            else:
                st.warning("이름과 시스템 프롬프트는 필수 입력 항목입니다.")

def render_gemini_test_page(api_client, token):
    st.header("🤖 Gemini 연동 테스트")
    st.info("이 페이지에서 페르소나와 대화하며 실제 Gemini API 응답을 확인할 수 있습니다.")

    # --- 1. 테스트용 대화방 생성 ---
    section_title("1. 테스트용 대화방 생성")
    with st.form("create_conversation_form"):
        persona_id = st.number_input("대화할 페르소나 ID*", min_value=1, step=1, help="페르소나 관리 페이지에서 생성한 페르소나의 ID를 입력하세요.")
        title = st.text_input("대화방 제목 (선택 사항)")
        
        submitted_conv = st.form_submit_button("대화방 생성")
        if submitted_conv:
            with st.spinner(f"페르소나 ID {int(persona_id)}와 대화방을 생성하는 중..."):
                new_conv = api_client.create_conversation(token, int(persona_id), title)
                if new_conv:
                    st.success("대화방이 성공적으로 생성되었습니다!")
                    display_api_result(new_conv)
                    st.info(f"생성된 대화방 ID: **{new_conv['id']}**. 아래 메시지 전송에 이 ID를 사용하세요.")
                else:
                    st.error("대화방 생성에 실패했습니다.")

    # --- 2. 메시지 전송 및 AI 응답 확인 ---
    section_title("2. 메시지 전송 및 AI 응답 확인")
    with st.form("send_message_form"):
        conversation_id = st.number_input("메시지를 보낼 대화방 ID*", min_value=1, step=1)
        content = st.text_input("보낼 메시지 내용*", placeholder="예: 안녕? 넌 누구야?")
        
        submitted_msg = st.form_submit_button("메시지 전송 및 AI 응답 받기")
        if submitted_msg:
            if conversation_id and content:
                with st.spinner("AI가 답변을 생성하는 중... (최대 30초 소요)"):
                    response_messages = api_client.send_message(token, int(conversation_id), content)
                    if response_messages:
                        st.success("AI 응답을 성공적으로 받았습니다!")
                        display_api_result(response_messages)
                    else:
                        st.error("메시지 전송 또는 AI 응답 수신에 실패했습니다.")
            else:
                st.warning("대화방 ID와 메시지 내용은 필수 입력 항목입니다.")

def render_login_page():
    st.subheader("관리자 로그인")
    api_client = ApiClient()
    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")
        if submitted:
            with st.spinner("로그인 중..."):
                token = api_client.login_for_token(email, password)
                if token:
                    st.session_state.jwt_token = token
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("로그인에 실패했습니다. 이메일, 비밀번호 또는 슈퍼유저 권한을 확인해주세요.")

def render_initial_setup_page():
    st.subheader("초기 관리자 계정 생성")
    st.info("시스템에 관리자 계정이 없습니다. 최초의 슈퍼유저 계정을 생성해주세요.")
    api_client = ApiClient()
    with st.form("setup_form"):
        email = st.text_input("관리자 이메일")
        password = st.text_input("관리자 비밀번호", type="password")
        confirm_password = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("계정 생성")
        if submitted:
            if password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
            elif not email or not password:
                st.error("이메일과 비밀번호를 모두 입력해주세요.")
            else:
                with st.spinner("최초 관리자 계정을 생성하는 중..."):
                    result = api_client.create_initial_superuser(email, password)
                    if result and 'id' in result:
                        st.success(f"관리자 계정 '{result['email']}'이(가) 성공적으로 생성되었습니다.")
                        st.info("이제 로그인 페이지로 이동합니다.")
                        st.warning("보안을 위해 관리자 앱의 SECRET_SIGNUP_MODE 환경 변수를 비활성화하고 재배포하는 것을 권장합니다.")
                        time.sleep(3)
                        st.rerun()
                    else:
                        error_detail = result.get('detail', '알 수 없는 오류가 발생했습니다.')
                        st.error(f"계정 생성 실패: {error_detail}")

# ===================================================================
# Main Application Logic
# ===================================================================
def main():
    st.set_page_config(page_title="멍탐정 관리자", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        st.sidebar.title("🐶 멍탐정 관리 메뉴")
        st.sidebar.success("관리자 모드로 로그인됨")
        page_options = {
            "사용자 관리": render_user_management_page,
            "페르소나 관리": render_persona_management_page,
            "Gemini 연동 테스트": render_gemini_test_page,
        }
        selected_page = st.sidebar.radio("이동할 페이지 선택:", list(page_options.keys()), key="page_selector")
        st.sidebar.divider()
        if st.sidebar.button("로그아웃"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        api_client = ApiClient()
        jwt_token = st.session_state.get("jwt_token")
        if jwt_token:
            render_function = page_options[selected_page]
            render_function(api_client, jwt_token)
        else:
            st.error("인증 세션이 만료되었습니다. 다시 로그인해주세요.")
            st.session_state.logged_in = False
            st.rerun()
    else:
        st.title("🐶 멍탐정 관리자 페이지")
        api_client = ApiClient()
        is_signup_mode_enabled = os.getenv("SECRET_SIGNUP_MODE") == "true"

        if is_signup_mode_enabled:
            @st.cache_data(ttl=10) # 10초간 캐시
            def get_superuser_existence():
                return api_client.check_superuser_exists()

            if not get_superuser_existence():
                render_initial_setup_page()
            else:
                render_login_page()
        else:
            render_login_page()

if __name__ == "__main__":
    main()