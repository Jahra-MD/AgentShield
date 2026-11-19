
import asyncio

from agentshield.authorization.manager import (
    AuthorizationManager,
)


async def main():
    manager = AuthorizationManager(timeout=2.0)

    task = asyncio.create_task(
        manager.request_approval(
            tool_name="add_numbers",
            arguments={"a": 10, "b": 20},
        )
    )

    # Let request_approval register its pending request.
    await asyncio.sleep(0)

    request_id = next(iter(manager.pending))

    manager.resolve(request_id, allowed=True)

    result = await task

    print("Approval result:", result)
    print("Pending requests:", len(manager.pending))



async def test_block():
    manager = AuthorizationManager(timeout=2.0)

    task = asyncio.create_task(
        manager.request_approval(
            tool_name="delete_employee",
            arguments={"employee_id": 101},
        )
    )

    await asyncio.sleep(0)

    request_id = next(iter(manager.pending))
    manager.resolve(request_id, allowed=False)

    result = await task

    assert result is False
    assert len(manager.pending) == 0

    print("Block test: PASSED")


async def test_timeout():
    manager = AuthorizationManager(timeout=0.2)

    result = await manager.request_approval(
        tool_name="delete_employee",
        arguments={"employee_id": 101},
    )

    assert result is False
    assert len(manager.pending) == 0

    print("Timeout test: PASSED")


if __name__ == "__main__":
    async def run_tests():
        await main()
        await test_block()
        await test_timeout()

    asyncio.run(run_tests())
