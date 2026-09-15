"""호텔 정책을 제공하는 stdio / Streamable HTTP MCP Server입니다.

MCP_TRANSPORT=streamable-http로 설정하면 HTTP 서버로 실행합니다.
stdio의 stdout은 MCP 메시지 전용이므로 일반 로그는 출력하지 않습니다.
"""

import os
from typing import Literal

from mcp.server.fastmcp import FastMCP

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
if MCP_TRANSPORT not in ("stdio", "streamable-http"):
    raise ValueError("MCP_TRANSPORT는 stdio 또는 streamable-http여야 합니다.")

MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8011"))


mcp = FastMCP(
    "mini-agent-policy",
    instructions="호텔 ID로 체크인 및 취소 정책을 제공합니다.",
    host=MCP_HOST,
    port=MCP_PORT,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def get_hotel_policy(
    hotel_id: Literal["hotel-busan-001", "hotel-seoul-001"],
) -> dict:
    """호텔 검색 결과의 hotel_id로 체크인 및 취소 정책을 조회합니다."""
    policies = {
        "hotel-busan-001": {
            "hotel_name": "바다 호텔",
            "check_in": "15:00",
            "check_out": "11:00",
            "cancellation": "체크인 2일 전까지 무료 취소",
        },
        "hotel-seoul-001": {
            "hotel_name": "도시 호텔",
            "check_in": "15:00",
            "check_out": "11:00",
            "cancellation": "체크인 1일 전까지 무료 취소",
        },
    }
    return {
        "hotel_id": hotel_id,
        **policies[hotel_id],
        "source": "hotel-policy-service",
    }


if __name__ == "__main__":
    mcp.run(transport=MCP_TRANSPORT)
