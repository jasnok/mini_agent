"""Check the local MCP endpoint using an actual initialization and tools/list."""

import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def check() -> None:
    port = int(os.environ["MCP_PORT"])
    async with asyncio.timeout(10):
        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                tools = await session.list_tools()
                if not tools.tools:
                    raise RuntimeError("MCP server returned no tools")


if __name__ == "__main__":
    asyncio.run(check())
