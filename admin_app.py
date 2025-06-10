# admin_app.py

import logging
import streamlit as st
from dotenv import load_dotenv
import os

# 로컬에서 API 클라이언트를 임포트합니다.
from api_client import ApiClient

# .env 파일에서 환경 변수를 로드합니다. (주로 FASTAPI_API_BASE_URL)
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Streamlit UI 렌더링 함수들 ---

def render_initial_setup_page():
    """최초 슈퍼유저 생성 페이지 UI를 렌더링합니다."""
    st.subheader("초기 관리자 계정 생성")
    st.info("관리자 계정이 없습니다. 최초의 슈퍼유저 계정을 생성해주세요.")
    
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
                result = api_client.create_initial_superuser(email, password)
                if result and 'id' in result: # 성공적으로 생성되면 'id'가 포함된 사용자 정보가 옴
                    st.success(f"관리자 계정 '{result['email']}'이(가) 성공적으로 생성되었습니다. 로그인 페이지로 이동합니다.")
                    # 성공 후에는 환경 변수를 비활성화해야 함을 안내
                    st.warning("보안을 위해 관리자 앱의 SECRET_SIGNUP_MODE 환경 변수를 비활성화하고 재배포하세요.")
                    # 로그인 페이지로 리디렉션하기 위해 잠시 대기 후 rerun
                    # (또는 버튼을 누르게 유도)
                else:
                    # API로부터 받은 에러 메시지 표시
                    error_detail = result.get('detail', '알 수 없는 오류가 발생했습니다.')
                    st.error(f"계정 생성 실패: {error_detail}")

def render_login_page():
    """
    로그인 페이지 UI를 렌더링합니다.
    사용자로부터 이메일과 비밀번호를 입력받아 API 서버에 로그인을 요청합니다.
    """
    st.subheader("관리자 로그인")
    api_client = ApiClient()  # API 클라이언트 인스턴스화

    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

        if submitted:
            # API를 통해 JWT 토큰 요청
            token = api_client.login_for_token(email, password)
            if token:
                # 성공 시, 토큰과 로그인 상태를 세션에 저장하고 앱을 새로고침
                st.session_state.jwt_token = token
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("로그인에 실패했습니다. 이메일, 비밀번호 또는 슈퍼유저 권한을 확인해주세요.")

