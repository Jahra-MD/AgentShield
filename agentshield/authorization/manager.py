
import asyncio
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ApprovalRequest:
    request_id: str
    tool_name: str
    arguments: dict
    decision: asyncio.Future = field(repr=False)


class AuthorizationManager:
    def __init__(
        self,
        timeout: float = 30.0,
        on_request=None,
        on_finished=None,
    ):
        self.timeout = timeout
        self.pending: dict[str, ApprovalRequest] = {}
        self.on_request = on_request
        self.on_finished = on_finished


    async def request_approval(
        self,
        tool_name: str,
        arguments: dict,
    ) -> bool:
        loop = asyncio.get_running_loop()

        request = ApprovalRequest(
            request_id=str(uuid4()),
            tool_name=tool_name,
            arguments=arguments,
            decision=loop.create_future(),
        )

        self.pending[request.request_id] = request
        
        if self.on_request is not None:
            self.on_request(request)

        try:
            return await asyncio.wait_for(
                request.decision,
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return False
        finally:
            self.pending.pop(request.request_id, None)
            if self.on_finished is not None:
                self.on_finished(request.request_id)

    def resolve(self, request_id: str, allowed: bool) -> bool:
        request = self.pending.get(request_id)

        if request is None or request.decision.done():
            return False

        request.decision.set_result(allowed)
        return True
