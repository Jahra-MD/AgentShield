
import asyncio

from agentshield.authorization.manager import AuthorizationManager


async def main():
    manager = AuthorizationManager(timeout=1.0)

    task = asyncio.create_task(
        manager.request_approval(
            "add_numbers",
            {"a": 10, "b": 20},
        )
    )

    await asyncio.sleep(0.1)

    request_id = next(iter(manager.pending))

    # Wait for authorization to expire.
    result = await task

    # Attempt approval after expiration.
    late_approval = manager.resolve(request_id, True)

    assert result is False
    assert late_approval is False
    assert len(manager.pending) == 0

    print("Timeout decision: BLOCKED")
    print("Late approval accepted:", late_approval)
    print("Pending requests:", len(manager.pending))
    print("Late approval test: PASSED")


if __name__ == "__main__":
    asyncio.run(main())
