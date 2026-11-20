
import asyncio
import os
import uvicorn

from agentshield.authorization.manager import AuthorizationManager
from agentshield.proxy.authorized_fastmcp import AuthorizedFastMCP
from agentshield.security.token_auth import TokenAuthMiddleware
from mcp.server.transport_security import TransportSecuritySettings


async def run_http_gateway(bridge):
    """
    Run the authorized MCP HTTP server.

    Tkinter runs on the main thread.
    This function runs in the background asyncio thread.
    """

    loop = asyncio.get_running_loop()

    manager = AuthorizationManager(
        timeout=30.0,
        on_request=bridge.notify_request,
        on_finished=bridge.notify_finished,
    )

    # Connect popup decisions to this event loop.
    bridge.set_backend(loop, manager)

    mcp = AuthorizedFastMCP(
    "AgentShield HTTP Gateway",
    authorization_manager=manager,
    host="127.0.0.1",
    port=8000,
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
        "127.0.0.1:8000",
        "localhost:8000",
        *(
        [os.environ["AGENTSHIELD_PUBLIC_HOST"]]
        if os.environ.get("AGENTSHIELD_PUBLIC_HOST")
        else []
        ),
       ],
    ),
    )

    @mcp.tool()
    def gateway_health_check() -> dict:
        """Return the HTTP gateway status."""
        return {
            "gateway": "AgentShield",
            "transport": "streamable-http",
            "status": "running",
        }

    @mcp.tool()
    def generate_verification_code() -> str:
        """Generate a random code after authorization."""
        import secrets
        return secrets.token_hex(8)

    app = TokenAuthMiddleware(mcp.streamable_http_app())

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        bridge.mark_stopped()


def main():
    """
    Launch the HTTP gateway with its Tkinter UI.
    """
    from agentshield.web_main import main as web_main
    web_main()


if __name__ == "__main__":
    main()
