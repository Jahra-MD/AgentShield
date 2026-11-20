
import hmac
import os


class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

        self.token = os.environ.get("AGENTSHIELD_API_TOKEN")

        if not self.token:
            raise RuntimeError(
                "AGENTSHIELD_API_TOKEN environment variable is required"
            )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))

        authorization = headers.get(b"authorization", b"").decode(
            "latin-1"
        )

        expected = f"Bearer {self.token}"

        if not hmac.compare_digest(authorization, expected):
            body = b"Unauthorized"

            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"content-length", str(len(body)).encode()),
                ],
            })

            await send({
                "type": "http.response.body",
                "body": body,
            })

            return

        await self.app(scope, receive, send)
