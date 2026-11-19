
import asyncio

from agentshield.authorization.manager import AuthorizationManager


async def main():
    manager = AuthorizationManager(timeout=5.0)

    # Two independent approval requests
    task_a = asyncio.create_task(
        manager.request_approval(
            "add_numbers",
            {"a": 10, "b": 20},
        )
    )

    task_b = asyncio.create_task(
        manager.request_approval(
            "add_numbers",
            {"a": 50, "b": 60},
        )
    )

    # Give both tasks a chance to register.
    await asyncio.sleep(0.1)

    assert len(manager.pending) == 2

    for request_id, request in list(manager.pending.items()):
        if request.arguments["a"] == 10:
            manager.resolve(request_id, False)
        elif request.arguments["a"] == 50:
            manager.resolve(request_id, True)

    result_a, result_b = await asyncio.gather(
        task_a,
        task_b,
    )

    assert result_a is False
    assert result_b is True
    assert len(manager.pending) == 0

    print("Request A: BLOCKED")
    print("Request B: ALLOWED")
    print("Pending requests: 0")
    print("Concurrency test: PASSED")


if __name__ == "__main__":
    asyncio.run(main())
