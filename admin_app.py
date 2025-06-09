# streamlit_admin/admin_app.py

import logging
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Firebase Admin SDK 및 비밀번호 해싱 라이브러리 임포트
import firebase_admin
import streamlit as st

# 모델 임포트
from db_models.user import User
from db_models.user_point import UserPoint
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from passlib.context import CryptContext
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, joinedload, sessionmaker

# .env 파일에서 환경 변수 로드
# 이 코드는 os.getenv를 호출하기 전에 실행되어야 합니다.
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- 보안 설정 ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Firebase Admin SDK 초기화 ---
try:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./serviceAccountKey.json")
    if cred_path and os.path.exists(cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logging.info("✅ Firebase Admin SDK initialized successfully.")
    else:
        logging.warning("⚠️ Firebase service account key not found.")
except Exception as e:
    logging.error(f"❌ Error initializing Firebase Admin SDK: {e}")

# --- 데이터베이스 연결 설정 ---
DB_USER = os.getenv("POSTGRES_USER", "dev_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dev_password")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "dev_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    st.error(f"데이터베이스 엔진 생성에 실패했습니다: {e}")
    st.stop()


@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 인증 및 CRUD 함수들 ---


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def check_if_superuser_exists(db: Session) -> bool:
    """DB에 슈퍼유저가 한 명이라도 있는지 확인합니다."""
    return db.query(User).filter(User.is_superuser == True).first() is not None


def create_initial_superuser(db: Session, email: str, password: str):
    """최초 슈퍼유저를 생성합니다."""
    hashed_password = get_password_hash(password)
    # UserPoint도 함께 생성
    new_user = User(
        email=email, hashed_password=hashed_password, is_active=True, is_superuser=True
    )
    db.add(new_user)
    db.commit()

    new_user_point = UserPoint(
        user_id=new_user.id, points=99999
    )  # 관리자에게 넉넉한 포인트
    db.add(new_user_point)
    db.commit()

    db.refresh(new_user)
    return new_user


def authenticate_superuser(db: Session, email: str, password: str) -> User | None:
    """이메일과 비밀번호로 슈퍼유저를 인증합니다."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not user.is_superuser:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# (기존 CRUD 함수들은 그대로 유지)
def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(User)
        .options(joinedload(User.social_accounts))
        .order_by(desc(User.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_user_by_id(db: Session, user_id: int):
    return (
        db.query(User)
        .options(joinedload(User.social_accounts))
        .filter(User.id == user_id)
        .first()
    )


def update_user_info(
    db: Session, user_id: int, username: str, is_active: bool, is_superuser: bool
):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.username = username
        user.is_active = is_active
        user.is_superuser = is_superuser
        db.commit()
        db.refresh(user)
        return user
    return None


def delete_user_and_firebase_account(db: Session, user_id: int):
    user_to_delete = get_user_by_id(db, user_id)
    if not user_to_delete:
        st.error(f"User with ID {user_id} not found in DB.")
        return
    if firebase_admin._apps:
        firebase_uids = [
            sa.provider_user_id
            for sa in user_to_delete.social_accounts
            if sa.provider.value.startswith("firebase_")
        ]
        for uid in firebase_uids:
            try:
                firebase_auth.delete_user(uid)
                st.toast(f"✅ Deleted Firebase user: {uid}", icon="🔥")
            except firebase_auth.UserNotFoundError:
                st.toast(f"⚠️ Firebase user not found: {uid}", icon="🤷")
            except Exception as e:
                st.error(f"❌ Failed to delete Firebase user {uid}: {e}")
                return
    db.delete(user_to_delete)
    db.commit()
    st.toast(f"✅ Deleted user {user_id} from DB.", icon="🗑️")


# --- Streamlit UI 렌더링 함수들 ---


def render_login_page():
    """로그인 페이지 UI를 렌더링합니다."""
    st.subheader("관리자 로그인")
    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")
        if submitted:
            with get_db_session() as db:
                user = authenticate_superuser(db, email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user.email
                    st.rerun()
                else:
                    st.error(
                        "이메일 또는 비밀번호가 잘못되었거나, 슈퍼유저가 아닙니다."
                    )


def render_initial_setup_page():
    """최초 슈퍼유저 생성 페이지 UI를 렌더링합니다."""
    st.subheader("초기 관리자 계정 생성")
    st.info("관리자 계정이 없습니다. 최초의 슈퍼유저 계정을 생성해주세요.")
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
                with get_db_session() as db:
                    create_initial_superuser(db, email, password)
                    st.success(
                        "관리자 계정이 성공적으로 생성되었습니다. 다시 로그인해주세요."
                    )
                    st.rerun()


def render_main_admin_page():
    """메인 관리자 페이지 UI를 렌더링합니다."""
    st.sidebar.success(f"{st.session_state.user_email} 님으로 로그인됨")
    if st.sidebar.button("로그아웃"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.header("사용자 목록")
    # (기존 관리자 페이지 코드는 여기에 위치)
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("이메일 또는 사용자명으로 검색", "")
    with col2:
        st.write("")
        if st.button("🔄 목록 새로고침", use_container_width=True):
            st.rerun()

    try:
        with get_db_session() as db:
            users = get_all_users(db)
            if search_term:
                users = [
                    u
                    for u in users
                    if (search_term.lower() in (u.email or "").lower())
                    or (search_term.lower() in (u.username or "").lower())
                ]

            if not users:
                st.warning("조회된 사용자가 없습니다.")
            else:
                for user in users:
                    with st.container():
                        cols = st.columns([1, 2, 2, 1, 1, 2])
                        cols[0].write(f"**ID: {user.id}**")
                        cols[1].write(user.email or "N/A")
                        cols[2].write(user.username or "N/A")
                        cols[3].write("✅ Active" if user.is_active else "❌ Inactive")
                        cols[4].write(
                            "👑"
                            if user.is_superuser
                            else ("👻" if user.is_guest else "👤")
                        )
                        with cols[5]:
                            sub_cols = st.columns(2)
                            if sub_cols[0].button(
                                "수정", key=f"edit_{user.id}", use_container_width=True
                            ):
                                st.session_state.editing_user_id = user.id
                            if sub_cols[1].button(
                                "삭제",
                                key=f"delete_{user.id}",
                                type="primary",
                                use_container_width=True,
                            ):
                                st.session_state.deleting_user_id = user.id
                        st.divider()

            if (
                "editing_user_id" in st.session_state
                and st.session_state.editing_user_id
            ):
                user_to_edit = get_user_by_id(db, st.session_state.editing_user_id)
                if user_to_edit:
                    with st.form(key=f"edit_form_{user_to_edit.id}"):
                        st.subheader(f"사용자 정보 수정 (ID: {user_to_edit.id})")
                        new_username = st.text_input(
                            "사용자명", value=user_to_edit.username or ""
                        )
                        new_is_active = st.checkbox(
                            "활성 상태", value=user_to_edit.is_active
                        )
                        new_is_superuser = st.checkbox(
                            "슈퍼유저 권한", value=user_to_edit.is_superuser
                        )
                        if st.form_submit_button("저장"):
                            update_user_info(
                                db,
                                user_to_edit.id,
                                new_username,
                                new_is_active,
                                new_is_superuser,
                            )
                            st.success(
                                f"사용자 ID {user_to_edit.id} 정보 업데이트 완료."
                            )
                            del st.session_state.editing_user_id
                            st.rerun()

            if (
                "deleting_user_id" in st.session_state
                and st.session_state.deleting_user_id
            ):
                user_to_delete_id = st.session_state.deleting_user_id
                st.warning(
                    f"정말로 사용자 ID {user_to_delete_id}을(를) 삭제하시겠습니까?"
                )
                c1, c2, c3 = st.columns([1, 1, 4])
                if c1.button("예, 삭제합니다.", type="primary"):
                    delete_user_and_firebase_account(db, user_to_delete_id)
                    del st.session_state.deleting_user_id
                    st.rerun()
                if c2.button("아니요, 취소합니다."):
                    del st.session_state.deleting_user_id
                    st.rerun()
    except Exception as e:
        st.error(f"DB 조회 중 오류: {e}")


# --- 메인 애플리케이션 로직 ---


def main():
    st.set_page_config(page_title="멍탐정 관리자", layout="wide")
    st.title("🐶 멍탐정 관리자 페이지")

    # 세션 상태에 'logged_in'이 없으면 False로 초기화
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        # 로그인 상태이면 메인 관리자 페이지 렌더링
        render_main_admin_page()
    else:
        # 로그아웃 상태이면 DB에 슈퍼유저가 있는지 확인
        try:
            with get_db_session() as db:
                superuser_exists = check_if_superuser_exists(db)
        except Exception as e:
            st.error(f"데이터베이스 연결에 실패했습니다: {e}")
            st.code(f"사용한 DB URL: {DATABASE_URL}")
            return

        if superuser_exists:
            # 슈퍼유저가 있으면 로그인 페이지 렌더링
            render_login_page()
        else:
            # 슈퍼유저가 없으면 초기 설정 페이지 렌더링
            render_initial_setup_page()


if __name__ == "__main__":
    main()
