import math
import os
import time

import pandas as pd  # pandas import 추가
import streamlit as st
from streamlit.components.v1 import html

# api_client.py 파일이 동일한 디렉토리에 있다고 가정합니다.
from api_client import ApiClient

# ===================================================================
# 헬퍼 함수 (Helper Functions)
# ===================================================================


def display_api_result(result_data):
    """
    API 호출 결과를 Streamlit UI에 예쁘게 표시합니다.
    결과가 없거나, dict/list, 또는 일반 문자열인 경우를 처리합니다.
    """
    if result_data is None:
        st.info("API 호출 결과가 없습니다.")
    elif isinstance(result_data, (dict, list)):
        st.json(result_data)
    else:
        st.text(str(result_data))


def section_title(title):
    """
    페이지 내에서 섹션을 구분하기 위한 공통 스타일의 제목을 생성합니다.
    """
    st.markdown(f"### {title}")
    st.divider()


# ===================================================================
# 페이지 렌더링 함수 (Page Rendering Functions)
# ===================================================================


def render_conversation_test_page(api_client, token):
    """
    대화방 관리 및 테스트 페이지 UI를 렌더링합니다.
    목록 조회, 상세 내용 확인, 메시지 전송 테스트, 삭제 기능을 통합 제공합니다.
    """

    # --- 자동 스크롤을 위한 JavaScript 함수 ---
    def scroll_to_element(element_id):
        js = f"""
        <script>
            function scroll() {{
                const element = parent.document.getElementById('{element_id}');
                if (element) {{
                    element.scrollIntoView({{behavior: 'smooth', block: 'end', inline: 'nearest'}});
                }}
            }}
            setTimeout(scroll, 250);
        </script>
        """
        html(js, height=0, width=0)

    st.header("대화방 관리 및 테스트")
    st.info(
        "이곳에서 전체 대화방을 관리하고, 특정 대화방을 선택하여 메시지 기록을 보거나 새 메시지를 보내 AI 응답을 직접 테스트할 수 있습니다."
    )

    with st.expander("새 대화방 생성하기", expanded=False):
        with st.form("create_conversation_form_admin"):
            st.write(
                "관리자 권한으로 특정 사용자와 페르소나 간의 새 대화방을 생성합니다."
            )
            col1, col2 = st.columns(2)
            with col1:
                user_id = st.number_input("대상 사용자 ID*", min_value=1, step=1)
            with col2:
                persona_id = st.number_input("대상 페르소나 ID*", min_value=1, step=1)
            title = st.text_input("대화방 제목 (선택 사항)")
            submitted = st.form_submit_button("생성하기", use_container_width=True)
            if submitted:
                with st.spinner("대화방 생성 중..."):
                    result = api_client.create_conversation_admin(
                        token=token, user_id=user_id, persona_id=persona_id, title=title
                    )
                if result and "id" in result:
                    st.success(
                        f"성공! 새 대화방이 생성되었습니다. (ID: {result['id']})"
                    )
                    st.cache_data.clear()
                else:
                    error_detail = (
                        result.get("detail", "알 수 없는 오류")
                        if result
                        else "알 수 없는 오류"
                    )
                    st.error(f"생성 실패: {error_detail}")

    st.divider()

    @st.cache_data(ttl=30)
    def get_conversations_data():
        return api_client.get_all_conversations_admin(token=token, limit=1000)

    all_conversations = get_conversations_data()
    if all_conversations is None:
        st.error("대화방 목록을 가져오는데 실패했습니다.")
        if st.button("다시 시도"):
            st.cache_data.clear()
            st.rerun()
        return

    search_query = st.text_input("검색 (사용자 이메일 또는 페르소나 이름)")
    if st.button("새로고침", use_container_width=True):
        keys_to_clear = [
            "messages",
            "current_conv_id",
            "last_api_response",
            "sort_asc",
            "scroll_to_anchor",
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.cache_data.clear()
        st.rerun()

    # 👇 [수정] 데이터가 비어있는지 먼저 확인
    if not all_conversations:
        st.info("조회된 대화방이 없습니다.")
        return  # 데이터가 없으면 아래 코드를 실행하지 않고 함수 종료

    df = pd.json_normalize(all_conversations, sep="_")
    if search_query:
        mask = df["user_email"].str.contains(search_query, case=False, na=False) | df[
            "persona_name"
        ].str.contains(search_query, case=False, na=False)
        filtered_df = df[mask]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 대화방이 조회되었습니다.")

    # 👇 [수정] filtered_df가 비어있을 경우에 대한 처리 추가
    if filtered_df.empty:
        st.info("검색 결과에 해당하는 대화방이 없습니다.")
        return

    display_df = filtered_df[
        ["id", "user_email", "persona_name", "title", "last_message_at"]
    ].copy()
    display_df.rename(
        columns={
            "id": "ID",
            "user_email": "사용자 이메일",
            "persona_name": "페르소나",
            "title": "대화방 제목",
            "last_message_at": "마지막 대화",
        },
        inplace=True,
    )

    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )
    st.divider()

    if selection.selection.rows:
        # ... (이하 상세 보기 로직은 이전과 동일)
        selected_row_index = selection.selection.rows[0]
        selected_conv_id = int(filtered_df.iloc[selected_row_index]["id"])

        section_title(f"대화 상세 및 테스트 (ID: {selected_conv_id})")

        if st.session_state.get("current_conv_id") != selected_conv_id:
            keys_to_clear = [
                "messages",
                "last_api_response",
                "sort_asc",
                "scroll_to_anchor",
            ]
            for key in keys_to_clear:
                st.session_state.pop(key, None)

        detail_c1, detail_c2 = st.columns([2, 1])

        with detail_c1:
            header_c1, header_c2 = st.columns([3, 1])
            with header_c1:
                st.subheader("✉️ 메시지 기록")
            with header_c2:
                if "sort_asc" not in st.session_state:
                    st.session_state.sort_asc = False
                button_text = (
                    "과거순으로 보기"
                    if not st.session_state.sort_asc
                    else "최신순으로 보기"
                )
                if st.button(button_text, use_container_width=True):
                    st.session_state.sort_asc = not st.session_state.sort_asc
                    st.rerun()

            if (
                "messages" not in st.session_state
                or st.session_state.get("current_conv_id") != selected_conv_id
            ):
                st.session_state.current_conv_id = selected_conv_id
                with st.spinner("메시지 기록을 불러오는 중..."):
                    st.session_state.messages = (
                        api_client.get_messages_for_conversation_admin(
                            token, selected_conv_id
                        )
                    )

            st.divider()
            if not st.session_state.get("messages"):
                st.info("메시지 기록이 없습니다.")
            else:
                messages_to_display = st.session_state.messages
                if st.session_state.sort_asc:
                    messages_to_display = reversed(messages_to_display)

                for msg in messages_to_display:
                    sender_type = msg.get("sender_type", "user")
                    avatar = (
                        "👤"
                        if sender_type == "user"
                        else "🤖"
                        if sender_type == "ai"
                        else "⚙️"
                    )
                    with st.chat_message(name=sender_type, avatar=avatar):
                        st.markdown(msg.get("content"))
                        with st.expander("메시지 상세 정보"):
                            st.json({k: v for k, v in msg.items() if k != "content"})

            st.markdown("<div id='chat_anchor'></div>", unsafe_allow_html=True)
            st.divider()

        with detail_c2:
            st.subheader("⚡️ 액션")
            with st.expander("**AI 응답 테스트하기**", expanded=True):
                with st.form(key=f"send_message_form_{selected_conv_id}"):
                    content = st.text_area(
                        "보낼 메시지 내용*", placeholder="예: 안녕? 넌 누구야?"
                    )
                    submitted = st.form_submit_button(
                        "메시지 전송 및 AI 응답 확인", use_container_width=True
                    )
                if submitted:
                    if content:
                        with st.spinner("AI가 답변을 생성하는 중..."):
                            response_data = api_client.send_message(
                                token, selected_conv_id, content
                            )
                        if response_data:
                            st.session_state.last_api_response = response_data
                            with st.spinner("채팅 기록 업데이트 중..."):
                                st.session_state.messages = (
                                    api_client.get_messages_for_conversation_admin(
                                        token, selected_conv_id
                                    )
                                )
                            st.session_state.scroll_to_anchor = True
                            st.rerun()
                        else:
                            st.error("메시지 전송 또는 AI 응답 수신에 실패했습니다.")
                            st.session_state.pop("last_api_response", None)
                    else:
                        st.warning("메시지 내용은 필수입니다.")

            if "last_api_response" in st.session_state:
                st.success("AI 응답을 성공적으로 받았습니다!")
                with st.expander("API Raw Response 보기", expanded=False):
                    display_api_result(st.session_state.last_api_response)

            with st.expander("**대화방 삭제하기**"):
                st.error("주의: 이 작업은 되돌릴 수 없습니다.")
                if st.button(
                    f"대화방 ID {selected_conv_id} 영구 삭제",
                    type="primary",
                    use_container_width=True,
                ):
                    if api_client.delete_conversation_admin(token, selected_conv_id):
                        st.success("대화방이 성공적으로 삭제되었습니다.")
                        keys_to_clear = [
                            "messages",
                            "current_conv_id",
                            "last_api_response",
                            "sort_asc",
                            "scroll_to_anchor",
                        ]
                        for key in keys_to_clear:
                            st.session_state.pop(key, None)
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("삭제에 실패했습니다.")

    if st.session_state.get("scroll_to_anchor"):
        scroll_to_element("chat_anchor")
        st.session_state.scroll_to_anchor = False


