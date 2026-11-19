
import queue
import threading


class UIBridge:
    def __init__(self):
        self.requests = queue.Queue()
        self.loop = None
        self.manager = None
        self.backend_ready = threading.Event()
        self.backend_stopped = threading.Event()
        self.finished_requests = queue.Queue()

    def notify_finished(self, request_id):
        self.finished_requests.put(request_id)

    def notify_request(self, request):
        self.requests.put({
            "request_id": request.request_id,
            "tool_name": request.tool_name,
            "arguments": request.arguments,
        })

    def set_backend(self, loop, manager):
        self.loop = loop
        self.manager = manager
        self.backend_ready.set()

    def is_pending(self, request_id):
        # UI reads only a snapshot; manager owns the actual decision.
        if not self.backend_ready.is_set():
            return False

        return request_id in self.manager.pending

    def submit_decision(self, request_id, allowed):
        if not self.backend_ready.is_set():
            return

        if self.loop.is_closed():
            return

        self.loop.call_soon_threadsafe(
            self.manager.resolve,
            request_id,
            allowed,
        )

    def mark_stopped(self):
        self.backend_stopped.set()
