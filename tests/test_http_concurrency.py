
import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


URL = "http://127.0.0.1:8000/mcp"


async def call_tool(tool_name):
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(tool_name, {})

            return {
                "tool": tool_name,
                "blocked": result.isError,
                "content": result.content,
            }


async def main():
    print("Sending two concurrent HTTP tool requests...")

    results = await asyncio.gather(
        call_tool("generate_verification_code"),
        call_tool("gateway_health_check"),
    )

    for result in results:
        print(
            f"{result['tool']}: "
            f"{'BLOCKED' if result['blocked'] else 'ALLOWED'}"
        )


if __name__ == "__main__":
    asyncio.run(main())
