# views/image_analysis_view.py
import base64

import streamlit as st

from api import ApiClient


def render_image_analysis_page(api_client: ApiClient, token: str):
    """이미지 피싱 분석 테스트 페이지 UI를 렌더링합니다."""
    st.header("🔬 이미지 피싱 분석 테스트")
    st.info(
        "분석하고 싶은 이미지를 업로드하고 '분석 시작' 버튼을 누르면, AI가 해당 이미지의 피싱 위험도를 분석하여 점수와 이유를 알려줍니다."
    )

    # 분석 결과와 에러 메시지를 저장할 세션 상태 초기화
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "analysis_error" not in st.session_state:
        st.session_state.analysis_error = None

    uploaded_file = st.file_uploader(
        "분석할 이미지 파일 업로드", type=["png", "jpg", "jpeg", "webp"]
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🖼️ 업로드된 이미지")
        if uploaded_file is not None:
            st.image(uploaded_file, use_container_width=True)
        else:
            st.info("왼쪽에서 분석할 이미지를 업로드해주세요.")

    with col2:
        st.subheader("📊 분석 결과")
        if st.button(
            "분석 시작", disabled=(uploaded_file is None), use_container_width=True
        ):
            # 버튼 클릭 시 이전 결과 초기화
            st.session_state.analysis_result = None
            st.session_state.analysis_error = None

            with st.spinner("AI가 이미지를 분석하는 중입니다. 잠시만 기다려주세요..."):
                # 파일을 읽어 Base64로 인코딩
                image_b64_string = base64.b64encode(uploaded_file.getvalue()).decode(
                    "utf-8"
                )

                # API 호출
                result = api_client.analyze_image_for_phishing(
                    token=token, image_base64=image_b64_string
                )

                if result and "phishing_score" in result:
                    st.session_state.analysis_result = result
                else:
                    st.session_state.analysis_error = result.get(
                        "detail", "알 수 없는 오류가 발생했습니다."
                    )
            # 분석 완료 후 UI를 다시 그리도록 rerun
            st.rerun()

        # 분석 결과 또는 에러 메시지 표시
        if st.session_state.analysis_result:
            result = st.session_state.analysis_result
            score = result.get("phishing_score", 0)
            reason = result.get("reason", "분석 이유를 찾을 수 없습니다.")

            st.metric(
                label="피싱 위험도 점수",
                value=f"{score} / 100",
                delta=f"{'높음' if score > 70 else '보통' if score > 40 else '낮음'}",
                delta_color="inverse",
            )
            st.text_area("분석 이유", value=reason, height=200, disabled=True)

        elif st.session_state.analysis_error:
            st.error(f"분석 실패: {st.session_state.analysis_error}")
        else:
            st.info("분석 버튼을 눌러주세요.")
