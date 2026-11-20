
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

from agentshield.authorization.manager import AuthorizationManager


class AuthorizedFastMCP(FastMCP):
    """
    FastMCP server that requires user approval
    before executing a registered tool.
    """

    def __init__(
        self,
        *args,
        authorization_manager: AuthorizationManager,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.authorization_manager = authorization_manager

    async def call_tool(self, name: str, arguments: dict):
        allowed = await self.authorization_manager.request_approval(
            tool_name=name,
            arguments=arguments,
        )

        if not allowed:
            raise McpError(
                ErrorData(
                    code=-32000,
                    message=(
                        "AgentShield: Tool execution denied "
                        "or authorization timed out."
                    ),
                )
            )

        # Execute only after approval.
        return await super().call_tool(name, arguments)
