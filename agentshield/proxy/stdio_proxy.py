
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from agentshield.authorization.manager import AuthorizationManager


# --------------------------------------------------
# Logging
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = PROJECT_ROOT / "proxy_debug.log"

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="[AgentShield] %(message)s",
)

logger = logging.getLogger("agentshield")

logger.addHandler(
    logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )
)


# --------------------------------------------------
# Send blocked response to MCP client
# --------------------------------------------------


async def send_denial(request_id, client_write_lock):
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": (
                        "AgentShield: Tool execution was explicitly "
                        "blocked by the user. The tool was not executed. "
                        "Do not retry without a new user request."
                    ),
                }
            ],
            "isError": True,
        },
    }

    encoded = (
        json.dumps(response) + "\n"
    ).encode("utf-8")

    async with client_write_lock:
        await asyncio.to_thread(
            sys.stdout.buffer.write,
            encoded,
        )

        await asyncio.to_thread(
            sys.stdout.buffer.flush,
        )



# --------------------------------------------------
# Handle tool authorization
# --------------------------------------------------

async def handle_tool_call(
    message,
    original_line,
    server,
    manager,
    server_write_lock,
    client_write_lock,
):
    params = message.get("params") or {}

    if not isinstance(params, dict):
        logger.warning("Invalid tools/call parameters")

        await send_denial(
            message.get("id"),
            client_write_lock,
        )
        return

    tool_name = params.get("name", "unknown")
    arguments = params.get("arguments") or {}

    logger.info(
        "Authorization requested: %s",
        tool_name,
    )

    allowed = await manager.request_approval(
        tool_name=tool_name,
        arguments=arguments,
    )

    if allowed:
        logger.info("Allowed: %s", tool_name)

        async with server_write_lock:
            server.stdin.write(original_line)
            await server.stdin.drain()

    else:
        logger.info("Blocked: %s", tool_name)

        await send_denial(
            message.get("id"),
            client_write_lock,
        )


# --------------------------------------------------
# Forward client requests to MCP server
# --------------------------------------------------

async def client_to_server(
    server,
    manager,
    server_write_lock,
    client_write_lock,
):
    logger.info("Client-to-server relay started")

    approval_tasks = set()

    try:
        while True:
            try:
                line = await asyncio.to_thread(
                    sys.stdin.buffer.readline
                )
            except Exception:
                logger.exception(
                    "Failed to read MCP client input"
                )
                raise

            if not line:
                logger.warning(
                    "MCP client input reached EOF"
                )
                break

            try:
                message = json.loads(line)

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ):
                logger.warning(
                    "Invalid JSON received from client"
                )
                continue

            if isinstance(message, dict):
                logger.info(
                    "Received MCP method: %s",
                    message.get("method", "<response>"),
                )

            if (
                isinstance(message, dict)
                and message.get("method") == "tools/call"
                and "id" in message
            ):
                logger.info(
                    "Intercepted tools/call request id=%s",
                    message.get("id"),
                )

                task = asyncio.create_task(
                    handle_tool_call(
                        message,
                        line,
                        server,
                        manager,
                        server_write_lock,
                        client_write_lock,
                    )
                )

                approval_tasks.add(task)

                def on_approval_done(completed_task):
                    approval_tasks.discard(completed_task)

                    if completed_task.cancelled():
                        logger.warning(
                            "Approval task cancelled"
                        )
                    elif completed_task.exception() is not None:
                        logger.error(
                            "Approval task failed",
                            exc_info=(
                                type(completed_task.exception()),
                                completed_task.exception(),
                                completed_task.exception().__traceback__,
                            ),
                        )

                task.add_done_callback(on_approval_done)

                continue

            async with server_write_lock:
                server.stdin.write(line)
                await server.stdin.drain()

    except asyncio.CancelledError:
        logger.info(
            "Client-to-server relay cancelled"
        )
        raise

    except Exception:
        logger.exception(
            "Client-to-server relay failed"
        )
        raise

    finally:
        logger.info(
            "Cleaning up pending approval tasks"
        )

        for task in approval_tasks:
            task.cancel()

        if approval_tasks:
            await asyncio.gather(
                *approval_tasks,
                return_exceptions=True,
            )


