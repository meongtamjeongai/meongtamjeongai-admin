# utils.py
import streamlit as st


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