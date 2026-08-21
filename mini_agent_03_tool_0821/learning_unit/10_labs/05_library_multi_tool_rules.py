"""여러 조회 Tool Result를 모은 뒤 서버의 도서 대출 규칙을 적용합니다.

Backend 디렉터리 기준 역할:
- `tools/`: get_member, get_book, get_current_loans가 독립적인 조회 Tool입니다.
- `services/`: evaluate_loan이 대출 규칙을 적용하고 request_loan이 고정 Workflow를 조정합니다.
- `agents/`: Tool 순서를 동적으로 선택하지 않으므로 별도 Agent를 사용하지 않습니다.
- `schemas/`: 입력 모델을 생략한 심화 실습이며 실제 Backend에서는 ID 계약을 정의해야 합니다.
- `routers/`: 이 파일에서는 `__main__` 실행부가 대출 요청 Endpoint를 대신합니다.
- `providers/`: Tool 선택을 고정해 두었으므로 LLM Provider는 사용하지 않습니다.
"""

from typing import Any


# [학습용 저장소] 실제 Backend에서는 회원·도서·대출 Repository 또는 DB가 담당합니다.
MEMBERS = {
    "M100": {"name": "김민준", "active": True, "overdue": False},
    "M200": {"name": "이서연", "active": True, "overdue": True},
}
BOOKS = {
    "B101": {"title": "파이썬 첫걸음", "available": True},
    "B102": {"title": "에이전트 설계", "available": False},
}
LOANS = {"M100": ["B201", "B202"], "M200": ["B203"]}
MAX_LOANS = 3


# [tools/] 회원 ID로 회원 상태를 조회하는 읽기 전용 Tool입니다.
def get_member(member_id: str) -> dict[str, Any]:
    return {"member_id": member_id, "member": MEMBERS.get(member_id)}


# [tools/] 도서 ID로 도서와 대출 가능 상태를 조회하는 읽기 전용 Tool입니다.
def get_book(book_id: str) -> dict[str, Any]:
    return {"book_id": book_id, "book": BOOKS.get(book_id)}


# [tools/] 회원의 현재 대출 목록과 권수를 조회하는 읽기 전용 Tool입니다.
def get_current_loans(member_id: str) -> dict[str, Any]:
    loans = LOANS.get(member_id, [])
    return {"member_id": member_id, "book_ids": loans.copy(), "count": len(loans)}


# [services/] 세 Tool Result를 조합해 서버의 대출 허용 규칙을 적용합니다.
def evaluate_loan(member_result: dict, book_result: dict, loans_result: dict) -> dict[str, Any]:
    """LLM 답변이 아니라 백엔드 업무 규칙이 대출 가능 여부를 결정합니다."""
    member = member_result["member"]
    book = book_result["book"]
    if member is None:
        return {"allowed": False, "reason": "회원 정보를 찾을 수 없습니다."}
    if not member["active"]:
        return {"allowed": False, "reason": "비활성 회원입니다."}
    if member["overdue"]:
        return {"allowed": False, "reason": "연체 도서가 있습니다."}
    if book is None:
        return {"allowed": False, "reason": "도서 정보를 찾을 수 없습니다."}
    if not book["available"]:
        return {"allowed": False, "reason": "이미 대출 중인 도서입니다."}
    if loans_result["count"] >= MAX_LOANS:
        return {"allowed": False, "reason": "최대 대출 권수를 초과합니다."}
    return {"allowed": True, "reason": "대출할 수 있습니다."}


# [services/] 조회 Tool 실행 → 정책 판단 → 상태 변경의 고정 Workflow를 조정합니다.
def request_loan(member_id: str, book_id: str) -> dict[str, Any]:
    tool_results = {
        "member": get_member(member_id),
        "book": get_book(book_id),
        "loans": get_current_loans(member_id),
    }
    decision = evaluate_loan(tool_results["member"], tool_results["book"], tool_results["loans"])
    if decision["allowed"]:
        LOANS.setdefault(member_id, []).append(book_id)
        BOOKS[book_id]["available"] = False
    return {"tool_results": tool_results, "decision": decision}


# [routers/ 대체] API 대신 여러 회원·도서 조합을 요청해 정책 결과를 확인합니다.
if __name__ == "__main__":
    for member_id, book_id in (("M100", "B101"), ("M200", "B101"), ("M100", "B102")):
        print(f"\n요청: {member_id} / {book_id}")
        print(request_loan(member_id, book_id))
