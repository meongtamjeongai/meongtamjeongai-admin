# views/phishing_view.py
import json
import time

import pandas as pd
import streamlit as st

from api import ApiClient


def render_phishing_case_form(api_client, token, category_map, case_data=None):
    is_edit_mode = case_data is not None
    if is_edit_mode:
        st.subheader(f"📝 피싱 사례 수정 (ID: {case_data['id']})")
    else:
        st.subheader("✍️ 새 피싱 사례 생성")

    category_codes = list(category_map.keys())
    with st.form(key="phishing_case_form"):
        default_index = (
            category_codes.index(case_data["category_code"])
            if is_edit_mode and case_data.get("category_code") in category_codes
            else 0
        )
        category_code = st.selectbox(
            "피싱 유형*",
            options=category_codes,
            format_func=lambda code: f"{code} - {category_map[code]}",
            index=default_index,
        )
        title = st.text_input(
            "제목*", value=case_data.get("title", "") if case_data else ""
        )
        content = st.text_area(
            "내용*", value=case_data.get("content", "") if case_data else "", height=200
        )
        case_date_value = (
            pd.to_datetime(case_data.get("case_date")).date()
            if is_edit_mode and case_data.get("case_date")
            else None
        )
        case_date = st.date_input("사건 발생일", value=case_date_value)
        reference_url = st.text_input(
            "참고 URL", value=case_data.get("reference_url", "") if case_data else ""
        )
        submitted = st.form_submit_button(
            "수정 완료" if is_edit_mode else "새 사례 생성하기",
            use_container_width=True,
            type="primary",
        )

        if submitted:
            if not title or not content:
                st.warning("제목과 내용은 필수 항목입니다.")
                return
            form_data = {
                "category_code": category_code,
                "title": title,
                "content": content,
                "case_date": str(case_date) if case_date else None,
                "reference_url": str(reference_url) if reference_url else None,
            }
            with st.spinner("처리 중..."):
                if is_edit_mode:
                    result = api_client.update_phishing_case(
                        token, case_data["id"], form_data
                    )
                else:
                    result = api_client.create_phishing_case(token, form_data)
            if result and "id" in result:
                st.success(
                    f"성공적으로 {'수정' if is_edit_mode else '생성'}되었습니다."
                )
                st.cache_data.clear()
                st.session_state.phishing_view_mode = "list"
                time.sleep(1)
                st.rerun()
            else:
                error_detail = (
                    result.get("detail", "알 수 없는 오류")
                    if result
                    else "API 요청 실패"
                )
                st.error(f"처리 실패: {error_detail}")

    if is_edit_mode:
        with st.expander("🚨 사례 삭제하기"):
            st.error("주의: 이 작업은 되돌릴 수 없습니다.")
            if st.button(
                f"ID {case_data['id']} 사례 영구 삭제",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("사례 삭제 중..."):
                    if api_client.delete_phishing_case(token, case_data["id"]):
                        st.success("사례가 성공적으로 삭제되었습니다.")
                        st.cache_data.clear()
                        st.session_state.phishing_view_mode = "list"
                        st.session_state.phishing_target_id = None
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("삭제에 실패했습니다.")


def render_case_list_view(api_client, token, category_map, all_cases):
    st.subheader("🗂️ 피싱 사례 목록")
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button(
            "➕ 새 피싱 사례 생성하기", use_container_width=True, type="primary"
        ):
            st.session_state.phishing_view_mode = "create"
            st.rerun()
    with col2:
        if st.button("🔄 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    st.divider()

    if not all_cases:
        st.info("등록된 피싱 사례가 없습니다.")
        return

    df_cases = pd.DataFrame(all_cases).sort_values(by="id", ascending=False)
    grouped = df_cases.groupby("category_code")
    for category_code, group in grouped:
        expander_title = f"{category_code} - {category_map.get(category_code, '알 수 없는 유형')} ({len(group)}개)"
        with st.expander(expander_title):
            for _, case in group.iterrows():
                with st.container(border=True):
                    st.markdown(
                        f"**ID: {case['id']}** | 발생일: {case.get('case_date', 'N/A')}"
                    )
                    st.markdown(f"##### {case['title']}")
                    st.text_area(
                        f"내용_{case['id']}",
                        value=case["content"],
                        height=100,
                        disabled=True,
                    )
                    if st.button(
                        "관리하기", key=f"manage_{case['id']}", use_container_width=True
                    ):
                        st.session_state.phishing_view_mode = "edit"
                        st.session_state.phishing_target_id = case["id"]
                        st.rerun()


def render_backup_restore_section_for_phishing(
    api_client: ApiClient, token: str, all_cases: list
):
    if "phishing_is_restoring" not in st.session_state:
        st.session_state.phishing_is_restoring = False

    def on_file_upload():
        if st.session_state.get("phishing_restore_uploader"):
            st.session_state.phishing_is_restoring = True
        else:
            st.session_state.phishing_is_restoring = False

    with st.expander(
        "📥 피싱 사례 데이터 백업 / 복원 📤",
        expanded=st.session_state.phishing_is_restoring,
    ):
        st.info(
            "피싱 사례 데이터를 JSON 파일로 내보내거나, 파일로부터 복원할 수 있습니다. 복원 기능은 기존 데이터를 덮어쓰지 않고 **새로운 사례를 추가**합니다."
        )
        st.subheader("데이터 내보내기 (백업)")
        try:
            cases_json = json.dumps(all_cases, ensure_ascii=False, indent=2)
            st.download_button(
                "📁 모든 피싱 사례 다운로드 (.json)",
                data=cases_json,
                file_name="mung_phishing_cases_backup.json",
                mime="application/json",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"백업 파일 생성 중 오류가 발생했습니다: {e}")
        st.divider()
        st.subheader("데이터 가져오기 (복원)")
        uploaded_file = st.file_uploader(
            "복원할 피싱 사례 JSON 파일을 업로드하세요.",
            type="json",
            key="phishing_restore_uploader",
            on_change=on_file_upload,
        )

        if uploaded_file is not None:
            try:
                restored_data = json.load(uploaded_file)
                if not isinstance(restored_data, list):
                    st.error("오류: 파일의 최상위 구조는 리스트(배열) 형태여야 합니다.")
                else:
                    st.success(
                        f"✅ 파일에서 {len(restored_data)}개의 피싱 사례를 찾았습니다."
                    )
                    st.warning(
                        "**주의:** 아래 버튼을 누르면 이 사례들이 시스템에 **새로 추가**됩니다."
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                            "복원 시작하기",
                            type="primary",
                            use_container_width=True,
                            key="phishing_restore_start",
                        ):
                            success_count, fail_count = 0, 0
                            progress_bar = st.progress(0, text="복원을 시작합니다...")
                            for i, case_data in enumerate(restored_data):
                                result = api_client.create_phishing_case(
                                    token, case_data
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
                            st.session_state.phishing_is_restoring = False
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                    with col2:
                        if st.button(
                            "취소",
                            use_container_width=True,
                            key="phishing_restore_cancel",
                        ):
                            st.session_state.phishing_is_restoring = False
                            st.rerun()
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
                st.session_state.phishing_is_restoring = False


def render_phishing_case_management_page(api_client: ApiClient, token: str):
    st.header("🎣 피싱 사례 관리")
    if "phishing_view_mode" not in st.session_state:
        st.session_state.phishing_view_mode = "list"
    if "phishing_target_id" not in st.session_state:
        st.session_state.phishing_target_id = None

    @st.cache_data(ttl=300)
    def get_categories():
        return api_client.get_phishing_categories()

    @st.cache_data(ttl=60)
    def get_all_cases():
        return api_client.get_all_phishing_cases(token)

    mode = st.session_state.phishing_view_mode
    if mode in ["edit", "create"]:
        categories = get_categories()
        if categories is None:
            st.error("피싱 유형 목록을 불러오는 데 실패했습니다.")
            return
        category_map = {cat["code"]: cat["description"] for cat in categories}
        if st.button("« 목록으로 돌아가기"):
            st.session_state.phishing_view_mode = "list"
            st.session_state.phishing_target_id = None
            st.rerun()
        st.divider()
        if mode == "create":
            render_phishing_case_form(api_client, token, category_map)
        elif mode == "edit":
            target_id = st.session_state.phishing_target_id
            all_cases = get_all_cases()
            if all_cases is None:
                st.error("피싱 사례 목록을 불러오는 데 실패했습니다.")
                return
            case_to_edit = next(
                (case for case in all_cases if case["id"] == target_id), None
            )
            if case_to_edit:
                render_phishing_case_form(
                    api_client, token, category_map, case_data=case_to_edit
                )
            else:
                st.error(
                    f"ID {target_id}에 해당하는 사례를 찾을 수 없습니다. 목록으로 돌아갑니다."
                )
                st.session_state.phishing_view_mode = "list"
                st.rerun()
        return

    categories = get_categories()
    if categories is None:
        st.error("피싱 유형 목록을 불러오는 데 실패했습니다.")
        return
    category_map = {cat["code"]: cat["description"] for cat in categories}
    all_cases = get_all_cases()
    if all_cases is None:
        st.error("피싱 사례 목록을 불러오는 데 실패했습니다.")
        return

    render_backup_restore_section_for_phishing(api_client, token, all_cases)
    st.divider()
    render_case_list_view(api_client, token, category_map, all_cases)
