"""카페 주문 문장에서 Tool arguments를 추출하고 누락값을 재질문합니다.

Backend 디렉터리 기준 역할:
- `schemas/`: CafeOrderInput이 주문 Tool의 필수 arguments 계약을 정의합니다.
- `agents/`: mock_extract_arguments가 LLM Tool Call을 흉내 내고 prepare_order가 누락값을 판단합니다.
- `tools/`: 완전한 arguments가 만들어진 뒤 실행될 주문 Tool은 이 실습 범위에서 생략합니다.
- `services/`: 별도의 업무 Service 없이 Agent의 추출·재질문 판단에 집중합니다.
- `routers/`: 이 파일에서는 `__main__` 실행부가 사용자 문장 입력을 대신합니다.
- `providers/`: 실제 Provider 대신 규칙 기반 Mock 추출기를 사용합니다.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


# [schemas/] 주문 Tool이 요구하는 메뉴·크기·수량 arguments 계약입니다.
class CafeOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    menu: Literal["아메리카노", "카페라테", "레몬에이드"]
    size: Literal["small", "medium", "large"]
    quantity: int = Field(ge=1, le=10)


# [agents/ 보조 규칙] Mock 추출기가 한국어 표현을 Tool arguments 값으로 바꿀 때 사용합니다.
SIZE_WORDS = {"스몰": "small", "미디엄": "medium", "라지": "large"}
QUANTITY_WORDS = {"한": 1, "두": 2, "세": 3}


# [agents/] 실제 Provider의 Tool Call 대신 문장에서 arguments를 추출하는 Mock 판단기입니다.
def mock_extract_arguments(message: str) -> dict[str, Any]:
    """실제 서비스에서는 LLM의 Tool Call이 이 arguments를 생성합니다."""
    arguments: dict[str, Any] = {}
    for menu in ("아메리카노", "카페라테", "레몬에이드"):
        if menu in message:
            arguments["menu"] = menu
            break
    for korean_size, value in SIZE_WORDS.items():
        if korean_size in message:
            arguments["size"] = value
            break
    for word, value in QUANTITY_WORDS.items():
        if f"{word} 잔" in message or f"{word}잔" in message:
            arguments["quantity"] = value
            break
    if "quantity" not in arguments:
        arguments["quantity"] = next(
            (number for number in range(1, 11) if f"{number}잔" in message or f"{number} 잔" in message),
            None,
        )
        if arguments["quantity"] is None:
            arguments.pop("quantity")
    return arguments


# [agents/] 추출 결과의 누락값을 찾고 재질문 또는 실행 준비 상태를 결정합니다.
def prepare_order(message: str) -> dict[str, Any]:
    arguments = mock_extract_arguments(message)
    missing = [field for field in CafeOrderInput.model_fields if field not in arguments]
    if missing:
        labels = {"menu": "메뉴", "size": "크기", "quantity": "수량"}
        return {
            "status": "needs_clarification",
            "arguments": arguments,
            "missing_arguments": missing,
            "follow_up_question": f"{', '.join(labels[field] for field in missing)}을(를) 알려주세요.",
        }
    try:
        order = CafeOrderInput.model_validate(arguments)
        return {"status": "ready", "arguments": order.model_dump()}
    except ValidationError as error:
        return {"status": "invalid", "arguments": arguments, "errors": error.errors()}


# [routers/ 대체] 여러 사용자 문장을 입력해 준비 완료와 추가 질문 응답을 비교합니다.
if __name__ == "__main__":
    for text in ("라지 아메리카노 두 잔 주세요", "미디엄 카페라테 2 잔 주세요", "카페라테 주세요", "미디엄 한 잔 주세요"):
        print(f"\n사용자: {text}")
        print(prepare_order(text))
