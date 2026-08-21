import streamlit as st

from core.api_client import BackendAPIError, upload_voice_translation


st.title("1-7. 음성 영어 번역")
st.caption("한국어 음성을 영어 문장과 영어 합성 음성으로 변환합니다.")
st.info(
    "녹음한 음성은 처리를 위해 외부 AI 서비스로 전송되며 이 앱은 음성을 "
    "영구 저장하지 않습니다. 결과 음성은 AI가 생성한 합성 음성입니다."
)

recording = st.audio_input("한국어로 말해 주세요")
voice = st.selectbox("영어 합성 음성", ["coral", "marin", "cedar", "alloy", "nova"])

if recording is not None:
    st.caption("전송 전에 녹음 내용을 확인할 수 있습니다.")
    st.audio(recording)

if st.button(
    "영어로 번역하고 음성 만들기",
    type="primary",
    disabled=recording is None,
):
    try:
        with st.spinner("음성을 인식하고 영어 번역과 합성 음성을 만들고 있습니다."):
            result = upload_voice_translation(
                recording.name,
                recording.getvalue(),
                recording.type,
                voice,
            )
        st.session_state["voice_translation_result"] = result
    except BackendAPIError as error:
        st.error(str(error))

result = st.session_state.get("voice_translation_result")
if result:
    left, right = st.columns(2)
    with left:
        st.subheader("인식된 한국어")
        st.write(result["transcript"])
    with right:
        st.subheader("영어 번역")
        st.write(result["translation"])
    st.warning("아래 음성은 AI가 생성한 합성 음성입니다.")
    st.audio(result["audio"], format=result["audio_mime_type"])

st.caption("마이크가 동작하지 않으면 브라우저 주소창에서 마이크 권한을 확인해 주세요.")
