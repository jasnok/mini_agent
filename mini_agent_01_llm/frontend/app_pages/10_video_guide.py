import streamlit as st

from core.api_client import BACKEND_URL


st.title("1-8. 영상 분석 음성 안내")
st.caption("동영상 또는 카메라의 현재 장면 한 장을 분석해 한국어 음성으로 안내합니다.")
st.info(
    "영상 캡처는 브라우저의 video·canvas·MediaDevices API를 사용하므로 "
    "백엔드가 제공하는 전용 화면에서 실행됩니다. 원본 동영상 전체는 업로드하지 않습니다."
)
st.link_button("영상 분석 화면 열기", f"{BACKEND_URL}/video/", type="primary")
st.warning("캡처 이미지는 외부 AI 서비스로 전송되며 결과 음성은 AI 합성 음성입니다.")
