# views/user_view.py
import math
import time

import pandas as pd
import streamlit as st

from api import ApiClient
from utils import section_title


def render_user_management_page(api_client: ApiClient, token: str):
    """
    사용자 관리 페이지 UI를 렌더링합니다.
    (프로필 이미지 CRUD 기능 추가)
    """
    st.header("사용자 관리")

    # --- 데이터 로드 및 캐싱 ---
    @st.cache_data(ttl=60)
    def get_users_data():
        return api_client.get_all_users(token=token)

    # --- 콜백 및 상태 초기화 함수 ---
    def handle_file_upload():
        if st.session_state.get("user_file_uploader_key"):
            st.session_state.user_uploaded_file = (
                st.session_state.user_file_uploader_key
            )
        else:
            st.session_state.user_uploaded_file = None

    def reset_user_form_states():
        keys_to_delete = [
            "user_uploaded_file",
            "user_file_uploader_key",
            "user_delete_image_checked",
            "current_selected_user_id",
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]

    all_users = get_users_data()
    if all_users is None:
        st.error("사용자 목록을 가져오는데 실패했습니다.")
        if st.button("다시 시도"):
            st.cache_data.clear()
            st.rerun()
        return

    # --- 세션 상태 초기화 ---
    if "users_page_num" not in st.session_state:
        st.session_state.users_page_num = 1
    if "users_search_query" not in st.session_state:
        st.session_state.users_search_query = ""
    if "users_per_page" not in st.session_state:
        st.session_state.users_per_page = 10

    # --- UI 컨트롤 (검색, 새로고침 등) ---
    c1, c2, c3 = st.columns([5, 1, 2], vertical_alignment="bottom")
    with c1:
        search_query = st.text_input(
            "사용자 검색 (이메일 또는 사용자명)",
            value=st.session_state.users_search_query,
            key="user_search_input",
            label_visibility="collapsed",
            placeholder="사용자 검색 (이메일 또는 사용자명)",
        )
        if search_query != st.session_state.users_search_query:
            st.session_state.users_search_query = search_query
            st.session_state.users_page_num = 1
            st.rerun()
    with c2:
        if st.button("새로고침", use_container_width=True):
            st.cache_data.clear()
            reset_user_form_states()
            st.rerun()
    with c3:
        items_per_page = st.selectbox(
            "페이지 당 항목 수",
            options=[10, 25, 50, 100],
            index=[10, 25, 50, 100].index(st.session_state.users_per_page),
            key="user_items_per_page_selector",
            label_visibility="collapsed",
        )
        if items_per_page != st.session_state.users_per_page:
            st.session_state.users_per_page = items_per_page
            st.session_state.users_page_num = 1
            st.rerun()

    # --- 데이터 필터링 및 페이지네이션 ---
    df = pd.DataFrame(all_users)
    if search_query:
        mask = df["email"].str.contains(search_query, case=False, na=False) | df[
            "username"
        ].str.contains(search_query, case=False, na=False)
        filtered_df = df[mask]
    else:
        filtered_df = df

    total_items = len(filtered_df)
    total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
    st.session_state.users_page_num = max(
        1, min(st.session_state.users_page_num, total_pages)
    )
    start_idx = (st.session_state.users_page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]

    # --- 데이터프레임 표시 ---
    st.write(
        f"총 {total_items}명의 사용자가 조회되었습니다. (페이지: {st.session_state.users_page_num}/{total_pages})"
    )
    display_df = paginated_df[
        ["id", "email", "username", "is_active", "is_superuser"]
    ].copy()
    display_df.rename(
        columns={
            "id": "ID",
            "email": "이메일",
            "username": "사용자명",
            "is_active": "활성",
            "is_superuser": "관리자",
        },
        inplace=True,
    )
    display_df["활성"] = display_df["활성"].apply(lambda x: "✅" if x else "❌")
    display_df["관리자"] = display_df["관리자"].apply(lambda x: "👑" if x else "👤")
    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- 페이지네이션 컨트롤 ---
    p_c1, p_c2, p_c3 = st.columns([1, 8, 1])
    with p_c1:
        if st.button("이전", disabled=(st.session_state.users_page_num <= 1)):
            st.session_state.users_page_num -= 1
            st.rerun()
    with p_c3:
        if st.button("다음", disabled=(st.session_state.users_page_num >= total_pages)):
            st.session_state.users_page_num += 1
            st.rerun()

    st.divider()

    # --- 선택된 행에 대한 작업 (수정/삭제) ---
    if selection.selection.rows:
        selected_row_index = selection.selection.rows[0]
        selected_user_id = paginated_df.iloc[selected_row_index]["id"]
        user = next((u for u in all_users if u["id"] == selected_user_id), None)

        if user:
            # [추가] 다른 사용자를 선택하면 이미지 관련 상태 초기화
            if st.session_state.get("current_selected_user_id") != selected_user_id:
                reset_user_form_states()
                st.session_state.current_selected_user_id = selected_user_id

            section_title(f"사용자 작업 (ID: {user['id']}, 이메일: {user['email']})")
            action_c1, action_c2 = st.columns(2)

            with action_c1:
                with st.expander("사용자 정보 수정", expanded=True):
                    img_c1, img_c2 = st.columns(2)
                    with img_c1:
                        st.markdown("**현재 프로필 이미지**")
                        current_image_key = user.get("profile_image_key")
                        if current_image_key:

                            @st.cache_data(ttl=300)
                            def get_cached_user_image_url(key):
                                return api_client.get_presigned_url_for_download(
                                    token=token, object_key=key
                                )

                            with st.spinner("이미지 로딩 중..."):
                                download_url = get_cached_user_image_url(
                                    current_image_key
                                )

                            if download_url:
                                st.image(
                                    download_url,
                                    caption="현재 이미지",
                                    use_container_width=True,
                                )
                            else:
                                st.error("이미지를 불러올 수 없습니다.")
                        else:
                            st.info("등록된 이미지가 없습니다.")
                    with img_c2:
                        st.markdown("**새 프로필 이미지**")
                        st.file_uploader(
                            "이미지 변경",
                            type=["png", "jpg", "jpeg", "webp"],
                            key="user_file_uploader_key",
                            on_change=handle_file_upload,
                        )
                        if st.session_state.get("user_uploaded_file"):
                            st.image(
                                st.session_state.user_uploaded_file,
                                caption="새로 업로드할 이미지",
                                use_container_width=True,
                            )
                        st.checkbox(
                            "이미지 삭제",
                            key="user_delete_image_checked",
                            value=st.session_state.get(
                                "user_delete_image_checked", False
                            ),
                        )
                    st.divider()

                    # 사용자 정보 수정 폼
                    with st.form(key=f"update_form_user_{user['id']}"):
                        new_username = st.text_input(
                            "사용자 이름", value=user.get("username", "")
                        )
                        new_is_active = st.checkbox(
                            "활성 상태", value=user["is_active"]
                        )
                        new_is_superuser = st.checkbox(
                            "슈퍼유저 권한", value=user["is_superuser"]
                        )

                        if st.form_submit_button("저장"):
                            # [수정] 이미지 처리 로직 추가
                            final_image_key = user.get("profile_image_key")
                            previous_image_key = final_image_key
                            should_delete_previous_image = False

                            with st.spinner("이미지 처리 중..."):
                                if st.session_state.get(
                                    "user_delete_image_checked", False
                                ):
                                    final_image_key = None
                                    st.toast("🗑️ 이미지가 삭제되도록 설정되었습니다.")
                                    if previous_image_key:
                                        should_delete_previous_image = True
                                elif (
                                    st.session_state.get("user_uploaded_file")
                                    is not None
                                ):
                                    file = st.session_state.user_uploaded_file
                                    presigned_data = (
                                        api_client.get_presigned_url_for_upload(
                                            token=token,
                                            filename=file.name,
                                            category="users",
                                        )
                                    )
                                    if presigned_data:
                                        upload_ok = api_client.upload_file_to_s3(
                                            presigned_data["url"],
                                            file.getvalue(),
                                            file.type,
                                        )
                                        if upload_ok:
                                            final_image_key = presigned_data[
                                                "object_key"
                                            ]
                                            st.toast(
                                                "✅ 이미지가 성공적으로 업로드되었습니다."
                                            )
                                            if previous_image_key:
                                                should_delete_previous_image = True
                                        else:
                                            st.error("S3에 이미지 업로드 실패.")
                                    else:
                                        st.error("업로드 URL 생성 실패.")

                            update_data = {
                                "username": new_username,
                                "is_active": new_is_active,
                                "is_superuser": new_is_superuser,
                                "profile_image_key": final_image_key,
                            }

                            with st.spinner("사용자 정보 저장 중..."):
                                if api_client.update_user(
                                    token, user["id"], update_data
                                ):
                                    if should_delete_previous_image:
                                        with st.spinner("이전 이미지 정리 중..."):
                                            api_client.delete_s3_object(
                                                token, previous_image_key
                                            )
                                            st.toast("🗑️ 이전 이미지가 삭제되었습니다.")

                                    st.success("사용자 정보가 업데이트되었습니다.")
                                    st.cache_data.clear()
                                    reset_user_form_states()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("업데이트에 실패했습니다.")

            with action_c2:
                with st.expander("사용자 삭제", expanded=False):
                    st.warning(
                        "**정말로 이 사용자를 삭제하시겠습니까?** 이 작업은 되돌릴 수 없습니다."
                    )
                    if st.button(
                        "예, 삭제합니다",
                        key=f"confirm_delete_{user['id']}",
                        type="primary",
                    ):
                        # [수정] S3 이미지 먼저 삭제
                        image_key_to_delete = user.get("profile_image_key")
                        if image_key_to_delete:
                            with st.spinner("연결된 프로필 이미지 삭제 중..."):
                                delete_img_ok = api_client.delete_s3_object(
                                    token, image_key_to_delete
                                )
                                if not delete_img_ok:
                                    st.error(
                                        "S3 이미지 삭제에 실패했습니다. 사용자 삭제를 중단합니다."
                                    )
                                    st.stop()
                                st.toast("🗑️ 연결된 이미지가 S3에서 삭제되었습니다.")

                        # 사용자 삭제 API 호출
                        if api_client.delete_user(token, user["id"]):
                            st.success("사용자가 삭제되었습니다.")
                            st.cache_data.clear()
                            reset_user_form_states()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("삭제에 실패했습니다.")