# --------------------------------------------------
# Forward MCP server responses to client
# --------------------------------------------------

async def server_to_client(
    server,
    client_write_lock,
):
    logger.info("Server-to-client relay started")

    try:
        while True:
            line = await server.stdout.readline()

            if not line:
                logger.warning(
                    "MCP server output reached EOF"
                )
                break

            async with client_write_lock:
                await asyncio.to_thread(
                    sys.stdout.buffer.write,
                    line,
                )

                await asyncio.to_thread(
                    sys.stdout.buffer.flush,
                )

    except asyncio.CancelledError:
        logger.info(
            "Server-to-client relay cancelled"
        )
        raise

    except Exception:
        logger.exception(
            "Server-to-client relay failed"
        )
        raise


# --------------------------------------------------
# Start AgentShield MCP proxy
# --------------------------------------------------

async def main(bridge=None):
    logger.info("Proxy main started")

    manager = AuthorizationManager(
        timeout=30.0,
        on_request=(
            bridge.notify_request
            if bridge is not None
            else None
        ),
        on_finished=(
            bridge.notify_finished
            if bridge is not None
            else None
        ),
    )

    if bridge is not None:
        bridge.set_backend(
            asyncio.get_running_loop(),
            manager,
        )

    server_write_lock = asyncio.Lock()
    client_write_lock = asyncio.Lock()

    # Read MCP server configuration once.
    server_command = os.environ.get(
        "AGENTSHIELD_SERVER_COMMAND",
        sys.executable,
    )

    server_args = json.loads(
        os.environ.get(
            "AGENTSHIELD_SERVER_ARGS",
            '["tests/test_server.py"]',
        )
    )

    if not isinstance(server_args, list) or not all(
        isinstance(arg, str) for arg in server_args
    ):
        raise ValueError(
            "AGENTSHIELD_SERVER_ARGS must be a JSON array of strings"
        )

    logger.info(
        "Starting configured MCP server: %s",
        server_command,
    )

    # Use an explicit working directory for the child server.
    server = await asyncio.create_subprocess_exec(
        server_command,
        *server_args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=sys.stderr,
        cwd=str(PROJECT_ROOT),
    )

    logger.info("MCP server subprocess started")

    client_task = asyncio.create_task(
        client_to_server(
            server,
            manager,
            server_write_lock,
            client_write_lock,
        ),
        name="client_to_server",
    )

    server_task = asyncio.create_task(
        server_to_client(
            server,
            client_write_lock,
        ),
        name="server_to_client",
    )

    try:
        done, pending = await asyncio.wait(
            [client_task, server_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            task_name = task.get_name()

            if task.cancelled():
                logger.error(
                    "%s was cancelled",
                    task_name,
                )

            elif task.exception() is not None:
                error = task.exception()

                logger.error(
                    "%s failed",
                    task_name,
                    exc_info=(
                        type(error),
                        error,
                        error.__traceback__,
                    ),
                )

            else:
                logger.warning(
                    "%s ended normally",
                    task_name,
                )

        # Preserve exception propagation for unexpected failures.
        for task in done:
            if not task.cancelled():
                task.result()

    finally:
        logger.info("Shutting down MCP proxy")

        for task in (client_task, server_task):
            if not task.done():
                task.cancel()

        if server.returncode is None:
            logger.info(
                "Terminating MCP server subprocess"
            )

            server.terminate()

            try:
                await asyncio.wait_for(
                    server.wait(),
                    timeout=5.0,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    "MCP server did not stop; killing process"
                )

                server.kill()
                await server.wait()

        await asyncio.gather(
            client_task,
            server_task,
            return_exceptions=True,
        )

        logger.info("MCP proxy stopped")


if __name__ == "__main__":
    asyncio.run(main())
