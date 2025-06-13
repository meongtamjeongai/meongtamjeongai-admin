# views/phishing_view.py
import pandas as pd
import streamlit as st

from api import ApiClient


def render_phishing_case_management_page(api_client: ApiClient, token: str):
    """피싱 사례 관리 페이지 UI를 렌더링합니다."""
    st.header("피싱 사례 관리")

    @st.cache_data(ttl=300)
    def get_categories():
        return api_client.get_phishing_categories()

    categories = get_categories()
    if categories is None:
        st.error("피싱 유형 목록을 불러오는 데 실패했습니다.")
        return

    category_map = {cat["code"]: cat["description"] for cat in categories}
    category_codes = list(category_map.keys())

    @st.cache_data(ttl=60)
    def get_cases():
        return api_client.get_all_phishing_cases(token)

    cases = get_cases()

    if "editing_case_id" not in st.session_state:
        st.session_state.editing_case_id = None
    if "confirming_delete_id" not in st.session_state:
        st.session_state.confirming_delete_id = None

    with st.expander("새 피싱 사례 생성하기", expanded=True):
        with st.form(key="create_phishing_case_form", clear_on_submit=True):
            st.subheader("새 피싱 사례 생성")
            category_code = st.selectbox(
                "피싱 유형*",
                options=category_codes,
                format_func=lambda code: f"{code} - {category_map[code]}",
            )
            title = st.text_input("제목*")
            content = st.text_area("내용*", height=200)
            case_date = st.date_input("사건 발생일")
            reference_url = st.text_input("참고 URL")
            submitted = st.form_submit_button("새 사례 생성하기")

            if submitted:
                if not title or not content:
                    st.warning("제목과 내용은 필수 항목입니다.")
                else:
                    case_data = {
                        "category_code": category_code,
                        "title": title,
                        "content": content,
                        "case_date": str(case_date) if case_date else None,
                        "reference_url": str(reference_url) if reference_url else None,
                    }
                    result = api_client.create_phishing_case(token, case_data)
                    if result and "id" in result:
                        st.success("새 사례가 성공적으로 생성되었습니다.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        error_detail = (
                            result.get("detail", "알 수 없는 오류")
                            if result
                            else "API 요청 실패"
                        )
                        st.error(f"생성 실패: {error_detail}")

    st.divider()
    st.subheader("기존 피싱 사례 목록")

    if cases is None:
        st.error("피싱 사례 목록을 불러오는 데 실패했습니다.")
    elif not cases:
        st.info("등록된 피싱 사례가 없습니다.")
    else:
        df_cases = pd.DataFrame(cases)
        grouped = df_cases.groupby("category_code")

        for category_code, group in grouped:
            category_description = category_map.get(category_code, "알 수 없는 유형")
            expander_title = (
                f"{category_code} - {category_description} ({len(group)}개)"
            )

            with st.expander(expander_title):
                for _, case in group.iterrows():
                    with st.container(border=True):
                        st.markdown(
                            f"**ID: {case['id']}** | 발생일: {case.get('case_date', 'N/A')}"
                        )
                        st.markdown(f"##### {case['title']}")
                        st.text_area(
                            "내용",
                            value=case["content"],
                            height=150,
                            disabled=True,
                            key=f"content_text_{case['id']}",
                        )
                        st.caption(f"참고 URL: {case.get('reference_url', '없음')}")
                        st.divider()

                        action_c1, action_c2 = st.columns(2)
                        with action_c1:
                            if st.button(
                                "수정",
                                key=f"edit_{case['id']}",
                                use_container_width=True,
                            ):
                                st.session_state.editing_case_id = case["id"]
                                st.session_state.confirming_delete_id = None
                                st.rerun()
                        with action_c2:
                            if st.button(
                                "삭제",
                                key=f"delete_{case['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                st.session_state.confirming_delete_id = case["id"]
                                st.session_state.editing_case_id = None
                                st.rerun()

                        if st.session_state.get("editing_case_id") == case["id"]:
                            with st.form(
                                key=f"update_form_{case['id']}", clear_on_submit=False
                            ):
                                st.info(f"ID {case['id']} 사례 수정 중...")
                                new_category_code = st.selectbox(
                                    "피싱 유형*",
                                    options=category_codes,
                                    format_func=lambda code: f"{code} - {category_map[code]}",
                                    index=category_codes.index(case["category_code"]),
                                    key=f"cat_{case['id']}",
                                )
                                new_title = st.text_input(
                                    "제목*",
                                    value=case["title"],
                                    key=f"title_{case['id']}",
                                )
                                new_content = st.text_area(
                                    "내용*",
                                    value=case["content"],
                                    height=150,
                                    key=f"cont_{case['id']}",
                                )
                                form_c1, form_c2 = st.columns(2)
                                with form_c1:
                                    if st.form_submit_button(
                                        "수정 완료",
                                        use_container_width=True,
                                        type="primary",
                                    ):
                                        update_data = {
                                            "category_code": new_category_code,
                                            "title": new_title,
                                            "content": new_content,
                                        }
                                        result = api_client.update_phishing_case(
                                            token, case["id"], update_data
                                        )
                                        if result and "id" in result:
                                            st.success("수정 완료!")
                                            st.session_state.editing_case_id = None
                                            st.cache_data.clear()
                                            st.rerun()
                                        else:
                                            st.error("수정 실패")
                                with form_c2:
                                    if st.form_submit_button(
                                        "취소", use_container_width=True
                                    ):
                                        st.session_state.editing_case_id = None
                                        st.rerun()

                        if st.session_state.get("confirming_delete_id") == case["id"]:
                            st.warning(
                                f"**정말로 ID {case['id']} 사례를 삭제하시겠습니까?** 이 작업은 되돌릴 수 없습니다."
                            )
                            del_c1, del_c2 = st.columns(2)
                            with del_c1:
                                if st.button(
                                    "예, 삭제합니다",
                                    key=f"confirm_del_{case['id']}",
                                    type="primary",
                                    use_container_width=True,
                                ):
                                    if api_client.delete_phishing_case(
                                        token, case["id"]
                                    ):
                                        st.success(
                                            f"사례(ID: {case['id']})가 삭제되었습니다."
                                        )
                                        st.session_state.confirming_delete_id = None
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("삭제 실패")
                            with del_c2:
                                if st.button(
                                    "아니요, 취소합니다",
                                    key=f"cancel_del_{case['id']}",
                                    use_container_width=True,
                                ):
                                    st.session_state.confirming_delete_id = None
                                    st.rerun()