# views/conversation_view.py
import time

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html

from api import ApiClient
from utils import display_api_result, section_title


def render_conversation_test_page(api_client: ApiClient, token: str):
    """
    대화방 관리 및 테스트 페이지 UI를 렌더링합니다.
    목록 조회, 상세 내용 확인, 메시지 전송 테스트, 삭제 기능을 통합 제공합니다.
    (시작 메시지 표시, 동적 선택지 버튼 기능 포함)
    """

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

        @st.cache_data(ttl=120)
        def get_all_users_for_selection():
            return api_client.get_all_users(token=token)

        @st.cache_data(ttl=120)
        def get_all_personas_for_selection():
            return api_client.get_personas(token=token)

        all_users = get_all_users_for_selection()
        all_personas = get_all_personas_for_selection()

        if not all_users or not all_personas:
            st.warning(
                "⚠️ 사용자 또는 페르소나 목록을 불러오는 데 실패했습니다. 잠시 후 새로고침 해주세요."
            )
        else:
            with st.form("create_conversation_form_admin"):
                st.write(
                    "관리자 권한으로 특정 사용자와 페르소나 간의 새 대화방을 생성합니다."
                )
                col1, col2 = st.columns(2)

                with col1:
                    selected_user = st.selectbox(
                        "대상 사용자*",
                        options=all_users,
                        format_func=lambda user: f"{user.get('username', user['email'])} (ID: {user['id']})",
                        help="대화를 시작할 사용자를 선택하세요.",
                    )
                with col2:
                    selected_persona = st.selectbox(
                        "대상 페르소나*",
                        options=all_personas,
                        format_func=lambda p: f"{p['name']} (ID: {p['id']})",
                        help="대화에 사용할 페르소나를 선택하세요.",
                    )

                title = st.text_input("대화방 제목 (선택 사항)")
                submitted = st.form_submit_button("생성하기", use_container_width=True)

                if submitted:
                    user_id = selected_user["id"] if selected_user else None
                    persona_id = selected_persona["id"] if selected_persona else None

                    if not user_id or not persona_id:
                        st.error("사용자와 페르소나를 모두 선택해야 합니다.")
                    else:
                        with st.spinner("대화방 생성 중..."):
                            result = api_client.create_conversation_admin(
                                token=token,
                                user_id=user_id,
                                persona_id=persona_id,
                                title=title,
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
            "selected_conv_id",
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.cache_data.clear()
        st.rerun()

    if not all_conversations:
        st.info("조회된 대화방이 없습니다.")
        return

    # 원본 JSON 구조를 유지한 DataFrame 생성
    df_original = pd.DataFrame(all_conversations)
    df_normalized = pd.json_normalize(all_conversations, sep=".")

    if search_query:
        mask = df_normalized["user.email"].str.contains(
            search_query, case=False, na=False
        ) | df_normalized["persona.name"].str.contains(
            search_query, case=False, na=False
        )
        filtered_indices = df_normalized[mask].index
        filtered_df = df_original.loc[filtered_indices]
    else:
        filtered_df = df_original

    st.write(f"총 {len(filtered_df)}개의 대화방이 조회되었습니다.")

    if filtered_df.empty:
        st.info("검색 결과에 해당하는 대화방이 없습니다.")
        return

    # 화면 표시용 DataFrame 생성
    display_df = pd.DataFrame(
        {
            "ID": filtered_df["id"],
            "사용자 ID": filtered_df["user"].apply(lambda u: u.get("id", "N/A")),
            "사용자 이메일": filtered_df["user"].apply(lambda u: u.get("email", "N/A")),
            "페르소나": filtered_df["persona"].apply(lambda p: p.get("name", "N/A")),
            "시나리오 ID": filtered_df["applied_phishing_case_id"]
            .fillna(0)
            .astype(int),
            "대화방 제목": filtered_df["title"],
            "마지막 대화": filtered_df["last_message_at"],
        }
    )

    # '마지막 대화' 열의 문자열을 datetime 객체로 변환합니다.
    # 변환 실패 시 (예: 값이 None인 경우) NaT(Not a Time)으로 처리됩니다.
    dt_series = pd.to_datetime(display_df["마지막 대화"], errors="coerce")

    # 1. 원본 시간이 UTC 기준임을 명시하고,
    # 2. 'Asia/Seoul' (KST) 타임존으로 변환한 후,
    # 3. 'YYYY-MM-DD HH:MM:SS' 형식의 문자열로 만듭니다.
    # 4. 변환에 실패했던 NaT 값은 'N/A'로 채웁니다.
    display_df["마지막 대화"] = (
        dt_series.dt.tz_localize("UTC")
        .dt.tz_convert("Asia/Seoul")
        .dt.strftime("%Y-%m-%d %H:%M:%S")
        .fillna("N/A")
    )

    selection = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selection.selection.rows:
        selected_row_index = selection.selection.rows[0]
        selected_id = int(filtered_df.iloc[selected_row_index]["id"])

        if st.session_state.get("selected_conv_id") != selected_id:
            st.session_state.selected_conv_id = selected_id
            st.rerun()

    st.divider()

    if st.session_state.get("selected_conv_id"):
        selected_conv_id = st.session_state.get("selected_conv_id")

        selected_conv_data_row = filtered_df[filtered_df["id"] == selected_conv_id]

        if selected_conv_data_row.empty:
            del st.session_state.selected_conv_id
            st.rerun()
            return

        selected_conv_data = selected_conv_data_row.iloc[0].to_dict()

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

            st.divider()

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

            if not st.session_state.get("messages"):
                st.info("메시지 기록이 없습니다.")
            else:
                messages_to_display = st.session_state.messages
                if not st.session_state.sort_asc:
                    messages_to_display = reversed(list(messages_to_display))

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
                            filtered_msg_details = {
                                k: v for k, v in msg.items() if k != "content"
                            }
                            st.json(filtered_msg_details)

            st.markdown("<div id='chat_anchor'></div>", unsafe_allow_html=True)
            st.divider()

        with detail_c2:
            st.subheader("⚡️ 액션")

            with st.expander("🤖 현재 페르소나 정보", expanded=True):
                persona_info = selected_conv_data.get("persona", {})
                st.markdown(f"**이름**: `{persona_info.get('name', 'N/A')}`")

                starting_message = persona_info.get("starting_message")
                if starting_message:
                    st.markdown("**시작 메시지**:")
                    st.info(starting_message)

                st.markdown("**시스템 프롬프트**:")
                st.text_area(
                    label="Original System Prompt",
                    value=persona_info.get("system_prompt", "프롬프트 정보 없음"),
                    height=150,
                    disabled=True,
                    key=f"system_prompt_{selected_conv_id}",
                )

            with st.expander("🎣 현재 적용된 피싱 시나리오", expanded=True):
                # 대화방 데이터에서 피싱 사례 ID를 가져옵니다.
                case_id = selected_conv_data.get("applied_phishing_case_id")

                # API 호출 결과를 캐싱하기 위한 함수를 내부에 정의합니다.
                @st.cache_data(ttl=300)  # 5분 동안 결과 캐시
                def get_phishing_case_details(id_to_fetch: int):
                    return api_client.get_phishing_case_by_id(
                        token=token, case_id=id_to_fetch
                    )

                if case_id:
                    with st.spinner(f"피싱 사례(ID: {case_id}) 정보 조회 중..."):
                        phishing_info = get_phishing_case_details(case_id)

                    if phishing_info:
                        st.markdown(f"**ID**: `{phishing_info.get('id', 'N/A')}`")
                        st.markdown(
                            f"**유형**: `{phishing_info.get('category_code', 'N/A')}`"
                        )
                        st.markdown(f"**제목**: `{phishing_info.get('title', 'N/A')}`")
                        st.text_area(
                            label="시나리오 내용",
                            value=phishing_info.get("content", "내용 없음"),
                            height=150,
                            disabled=True,
                            key=f"phishing_content_{selected_conv_id}",
                        )
                        with st.popover("전체 데이터 보기"):
                            st.json(phishing_info)
                    else:
                        st.error(
                            f"피싱 사례(ID: {case_id}) 정보를 불러오는 데 실패했습니다."
                        )
                else:
                    st.info("현재 적용된 피싱 시나리오가 없습니다.")

            with st.expander("**AI 응답 테스트하기**", expanded=True):
                with st.form(key=f"send_message_form_{selected_conv_id}"):
                    content = st.text_area(
                        "보낼 메시지 내용*",
                        placeholder="여기에 메시지를 입력하거나 아래 선택지 버튼을 클릭하세요.",
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
                    else:
                        st.warning("메시지 내용은 필수입니다.")

                st.markdown("##### 빠른 선택지")
                options_to_show = []
                messages_exist = st.session_state.get("messages")

                if not messages_exist:
                    starters = selected_conv_data.get("persona", {}).get(
                        "conversation_starters"
                    )
                    if starters and isinstance(starters, list):
                        options_to_show = starters
                        st.caption("ℹ️ 페르소나의 '대화 시작 선택지'입니다.")
                elif st.session_state.get("last_api_response"):
                    suggestions = st.session_state.last_api_response.get(
                        "suggested_user_questions"
                    )
                    if suggestions:
                        options_to_show = suggestions
                        st.caption("ℹ️ AI가 생성한 '추천 질문'입니다.")

                if options_to_show:
                    # 선택지 개수에 따라 유연하게 컬럼 생성
                    num_options = len(options_to_show)
                    cols = st.columns(num_options) if num_options > 0 else []
                    for i, option in enumerate(options_to_show):
                        if cols[i].button(
                            option, key=f"option_{i}", use_container_width=True
                        ):
                            with st.spinner(f"'{option}' 메시지 전송 중..."):
                                response_data = api_client.send_message(
                                    token, selected_conv_id, option
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
                                st.error(
                                    "메시지 전송 또는 AI 응답 수신에 실패했습니다."
                                )
                else:
                    st.info("표시할 선택지가 없습니다.")

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
                        st.cache_data.clear()
                        keys_to_clear = [
                            "messages",
                            "current_conv_id",
                            "last_api_response",
                            "sort_asc",
                            "scroll_to_anchor",
                            "selected_conv_id",
                        ]
                        for key in keys_to_clear:
                            st.session_state.pop(key, None)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("삭제에 실패했습니다.")

    if st.session_state.get("scroll_to_anchor"):
        scroll_to_element("chat_anchor")
        st.session_state.scroll_to_anchor = False
