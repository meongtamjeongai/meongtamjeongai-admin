# views/persona_view.py
import json
import time

import streamlit as st

from api import ApiClient
from utils import section_title


def render_backup_restore_section_for_persona(
    api_client: ApiClient, token: str, all_personas: list
):
    """페르소나 데이터의 백업 및 복원 UI를 렌더링합니다."""

    if "persona_is_restoring" not in st.session_state:
        st.session_state.persona_is_restoring = False

    def on_file_upload():
        if st.session_state.get("persona_restore_uploader"):
            st.session_state.persona_is_restoring = True
        else:
            st.session_state.persona_is_restoring = False

    with st.expander(
        "📥 페르소나 데이터 백업 / 복원 📤",
        expanded=st.session_state.persona_is_restoring,
    ):
        st.info(
            "페르소나 데이터를 JSON 파일로 내보내거나, 파일로부터 복원할 수 있습니다. "
            "복원 기능은 기존 데이터를 덮어쓰지 않고 **새로운 페르소나를 추가**합니다."
        )

        st.subheader("데이터 내보내기 (백업)")
        try:
            personas_json = json.dumps(all_personas, ensure_ascii=False, indent=2)
            st.download_button(
                label="📁 모든 페르소나 다운로드 (.json)",
                data=personas_json,
                file_name="mung_personas_backup.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"백업 파일 생성 중 오류가 발생했습니다: {e}")

        st.divider()

        st.subheader("데이터 가져오기 (복원)")
        uploaded_file = st.file_uploader(
            "복원할 페르소나 JSON 파일을 업로드하세요.",
            type="json",
            key="persona_restore_uploader",
            on_change=on_file_upload,
        )

        if uploaded_file is not None:
            try:
                restored_data = json.load(uploaded_file)
                if not isinstance(restored_data, list):
                    st.error("오류: 파일의 최상위 구조는 리스트(배열) 형태여야 합니다.")
                else:
                    st.success(
                        f"✅ 파일에서 {len(restored_data)}개의 페르소나를 찾았습니다."
                    )
                    st.warning(
                        "**주의:** 아래 버튼을 누르면 이 페르소나들이 시스템에 **새로 추가**됩니다."
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "복원 시작하기", type="primary", use_container_width=True
                        ):
                            success_count, fail_count = 0, 0
                            progress_bar = st.progress(0, text="복원을 시작합니다...")

                            for i, persona_data in enumerate(restored_data):
                                result = api_client.create_persona(
                                    token=token,
                                    name=persona_data.get("name", "이름 없음"),
                                    system_prompt=persona_data.get("system_prompt", ""),
                                    description=persona_data.get("description"),
                                    profile_image_key=None,
                                    starting_message=persona_data.get(
                                        "starting_message"
                                    ),
                                    conversation_starters=persona_data.get(
                                        "conversation_starters"
                                    ),
                                )
                                if result and "id" in result:
                                    success_count += 1
                                else:
                                    fail_count += 1

                                progress_text = f"진행 중... ({i + 1}/{len(restored_data)}) 성공: {success_count}, 실패: {fail_count}"
                                progress_bar.progress(
                                    (i + 1) / len(restored_data), text=progress_text
                                )

                            st.success(
                                f"복원 완료! 성공: {success_count}건, 실패: {fail_count}건"
                            )
                            st.session_state.persona_is_restoring = False
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    with col2:
                        if st.button("취소", use_container_width=True):
                            st.session_state.persona_is_restoring = False
                            st.rerun()
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
                st.session_state.persona_is_restoring = False


def render_persona_management_page(api_client: ApiClient, token: str):
    """
    페르소나 관리 페이지 UI를 렌더링합니다.
    """
    st.header("페르소나 관리")

    @st.cache_data(ttl=60)
    def get_personas_data():
        return api_client.get_personas(token)

    def handle_file_upload():
        if st.session_state.get("file_uploader_key"):
            st.session_state.uploaded_file = st.session_state.file_uploader_key
        else:
            st.session_state.uploaded_file = None

    def reset_form_states():
        keys_to_delete = [
            "editing_persona_id",
            "uploaded_file",
            "file_uploader_key",
            "delete_image_checked",
            "init_edit_mode",
            "init_create_mode",
            "persona_view_mode",
            "persona_is_restoring",
        ]
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]

    # --- 1. 수정 뷰 렌더링 ---
    if (
        "editing_persona_id" in st.session_state
        and st.session_state.editing_persona_id is not None
    ):
        all_personas = get_personas_data()
        if all_personas is None:
            st.error("페르소나 목록을 가져오는 데 실패했습니다.")
            return

        persona_to_edit = next(
            (p for p in all_personas if p["id"] == st.session_state.editing_persona_id),
            None,
        )

        if persona_to_edit is None:
            st.error("수정할 페르소나를 찾을 수 없습니다. 목록으로 돌아갑니다.")
            reset_form_states()
            st.rerun()
            return

        if st.button("« 목록으로 돌아가기"):
            reset_form_states()
            st.rerun()

        section_title(f"페르소나 수정 (ID: {persona_to_edit['id']})")

        img_c1, img_c2 = st.columns(2)
        with img_c1:
            st.markdown("**현재 이미지**")
            current_image_key = persona_to_edit.get("profile_image_key")
            if current_image_key:
                with st.spinner("이미지 로딩 중..."):
                    download_url = api_client.get_presigned_url_for_download(
                        token, current_image_key
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

            st.divider()
            st.markdown("##### 💬 대화 시작 설정 (선택 사항)")
            starting_message = st.text_area(
                "시작 메시지",
                value=persona_to_edit.get("starting_message", ""),
                placeholder="페르소나와 대화를 시작할 때 가장 먼저 표시될 메시지를 입력하세요.",
                help="이 메시지는 사용자가 대화방에 처음 입장했을 때 자동으로 표시됩니다.",
            )
            starters_text = "\n".join(
                persona_to_edit.get("conversation_starters") or []
            )
            conversation_starters_input = st.text_area(
                "대화 시작 선택지",
                value=starters_text,
                placeholder="예시:\n안녕? 넌 누구야?\n피싱 사기가 뭔지 알려줘\n오늘의 학습 주제는 뭐야?",
                help="사용자에게 보여줄 대화 시작 선택지를 한 줄에 하나씩 입력하세요.",
            )
            st.divider()

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
                                if previous_image_key:
                                    should_delete_previous_image = True
                            else:
                                st.error("S3에 이미지를 업로드하는 데 실패했습니다.")
                        else:
                            st.error("이미지 업로드 URL을 받아오는 데 실패했습니다.")

                starters_list = [
                    line.strip()
                    for line in conversation_starters_input.split("\n")
                    if line.strip()
                ]

                update_data = {
                    "name": name,
                    "description": desc,
                    "system_prompt": prompt,
                    "is_public": is_public,
                    "profile_image_key": final_image_key,
                    "starting_message": starting_message,
                    "conversation_starters": starters_list,
                }

                with st.spinner("페르소나 정보 저장 중..."):
                    if api_client.update_persona(
                        token, persona_to_edit["id"], update_data
                    ):
                        if should_delete_previous_image:
                            with st.spinner("이전 이미지 정리 중..."):
                                api_client.delete_s3_object(token, previous_image_key)
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
                    with st.spinner("연결된 이미지 삭제 중..."):
                        if not api_client.delete_s3_object(token, image_key_to_delete):
                            st.error(
                                "S3 이미지 삭제에 실패했습니다. 페르소나 삭제를 중단합니다."
                            )
                            st.stop()
                if api_client.delete_persona(token, persona_to_edit["id"]):
                    st.success("페르소나가 성공적으로 삭제되었습니다.")
                    st.cache_data.clear()
                    reset_form_states()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("삭제에 실패했습니다.")
        return

    # --- 2. 목록 및 생성/백업 뷰 렌더링 ---
    all_personas = get_personas_data()
    if all_personas is None:
        st.error("페르소나 목록을 가져오는 데 실패했습니다.")
        return

    render_backup_restore_section_for_persona(api_client, token, all_personas)
    st.divider()

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

        personas = sorted(all_personas, key=lambda p: p["id"])
        st.write(f"총 {len(personas)}개의 페르소나가 조회되었습니다.")
        st.divider()

        for p in personas:
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                with c1:
                    image_key = p.get("profile_image_key")
                    if image_key:

                        @st.cache_data(ttl=300)
                        def get_cached_download_url(key, auth_token):
                            return api_client.get_presigned_url_for_download(
                                token=auth_token, object_key=key
                            )

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

            st.divider()
            st.markdown("##### 💬 대화 시작 설정 (선택 사항)")
            starting_message = st.text_area(
                "시작 메시지",
                placeholder="페르소나와 대화를 시작할 때 가장 먼저 표시될 메시지를 입력하세요.",
            )
            conversation_starters_input = st.text_area(
                "대화 시작 선택지",
                placeholder="사용자에게 보여줄 대화 시작 선택지를 한 줄에 하나씩 입력하세요.",
                help="한 줄에 하나의 선택지를 입력합니다.",
            )
            st.divider()

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
                                else:
                                    st.error("S3 업로드 실패.")
                                    st.stop()
                            else:
                                st.error("업로드 URL 생성 실패.")
                                st.stop()

                    starters_list = [
                        line.strip()
                        for line in conversation_starters_input.split("\n")
                        if line.strip()
                    ]

                    with st.spinner("페르소나 생성 중..."):
                        creation_success = api_client.create_persona(
                            token=token,
                            name=name,
                            system_prompt=system_prompt,
                            description=description,
                            profile_image_key=image_key_to_create,
                            starting_message=starting_message,
                            conversation_starters=starters_list,
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
