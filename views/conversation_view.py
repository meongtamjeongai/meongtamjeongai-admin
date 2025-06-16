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
            "selected_conv_id",
        ]
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        st.cache_data.clear()
        st.rerun()

    if not all_conversations:
        st.info("조회된 대화방이 없습니다.")
        return

    df = pd.json_normalize(all_conversations, sep="_")
    if search_query:
        mask = df["user_email"].str.contains(search_query, case=False, na=False) | df[
            "persona_name"
        ].str.contains(search_query, case=False, na=False)
        filtered_df = df[mask]
    else:
        filtered_df = df

    st.write(f"총 {len(filtered_df)}개의 대화방이 조회되었습니다.")

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

    if selection.selection.rows:
        selected_row_index = selection.selection.rows[0]
        st.session_state.selected_conv_id = int(
            filtered_df.iloc[selected_row_index]["id"]
        )

    st.divider()

    if st.session_state.get("selected_conv_id"):
        selected_conv_id = st.session_state.get("selected_conv_id")
        selected_conv_data_row = filtered_df[filtered_df["id"] == selected_conv_id]
        if not selected_conv_data_row.empty:
            selected_conv_data = selected_conv_data_row.iloc[0].to_dict()
        else:
            del st.session_state.selected_conv_id
            st.rerun()
            return

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
                            is_last_ai_message = (
                                sender_type == "ai"
                                and "last_api_response" in st.session_state
                                and st.session_state.last_api_response["ai_message"][
                                    "id"
                                ]
                                == msg["id"]
                            )

                            if (
                                is_last_ai_message
                                and "debug_request_contents"
                                in st.session_state.last_api_response
                            ):
                                with st.expander("🪙 토큰 계산에 사용된 Contents 보기"):
                                    st.info(
                                        "아래 내용은 `gemini_token_usage` 계산의 기반이 된 실제 데이터입니다."
                                    )
                                    st.json(
                                        st.session_state.last_api_response[
                                            "debug_request_contents"
                                        ]
                                    )

                            filtered_msg_details = {
                                k: v
                                for k, v in msg.items()
                                if k not in ["content", "applied_phishing_case"]
                            }
                            st.json(filtered_msg_details)

            st.markdown("<div id='chat_anchor'></div>", unsafe_allow_html=True)
            st.divider()

        with detail_c2:
            st.subheader("⚡️ 액션")

            with st.expander("🤖 현재 페르소나의 원본 시스템 프롬프트"):
                persona_prompt = selected_conv_data.get(
                    "persona_system_prompt", "프롬프트 정보를 불러올 수 없습니다."
                )
                st.text_area(
                    label="Original System Prompt",
                    value=persona_prompt,
                    height=200,
                    disabled=True,
                    key=f"system_prompt_{selected_conv_id}",
                )

            if (
                "last_api_response" in st.session_state
                and st.session_state.last_api_response.get("final_system_prompt")
            ):
                with st.expander("🚀 AI에 적용된 최종 시스템 프롬프트", expanded=True):
                    final_prompt = st.session_state.last_api_response.get(
                        "final_system_prompt"
                    )
                    st.text_area(
                        label="Final System Prompt Applied to AI",
                        value=final_prompt,
                        height=250,
                        disabled=True,
                        key=f"final_prompt_{selected_conv_id}",
                    )

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
                            "selected_conv_id",
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


def render_gemini_test_page(api_client: ApiClient, token: str):
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
