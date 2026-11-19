
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError


async def call_tool(session, label, a, b):
    try:
        result = await session.call_tool(
            "add_numbers",
            arguments={"a": a, "b": b},
        )

        print(f"{label}: ALLOWED")
        print(f"{label} result: {result.content}")

    except McpError as error:
        print(f"{label}: BLOCKED")
        print(f"{label} error: {error}")


async def main():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agentshield.main"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("Sending two concurrent tool calls...")

            await asyncio.gather(
                call_tool(session, "Request A", 10, 20),
                call_tool(session, "Request B", 50, 60),
            )


if __name__ == "__main__":
    asyncio.run(main())
