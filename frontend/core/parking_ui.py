"""Workflow와 AI Agent 주차 화면의 공통 Streamlit UI."""

import os
from typing import Any, Literal

import streamlit as st

from clients.parking_client import execute_parking, recognize_vehicle
from core.api_client import BackendAPIError
from core.parking_mock import MOCK_SCENARIOS, get_mock_response


Mode = Literal["workflow", "agent"]
MAX_IMAGE_BYTES = int(float(os.getenv("MAX_IMAGE_SIZE_MB", "5")) * 1024 * 1024)


def _show_result(result: dict[str, Any]) -> None:
    st.subheader("처리 결과")
    if not result.get("success"):
        st.error(result.get("message", "처리 중 오류가 발생했습니다."))
        error = result.get("error")
        if error:
            st.caption(f"오류 코드: {error.get('code', 'UNKNOWN')}")
    elif result.get("gate_opened"):
        st.success(result["message"])
    else:
        st.warning(result["message"])

    col1, col2 = st.columns(2)
    col1.metric("인식된 차량 번호", result.get("vehicle_number") or "인식 실패")
    col2.metric("차량 상태", result.get("vehicle_status") or "확인 불가")
    col3, col4 = st.columns(2)
    col3.metric("등록 여부", "등록" if result.get("registered") else "미등록")
    col4.metric("출입문", "열림" if result.get("gate_opened") else "닫힘")

    st.container(border=True).write(result.get("message", "안내 메시지가 없습니다."))
    if result.get("trace"):
        with st.expander("처리 단계(Trace)"):
            st.dataframe(result["trace"], use_container_width=True, hide_index=True)
    with st.expander("API 응답 확인"):
        st.json(result)


def _call_backend(mode: Mode, image: Any) -> dict[str, Any]:
    recognized = recognize_vehicle(image.name, image.getvalue(), image.type or "application/octet-stream")
    if not recognized.get("success") or not recognized.get("vehicle_number"):
        return {
            "success": False, "vehicle_number": None, "registered": False,
            "vehicle_status": None, "gate_opened": False,
            "message": recognized.get("message", "번호판을 인식하지 못했습니다."),
            "execution_type": mode, "status": "error", "trace": [],
            "termination_reason": "tool_execution_error", "error": recognized.get("error"),
        }
    return execute_parking(mode, recognized["vehicle_number"])


def render_parking_page(mode: Mode) -> None:
    is_workflow = mode == "workflow"
    page_name = "Workflow" if is_workflow else "AI Agent"
    state_key, error_key = f"parking_{mode}_result", f"parking_{mode}_error"

    st.title(f"{'🔀' if is_workflow else '🤖'} 주차장 {page_name}")
    st.caption(f"{'2-4' if is_workflow else '2-5'} · 번호판 이미지로 출입 결과를 확인합니다.")

    source = st.radio("데이터 연결", ["Mock API", "Backend API"], horizontal=True, key=f"{mode}_source")
    if source == "Mock API":
        st.info("사진 자체를 인식하지 않습니다. 아래 시나리오를 Backend 응답으로 가정해 UI를 테스트합니다.")
    else:
        st.info("사진을 Backend에 전송해 번호판을 인식한 뒤 출입 API를 호출합니다.")

    st.subheader("1. 번호판 이미지 입력")
    camera_tab, upload_tab = st.tabs(["📷 카메라 촬영", "🖼️ 이미지 업로드"])
    with camera_tab:
        camera_image = st.camera_input("자동차 번호판을 촬영하세요", key=f"{mode}_camera")
    with upload_tab:
        uploaded_image = st.file_uploader("번호판 이미지 선택", type=["jpg", "jpeg", "png"], key=f"{mode}_upload")
    image = camera_image if camera_image is not None else uploaded_image
    image_error = None
    if image is not None:
        st.image(image, caption="선택한 번호판 이미지", width=520)
        if image.size > MAX_IMAGE_BYTES:
            image_error = f"이미지 크기가 제한({MAX_IMAGE_BYTES // 1024 // 1024}MB)을 초과했습니다."
            st.error(image_error)
    else:
        st.caption("촬영하거나 업로드한 이미지가 여기에 표시됩니다.")

    scenario = None
    if source == "Mock API":
        st.subheader("2. Mock 인식 결과 선택")
        scenario = st.selectbox("사진과 무관하게 반환할 테스트 응답", list(MOCK_SCENARIOS), key=f"{mode}_scenario")
        st.caption("실제 번호판 인식 결과가 아니며, 기본 선택값은 12가3456입니다.")
    else:
        st.subheader("2. Backend 번호판 인식 및 출입 확인")

    can_run = image_error is None and (source == "Mock API" or image is not None)
    if st.button(f"{page_name}로 출입 확인", type="primary", use_container_width=True, disabled=not can_run, key=f"{mode}_submit"):
        st.session_state.pop(state_key, None)
        st.session_state.pop(error_key, None)
        try:
            with st.spinner("번호판을 인식하고 출입 요청을 처리하고 있습니다..."):
                st.session_state[state_key] = get_mock_response(scenario, mode) if source == "Mock API" else _call_backend(mode, image)
        except (BackendAPIError, ConnectionError) as error:
            st.session_state[error_key] = str(error)

    if source == "Backend API" and image is None:
        st.warning("Backend API 실행을 위해 번호판 이미지를 촬영하거나 업로드해 주세요.")

    error = st.session_state.get(error_key)
    if error:
        st.error(error)
        st.caption("Backend 실행 상태와 네트워크 연결을 확인한 뒤 다시 시도해 주세요.")
        if st.button("오류 닫기", use_container_width=True, key=f"{mode}_dismiss"):
            st.session_state.pop(error_key, None)
            st.rerun()

    result = st.session_state.get(state_key)
    if result:
        _show_result(result)