def render_main_admin_page():
    """
    로그인 후 보여줄 메인 관리자 페이지 UI를 렌더링합니다.
    모든 데이터는 API 서버로부터 받아옵니다.
    """
    st.sidebar.success("관리자 모드로 로그인됨")
    if st.sidebar.button("로그아웃"):
        # 세션 상태를 초기화하고 앱을 새로고침하여 로그인 페이지로 이동
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.header("사용자 목록")

    api_client = ApiClient()
    jwt_token = st.session_state.get("jwt_token")

    # 토큰 유효성 확인
    if not jwt_token:
        st.error("인증 토큰이 없습니다. 다시 로그인해주세요.")
        st.session_state.logged_in = False
        st.rerun()
        return

    # API를 통해 전체 사용자 목록 조회
    users = api_client.get_all_users(token=jwt_token)

    if users is None:
        st.error("사용자 목록을 가져오는데 실패했습니다. 슈퍼유저 권한이 없거나 API 서버에 문제가 발생했습니다.")
        return

    # 사용자 목록 UI 렌더링
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("이메일 또는 사용자명으로 검색", "")
    with col2:
        st.write("")
        if st.button("🔄 목록 새로고침", use_container_width=True):
            st.rerun()

    if search_term:
        users = [
            u for u in users
            if (search_term.lower() in (u.get('email') or "").lower()) or \
               (search_term.lower() in (u.get('username') or "").lower())
        ]
    
    if not users:
        st.warning("조회된 사용자가 없습니다.")
    else:
        for user in users:
            # 이제 user는 DB 모델 객체가 아닌 Dictionary 입니다.
            with st.container():
                cols = st.columns([1, 2, 2, 1, 1, 2])
                cols[0].write(f"**ID: {user['id']}**")
                cols[1].write(user.get('email') or "N/A")
                cols[2].write(user.get('username') or "N/A")
                cols[3].write("✅ Active" if user['is_active'] else "❌ Inactive")
                cols[4].write("👑" if user['is_superuser'] else ("👻" if user['is_guest'] else "👤"))
                with cols[5]:
                    sub_cols = st.columns(2)
                    if sub_cols[0].button("수정", key=f"edit_{user['id']}", use_container_width=True):
                        st.session_state.editing_user_id = user['id']
                    if sub_cols[1].button("삭제", key=f"delete_{user['id']}", type="primary", use_container_width=True):
                        st.session_state.deleting_user_id = user['id']
                st.divider()

    # 사용자 수정 폼 렌더링
    if "editing_user_id" in st.session_state and st.session_state.editing_user_id:
        user_to_edit_id = st.session_state.editing_user_id
        user_to_edit = next((u for u in users if u['id'] == user_to_edit_id), None)
        
        if user_to_edit:
            with st.form(key=f"edit_form_{user_to_edit['id']}"):
                st.subheader(f"사용자 정보 수정 (ID: {user_to_edit['id']})")
                new_username = st.text_input("사용자명", value=user_to_edit.get('username') or "")
                new_is_active = st.checkbox("활성 상태", value=user_to_edit['is_active'])
                new_is_superuser = st.checkbox("슈퍼유저 권한", value=user_to_edit['is_superuser'])
                
                if st.form_submit_button("저장"):
                    update_data = {
                        "username": new_username,
                        "is_active": new_is_active,
                        "is_superuser": new_is_superuser
                    }
                    result = api_client.update_user(token=jwt_token, user_id=user_to_edit['id'], update_data=update_data)
                    if result:
                        st.success(f"사용자 ID {user_to_edit['id']} 정보 업데이트 완료.")
                    else:
                        st.error("사용자 정보 업데이트에 실패했습니다.")
                    del st.session_state.editing_user_id
                    st.rerun()

    # 사용자 삭제 확인 폼 렌더링
    if "deleting_user_id" in st.session_state and st.session_state.deleting_user_id:
        user_to_delete_id = st.session_state.deleting_user_id
        st.warning(f"정말로 사용자 ID {user_to_delete_id}을(를) DB와 Firebase에서 영구적으로 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("예, 삭제합니다.", type="primary"):
            result = api_client.delete_user(token=jwt_token, user_id=user_to_delete_id)
            if result:
                st.success(result.get("message", "사용자 삭제 완료."))
            else:
                st.error("사용자 삭제에 실패했습니다.")
            del st.session_state.deleting_user_id
            st.rerun()
        if c2.button("아니요, 취소합니다."):
            del st.session_state.deleting_user_id
            st.rerun()

# --- 메인 애플리케이션 로직 ---

def main():
    st.set_page_config(page_title="멍탐정 관리자", layout="wide")
    st.title("🐶 멍탐정 관리자 페이지 (API Client Mode)")

    # 1. 세션 상태 초기화
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    # 2. 로그인 상태이면, 무조건 메인 페이지 표시
    if st.session_state.logged_in:
        render_main_admin_page()
        return

    # 3. 로그아웃 상태일 때의 로직
    api_client = ApiClient()
    
    # 4. "비밀 가입 모드" 환경 변수 확인 및 상태 변수 설정
    signup_mode_env_value = os.getenv("SECRET_SIGNUP_MODE", False)
    is_signup_mode_enabled = signup_mode_env_value

    # ==========================================================
    # 💡 사이드바에 현재 설정 상태를 명확하게 표시
    # ==========================================================
    with st.sidebar:
        st.header("⚙️ 앱 실행 상태")
        st.write(f"환경 변수 `SECRET_SIGNUP_MODE`: `{signup_mode_env_value or '설정되지 않음'}`")
        
        # is_signup_mode_enabled의 bool 값에 따라 다른 아이콘과 색상으로 표시
        if is_signup_mode_enabled:
            st.success(f"➡️ 가입 모드 활성화됨: `{is_signup_mode_enabled}`")
        else:
            st.error(f"➡️ 가입 모드 비활성화됨: `{is_signup_mode_enabled}`")
        st.caption("가입 모드가 활성화되어야 최초 관리자 생성이 가능합니다.")
    # ==========================================================

    if is_signup_mode_enabled:
        # CASE 1: 비밀 가입 모드가 활성화된 경우
        @st.cache_data(ttl=10)
        def get_superuser_existence_from_api():
            return api_client.check_superuser_exists()

        superuser_exists = get_superuser_existence_from_api()

        if superuser_exists is None:
            # API 호출 실패
            st.error("백엔드 API 서버에 연결할 수 없습니다. 네트워크 설정을 확인해주세요.")
            st.code(f"호출 대상 API 주소: {api_client.base_url}/admin/superuser-exists")
            if st.button("재시도"):
                st.cache_data.clear()
                st.rerun()

        elif superuser_exists is False:
            # API 성공 & 슈퍼유저 없음 -> 가입 페이지
            render_initial_setup_page()
            
        else: # superuser_exists is True
            # API 성공 & 슈퍼유저 있음 -> 로그인 페이지
            st.info("관리자 계정이 이미 존재합니다. 로그인을 진행해주세요.")
            render_login_page()

    else:
        # CASE 2: 비밀 가입 모드가 비활성화된 경우
        # (사이드바에 이미 안내 메시지가 표시됨)
        render_login_page()

if __name__ == "__main__":
    main()