# ⭐️ 사용자 관리 페이지: DataFrame, 검색, 페이지네이션 기능으로 전면 개편 ⭐️
def render_user_management_page(api_client, token):
    """
    사용자 관리 페이지 UI를 렌더링합니다.
    Pandas DataFrame, 검색, 페이지네이션 기능을 포함합니다.
    """
    st.header("사용자 관리")

    # --- 1. 데이터 로드 및 캐싱 ---
    @st.cache_data(ttl=60)
    def get_users_data():
        return api_client.get_all_users(token=token)

    all_users = get_users_data()
    if all_users is None:
        st.error("사용자 목록을 가져오는데 실패했습니다.")
        if st.button("다시 시도"):
            st.cache_data.clear()
            st.rerun()
        return

    # --- 2. 세션 상태 초기화 ---
    if "users_page_num" not in st.session_state:
        st.session_state.users_page_num = 1
    if "users_search_query" not in st.session_state:
        st.session_state.users_search_query = ""
    if "users_per_page" not in st.session_state:
        st.session_state.users_per_page = 10

    # --- 3. UI 컨트롤 (검색, 새로고침, 페이지 당 항목 수) ---

    # 👇 [수정] 모든 컨트롤을 하나의 columns에 배치하고, 수직 정렬 및 비율 조정
    c1, c2, c3 = st.columns([5, 1, 2], vertical_alignment="bottom")

    with c1:
        search_query = st.text_input(
            "사용자 검색 (이메일 또는 사용자명)",
            value=st.session_state.users_search_query,
            key="user_search_input",
            label_visibility="collapsed",  # 라벨을 숨겨 높이를 맞춤
            placeholder="사용자 검색 (이메일 또는 사용자명)",
        )
        if search_query != st.session_state.users_search_query:
            st.session_state.users_search_query = search_query
            st.session_state.users_page_num = 1
            st.rerun()

    with c2:
        if st.button("새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with c3:
        items_per_page = st.selectbox(
            "페이지 당 항목 수",
            options=[10, 25, 50, 100],
            index=[10, 25, 50, 100].index(st.session_state.users_per_page),
            key="user_items_per_page_selector",
            label_visibility="collapsed",  # 라벨을 숨겨 높이를 맞춤
        )
        if items_per_page != st.session_state.users_per_page:
            st.session_state.users_per_page = items_per_page
            st.session_state.users_page_num = 1
            st.rerun()

    # --- 4. 데이터 필터링 및 전처리 ---
    df = pd.DataFrame(all_users)
    if search_query:
        mask = df["email"].str.contains(search_query, case=False, na=False) | df[
            "username"
        ].str.contains(search_query, case=False, na=False)
        filtered_df = df[mask]
    else:
        filtered_df = df

    # --- 5. 페이지네이션 계산 ---
    total_items = len(filtered_df)
    total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
    st.session_state.users_page_num = max(
        1, min(st.session_state.users_page_num, total_pages)
    )
    start_idx = (st.session_state.users_page_num - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_df = filtered_df.iloc[start_idx:end_idx]

    # --- 6. 데이터프레임 표시 ---
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

    # --- 7. 페이지네이션 컨트롤 (하단) ---
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

    # --- 8. 선택된 행에 대한 작업 (수정/삭제) ---
    if selection.selection.rows:
        selected_row_index = selection.selection.rows[0]
        selected_user_id = paginated_df.iloc[selected_row_index]["id"]
        user = next((u for u in all_users if u["id"] == selected_user_id), None)
        if user:
            section_title(f"사용자 작업 (ID: {user['id']}, 이메일: {user['email']})")
            action_c1, action_c2 = st.columns(2)
            with action_c1:
                with st.expander("사용자 정보 수정", expanded=False):
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
                            update_data = {
                                "username": new_username,
                                "is_active": new_is_active,
                                "is_superuser": new_is_superuser,
                            }
                            if api_client.update_user(token, user["id"], update_data):
                                st.success("사용자 정보가 업데이트되었습니다.")
                                st.cache_data.clear()
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
                        if api_client.delete_user(token, user["id"]):
                            st.success("사용자가 삭제되었습니다.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("삭제에 실패했습니다.")


def render_phishing_case_management_page(api_client, token):
    """피싱 사례 관리 페이지 UI를 렌더링합니다."""
    st.header("피싱 사례 관리")

    @st.cache_data(ttl=300)
    def get_categories():
        return api_client.get_phishing_categories()

    categories = get_categories()
    if categories is None:
        st.error(
            "피싱 유형 목록을 불러오는 데 실패했습니다. 이 문제가 해결되어야 페이지를 사용할 수 있습니다."
        )
        return

    category_map = {cat["code"]: cat["description"] for cat in categories}
    category_codes = list(category_map.keys())

    @st.cache_data(ttl=60)
    def get_cases():
        return api_client.get_all_phishing_cases(token)

    cases = get_cases()

    if "editing_case_id" not in st.session_state:
        st.session_state.editing_case_id = None

    editing_case = None
    if st.session_state.editing_case_id and cases is not None:
        editing_case = next(
            (case for case in cases if case["id"] == st.session_state.editing_case_id),
            None,
        )

    form_title = (
        "새 피싱 사례 생성"
        if editing_case is None
        else f"피싱 사례 수정 (ID: {editing_case['id']})"
    )

    with st.form(key="phishing_case_form", clear_on_submit=False):
        st.subheader(form_title)

        default_title = editing_case["title"] if editing_case else ""
        default_content = editing_case["content"] if editing_case else ""
        default_category_index = (
            category_codes.index(editing_case["category_code"]) if editing_case else 0
        )
        default_date = (
            pd.to_datetime(editing_case["case_date"]).date()
            if editing_case and editing_case["case_date"]
            else None
        )
        default_url = editing_case["reference_url"] if editing_case else ""

        category_code = st.selectbox(
            "피싱 유형*",
            options=category_codes,
            format_func=lambda code: f"{code} - {category_map[code]}",
            index=default_category_index,
        )
        title = st.text_input("제목*", value=default_title)
        content = st.text_area("내용*", value=default_content, height=200)
        case_date = st.date_input("사건 발생일", value=default_date)
        reference_url = st.text_input("참고 URL", value=default_url)

        submitted = st.form_submit_button(
            "저장하기" if editing_case is None else "수정 완료"
        )

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

                if editing_case:
                    result = api_client.update_phishing_case(
                        token, editing_case["id"], case_data
                    )
                    if result and "id" in result:
                        st.success("사례가 성공적으로 수정되었습니다.")
                        st.session_state.editing_case_id = None
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        error_detail = (
                            result.get("detail", "알 수 없는 오류")
                            if result
                            else "API 요청 실패. 서버 연결을 확인해주세요."
                        )
                        st.error(f"수정 실패: {error_detail}")
                else:
                    result = api_client.create_phishing_case(token, case_data)
                    if result and "id" in result:
                        st.success("새 사례가 성공적으로 생성되었습니다.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        error_detail = (
                            result.get("detail", "알 수 없는 오류")
                            if result
                            else "API 요청 실패. 서버 연결을 확인해주세요."
                        )
                        st.error(f"생성 실패: {error_detail}")

    if st.session_state.editing_case_id:
        if st.button("수정 취소"):
            st.session_state.editing_case_id = None
            st.rerun()

    st.divider()

    # --- 3. 기존 사례 목록 표시 ---
    st.subheader("기존 피싱 사례 목록")

    if cases is None:
        st.error(
            "피싱 사례 목록을 불러오는 데 실패했습니다. 네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
        )
    elif not cases:
        st.info("등록된 피싱 사례가 없습니다.")
    else:
        # 👇 [수정] Pandas DataFrame으로 변환하여 유형별로 그룹화
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
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"**ID: {case['id']}**")
                            st.markdown(f"##### {case['title']}")
                            st.caption(
                                f"발생일: {case.get('case_date', 'N/A')} | 출처: {case.get('reference_url', 'N/A')}"
                            )
                        with c2:
                            if st.button(
                                "수정",
                                key=f"edit_{case['id']}",
                                use_container_width=True,
                            ):
                                st.session_state.editing_case_id = case["id"]
                                st.rerun()
                            if st.button(
                                "삭제",
                                key=f"delete_{case['id']}",
                                type="primary",
                                use_container_width=True,
                            ):
                                if api_client.delete_phishing_case(token, case["id"]):
                                    st.success(
                                        f"사례(ID: {case['id']})가 삭제되었습니다."
                                    )
                                    st.cache_data.clear()
                                    st.session_state.editing_case_id = None
                                    st.rerun()
                                else:
                                    st.error("삭제에 실패했습니다.")


def render_persona_management_page(api_client, token):
    """페르소나 관리 페이지 UI를 렌더링합니다."""
    st.header("페르소나 관리")
    tab1, tab2 = st.tabs(["페르소나 목록", "새 페르소나 생성"])

    # '페르소나 목록' 탭
    with tab1:
        if st.button("페르소나 목록 새로고침"):
            st.cache_data.clear()
            st.rerun()

        @st.cache_data(ttl=60)
        def get_personas_data():
            return api_client.get_personas(token)

        personas = get_personas_data()
        if personas is None:
            st.error("페르소나 목록을 가져오는 데 실패했습니다.")
            return

        st.write(f"총 {len(personas)}개의 페르소나가 조회되었습니다.")
        for p in personas:
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.subheader(f"ID {p['id']}: {p['name']}")
                    st.caption(f"Public: {p['is_public']}")
                    st.text_area(
                        "System Prompt",
                        value=p["system_prompt"],
                        height=100,
                        disabled=True,
                        key=f"prompt_{p['id']}",
                    )
                with c2:
                    if st.button("수정", key=f"edit_persona_{p['id']}"):
                        st.session_state["edit_persona_id"] = p["id"]
                    if st.button(
                        "삭제", key=f"delete_persona_{p['id']}", type="primary"
                    ):
                        st.session_state["delete_persona_id"] = p["id"]

                # 페르소나 수정 폼
                if st.session_state.get("edit_persona_id") == p["id"]:
                    with st.expander(f"**ID {p['id']} 페르소나 수정**", expanded=True):
                        with st.form(key=f"update_form_persona_{p['id']}"):
                            name = st.text_input("이름", value=p["name"])
                            desc = st.text_input("설명", value=p.get("description", ""))
                            prompt = st.text_area(
                                "시스템 프롬프트", value=p["system_prompt"], height=150
                            )
                            is_public = st.checkbox("공개", value=p["is_public"])
                            if st.form_submit_button("저장"):
                                update_data = {
                                    "name": name,
                                    "description": desc,
                                    "system_prompt": prompt,
                                    "is_public": is_public,
                                }
                                if api_client.update_persona(
                                    token, p["id"], update_data
                                ):
                                    st.success("업데이트 성공!")
                                    st.cache_data.clear()
                                    del st.session_state["edit_persona_id"]
                                    st.rerun()
                                else:
                                    st.error("업데이트 실패.")

                # 페르소나 삭제 확인
                if st.session_state.get("delete_persona_id") == p["id"]:
                    st.warning(
                        f"**정말로 페르소나 ID {p['id']} ({p['name']})을(를) 삭제하시겠습니까?**"
                    )
                    c1, c2 = st.columns(2)
                    if c1.button(
                        "예, 삭제합니다",
                        key=f"confirm_delete_p_{p['id']}",
                        type="primary",
                    ):
                        if api_client.delete_persona(token, p["id"]):
                            st.success("삭제 성공!")
                            st.cache_data.clear()
                            del st.session_state["delete_persona_id"]
                            st.rerun()
                        else:
                            st.error("삭제 실패.")
                    if c2.button("아니요", key=f"cancel_delete_p_{p['id']}"):
                        del st.session_state["delete_persona_id"]
                        st.rerun()

    # '새 페르소나 생성' 탭
    with tab2:
        section_title("새 페르소나 생성")
        with st.form("create_persona_form"):
            name = st.text_input("이름*", placeholder="예: 고양이 집사 츄르")
            system_prompt = st.text_area(
                "시스템 프롬프트*",
                height=150,
                placeholder="예: 너는 고양이를 매우 사랑하는 고양이 집사야...",
            )
            description = st.text_input(
                "설명", placeholder="예: 세상의 모든 고양이를 사랑하는 츄르"
            )
            if st.form_submit_button("페르소나 생성"):
                if name and system_prompt:
                    if api_client.create_persona(
                        token, name, system_prompt, description
                    ):
                        st.success("페르소나가 성공적으로 생성되었습니다!")
                        st.cache_data.clear()
                    else:
                        st.error("페르소나 생성에 실패했습니다.")
                else:
                    st.warning("이름과 시스템 프롬프트는 필수입니다.")


def render_gemini_test_page(api_client, token):
    """Gemini API 연동을 테스트하는 페이지를 렌더링합니다."""
    st.header("🤖 Gemini 연동 테스트")
    st.info(
        "이 페이지에서 페르소나와 대화하며 실제 Gemini API 응답을 확인할 수 있습니다."
    )

    section_title("1. 테스트용 대화방 생성")
    with st.form("create_conversation_form"):
        persona_id = st.number_input("대화할 페르소나 ID*", min_value=1, step=1)
        title = st.text_input("대화방 제목 (선택 사항)")
        if st.form_submit_button("대화방 생성"):
            new_conv = api_client.create_conversation(token, int(persona_id), title)
            if new_conv:
                st.success("대화방이 성공적으로 생성되었습니다!")
                display_api_result(new_conv)
                st.info(
                    f"생성된 대화방 ID: **{new_conv['id']}**. 아래 메시지 전송에 이 ID를 사용하세요."
                )
            else:
                st.error("대화방 생성에 실패했습니다.")

    section_title("2. 메시지 전송 및 AI 응답 확인")
    with st.form("send_message_form"):
        conversation_id = st.number_input(
            "메시지를 보낼 대화방 ID*", min_value=1, step=1
        )
        content = st.text_input("보낼 메시지 내용*", placeholder="예: 안녕? 넌 누구야?")
        if st.form_submit_button("메시지 전송 및 AI 응답 받기"):
            if conversation_id and content:
                with st.spinner("AI가 답변을 생성하는 중..."):
                    response_messages = api_client.send_message(
                        token, int(conversation_id), content
                    )
                    if response_messages:
                        st.success("AI 응답을 성공적으로 받았습니다!")
                        display_api_result(response_messages)
                    else:
                        st.error("메시지 전송 또는 AI 응답 수신에 실패했습니다.")
            else:
                st.warning("대화방 ID와 메시지 내용은 필수입니다.")


def render_login_page(api_client):
    """
    로그인 페이지 UI를 렌더링하고, Placeholder Pattern을 사용해 로그인 시도 시
    폼 중복 표시 버그를 방지합니다.
    """
    st.subheader("관리자 로그인")

    is_dev_mode = os.getenv("APP_ENV") == "dev"
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


def render_initial_setup_page(api_client):
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
                    time.sleep(3)
                    st.rerun()
                else:
                    st.error(
                        f"계정 생성 실패: {result.get('detail', '알 수 없는 오류')}"
                    )


def render_main_app(api_client, token):
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

    page_options[selected_page](api_client, token)


# ===================================================================
# 메인 애플리케이션 로직
# ===================================================================
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
            is_signup_mode_enabled = os.getenv("SECRET_SIGNUP_MODE") == "true"
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
