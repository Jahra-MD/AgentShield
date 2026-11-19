
import asyncio
import sys


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError


async def main():
    server_params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "agentshield.main"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"- {tool.name}")

            try:
                result = await session.call_tool(
                    "add_numbers",
                    arguments={"a": 10, "b": 20},
                )
                print("Tool result:", result.content)
            except McpError as e:
                print("Error calling tool:", e)

if __name__ == "__main__":
    asyncio.run(main())
