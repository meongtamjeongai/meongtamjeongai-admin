# views/persona_view.py
import time

import streamlit as st

from api import ApiClient
from utils import section_title


def render_persona_management_page(api_client: ApiClient, token: str):
    """
    페르소나 관리 페이지 UI를 렌더링합니다.
    (ID 정렬 기능이 추가된 최종 안정화 버전)
    """
    st.header("페르소나 관리")

    # --- 데이터 로드 및 캐싱 ---
    @st.cache_data(ttl=60)
    def get_personas_data():
        """API를 통해 페르소나 목록을 가져와 캐싱합니다."""
        return api_client.get_personas(token)

    # --- 콜백 함수 정의 ---
    def handle_file_upload():
        """파일 업로더의 상태가 변경될 때 호출되어 세션 상태를 업데이트합니다."""
        if st.session_state.get("file_uploader_key"):
            st.session_state.uploaded_file = st.session_state.file_uploader_key
        else:
            st.session_state.uploaded_file = None

    # --- 상태 초기화 함수 정의 ---
    def reset_form_states():
        """
        수정/생성 폼과 관련된 모든 세션 상태를 초기화(삭제)합니다.
        """
        keys_to_delete = [
            "editing_persona_id",
            "uploaded_file",
            "file_uploader_key",
            "delete_image_checked",
            "init_edit_mode",
            "init_create_mode",
            "persona_view_mode",
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]

    # --- 1. 수정/삭제 뷰 렌더링 ---
    if (
        "editing_persona_id" in st.session_state
        and st.session_state.editing_persona_id is not None
    ):
        # (수정 뷰 로직은 변경 없음)
        if (
            "init_edit_mode" not in st.session_state
            or st.session_state.init_edit_mode != st.session_state.editing_persona_id
        ):
            if "uploaded_file" in st.session_state:
                del st.session_state.uploaded_file
            if "delete_image_checked" in st.session_state:
                del st.session_state.delete_image_checked
            st.session_state.init_edit_mode = st.session_state.editing_persona_id

        all_personas = get_personas_data()
        persona_to_edit = next(
            (p for p in all_personas if p["id"] == st.session_state.editing_persona_id),
            None,
        )

        if persona_to_edit is None:
            st.error("수정할 페르소나를 찾을 수 없습니다. 목록으로 돌아갑니다.")
            reset_form_states()
            st.rerun()
            return

        section_title(f"페르소나 관리 (ID: {persona_to_edit['id']})")

        img_c1, img_c2 = st.columns(2)
        with img_c1:
            st.markdown("**현재 이미지**")
            current_image_key = persona_to_edit.get("profile_image_key")
            if current_image_key:
                with st.spinner("이미지 로딩 중..."):
                    download_url = api_client.get_presigned_url_for_download(
                        token,current_image_key
                    )
                if download_url:
                    st.image(
                        download_url,
                        caption="현재 저장된 이미지",
                        use_container_width=True,
                    )
                else:
                    st.error("이미지를 불러올 수 없습니다.")
            else:
                st.info("등록된 프로필 이미지가 없습니다.")

        with img_c2:
            st.markdown("**새 이미지**")
            st.file_uploader(
                "이미지 변경",
                type=["png", "jpg", "jpeg", "webp"],
                key="file_uploader_key",
                on_change=handle_file_upload,
            )
            if st.session_state.get("uploaded_file"):
                st.image(
                    st.session_state.uploaded_file,
                    caption="새로 업로드할 이미지 (미리보기)",
                    use_container_width=True,
                )

            st.checkbox(
                "이미지 삭제",
                key="delete_image_checked",
                value=st.session_state.get("delete_image_checked", False),
                help="체크하고 저장하면 현재 이미지가 삭제됩니다.",
            )

        st.divider()

        with st.form(key=f"update_form_persona_{persona_to_edit['id']}"):
            name = st.text_input("이름", value=persona_to_edit["name"])
            desc = st.text_input("설명", value=persona_to_edit.get("description", ""))
            prompt = st.text_area(
                "시스템 프롬프트", value=persona_to_edit["system_prompt"], height=200
            )
            is_public = st.checkbox("공개", value=persona_to_edit["is_public"])

            btn_c1, btn_c2 = st.columns(2)
            if btn_c1.form_submit_button(
                "저장하기", use_container_width=True, type="primary"
            ):
                final_image_key = persona_to_edit.get("profile_image_key")
                previous_image_key = final_image_key
                should_delete_previous_image = False

                if st.session_state.get("delete_image_checked", False):
                    final_image_key = None
                    st.toast("🗑️ 이미지가 삭제되도록 설정되었습니다.")
                    if previous_image_key:
                        should_delete_previous_image = True
                elif st.session_state.get("uploaded_file") is not None:
                    file_to_upload = st.session_state.uploaded_file
                    with st.spinner("이미지 업로드 중..."):
                        presigned_data = api_client.get_presigned_url_for_upload(
                            token=token,
                            filename=file_to_upload.name,
                            category="personas",
                        )
                        if presigned_data:
                            upload_success = api_client.upload_file_to_s3(
                                presigned_url=presigned_data["url"],
                                file_data=file_to_upload.getvalue(),
                                content_type=file_to_upload.type,
                            )
                            if upload_success:
                                final_image_key = presigned_data["object_key"]
                                st.toast("✅ 이미지가 성공적으로 업로드되었습니다.")
                                if previous_image_key:
                                    should_delete_previous_image = True
                            else:
                                st.error("S3에 이미지를 업로드하는 데 실패했습니다.")
                        else:
                            st.error("이미지 업로드 URL을 받아오는 데 실패했습니다.")

                update_data = {
                    "name": name,
                    "description": desc,
                    "system_prompt": prompt,
                    "is_public": is_public,
                    "profile_image_key": final_image_key,
                }

                with st.spinner("페르소나 정보 저장 중..."):
                    if api_client.update_persona(
                        token, persona_to_edit["id"], update_data
                    ):
                        if should_delete_previous_image:
                            with st.spinner("이전 이미지 정리 중..."):
                                api_client.delete_s3_object(token, previous_image_key)
                                st.toast(
                                    f"🗑️ 이전 이미지({previous_image_key[:15]}...)가 삭제되었습니다."
                                )

                        st.success("페르소나 정보가 성공적으로 업데이트되었습니다.")
                        st.cache_data.clear()
                        reset_form_states()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("페르소나 정보 업데이트에 실패했습니다.")

            if btn_c2.form_submit_button("취소", use_container_width=True):
                reset_form_states()
                st.rerun()

        with st.expander("페르소나 삭제하기", expanded=False):
            if st.button(
                f"ID {persona_to_edit['id']} ({persona_to_edit['name']}) 영구 삭제",
                type="primary",
                use_container_width=True,
            ):
                image_key_to_delete = persona_to_edit.get("profile_image_key")
                if image_key_to_delete:
                    with st.spinner(
                        f"연결된 이미지({image_key_to_delete[:15]}...) 삭제 중..."
                    ):
                        delete_success = api_client.delete_s3_object(
                            token, image_key_to_delete
                        )
                        if not delete_success:
                            st.error(
                                "S3 이미지 삭제에 실패했습니다. 페르소나 삭제를 중단합니다."
                            )
                            st.stop()
                        st.toast("🗑️ 연결된 이미지가 S3에서 삭제되었습니다.")

                if api_client.delete_persona(token, persona_to_edit["id"]):
                    st.success("페르소나가 성공적으로 삭제되었습니다.")
                    st.cache_data.clear()
                    reset_form_states()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("삭제에 실패했습니다.")
        return

    # --- 2. 목록 및 생성 뷰 렌더링 ---

    if "persona_view_mode" not in st.session_state:
        st.session_state.persona_view_mode = "페르소나 목록"

    st.radio(
        "보기 모드",
        ["페르소나 목록", "새 페르소나 생성"],
        key="persona_view_mode",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    if st.session_state.persona_view_mode == "페르소나 목록":
        if st.button("페르소나 목록 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        personas = get_personas_data()
        if personas is None:
            st.error("페르소나 목록을 가져오는 데 실패했습니다.")
            return

        # ⭐️ [수정] ID를 기준으로 페르소나 목록을 오름차순으로 정렬합니다.
        personas = sorted(personas, key=lambda p: p["id"])

        st.write(f"총 {len(personas)}개의 페르소나가 조회되었습니다.")
        st.divider()

        for p in personas:
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                with c1:
                    image_key = p.get("profile_image_key")
                    if image_key:

                        @st.cache_data(ttl=3600)
                        def get_cached_download_url(key, auth_token): # 1. auth_token 인자 추가
                            # 2. token과 object_key를 명시적으로 전달
                            return api_client.get_presigned_url_for_download(token=auth_token, object_key=key)

                        # 3. 함수 호출 시 token 전달
                        img_url = get_cached_download_url(image_key, token)
                        if img_url:
                            st.image(img_url, width=150)
                        else:
                            st.caption("이미지 로드 실패")
                    else:
                        st.image("https://placehold.co/150?text=No+Image", width=150)
                with c2:
                    st.subheader(f"ID {p['id']}: {p['name']}")
                    st.caption(f"설명: {p.get('description') or '없음'}")
                    st.text_area(
                        "System Prompt",
                        value=p["system_prompt"],
                        height=100,
                        disabled=True,
                        key=f"prompt_{p['id']}",
                    )
                    if st.button(
                        "관리하기",
                        key=f"manage_persona_{p['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.editing_persona_id = p["id"]
                        st.rerun()

    elif st.session_state.persona_view_mode == "새 페르소나 생성":
        if (
            "init_create_mode" not in st.session_state
            or not st.session_state.init_create_mode
        ):
            if "uploaded_file" in st.session_state:
                del st.session_state.uploaded_file
            st.session_state.init_create_mode = True

        section_title("새 페르소나 생성")

        st.markdown("**프로필 이미지 (선택 사항)**")
        st.file_uploader(
            "이미지 선택",
            type=["png", "jpg", "jpeg", "webp"],
            key="file_uploader_key",
            on_change=handle_file_upload,
        )
        if st.session_state.get("uploaded_file"):
            st.image(
                st.session_state.uploaded_file,
                caption="업로드할 이미지 미리보기",
                use_container_width=True,
            )
        st.divider()

        with st.form("create_persona_form"):
            name = st.text_input("이름*", placeholder="예: 금융감독원 김민준 주임")
            description = st.text_input(
                "설명", placeholder="예: 불법 사금융 및 보이스피싱 피해 예방 전문가"
            )
            system_prompt = st.text_area(
                "시스템 프롬프트*",
                height=150,
                placeholder="예: 너는 금융감독원의 '김민준 주임'이야...",
            )

            submitted = st.form_submit_button("페르소나 생성", use_container_width=True)
            if submitted:
                if not name or not system_prompt:
                    st.warning("이름과 시스템 프롬프트는 필수입니다.")
                else:
                    image_key_to_create = None
                    if st.session_state.get("uploaded_file"):
                        file_to_upload = st.session_state.uploaded_file
                        with st.spinner("이미지 업로드 중..."):
                            presigned_data = api_client.get_presigned_url_for_upload(
                                token=token,
                                filename=file_to_upload.name,
                                category="personas",
                            )
                            if presigned_data:
                                upload_success = api_client.upload_file_to_s3(
                                    presigned_url=presigned_data["url"],
                                    file_data=file_to_upload.getvalue(),
                                    content_type=file_to_upload.type,
                                )
                                if upload_success:
                                    image_key_to_create = presigned_data["object_key"]
                                    st.toast("✅ 이미지가 성공적으로 업로드되었습니다.")
                                else:
                                    st.error(
                                        "S3에 이미지를 업로드하는 데 실패했습니다."
                                    )
                                    st.stop()
                            else:
                                st.error(
                                    "이미지 업로드 URL을 받아오는 데 실패했습니다."
                                )
                                st.stop()

                    with st.spinner("페르소나 생성 중..."):
                        creation_success = api_client.create_persona(
                            token=token,
                            name=name,
                            system_prompt=system_prompt,
                            description=description,
                            profile_image_key=image_key_to_create,
                        )

                    if creation_success:
                        st.success(
                            "페르소나가 성공적으로 생성되었습니다! 목록을 새로고침합니다."
                        )
                        st.cache_data.clear()
                        reset_form_states()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("페르소나 생성에 실패했습니다.")
