
import json
import tkinter as tk
from tkinter import ttk
import queue


class ApprovalPopup:

    def __init__(self, root, on_decision):
        self.root = root
        self.on_decision = on_decision
        self.bridge = None

        self.current_request_id = None
        self.waiting_requests = []
        self.pending_requests = queue.Queue()

        self.root.title("AgentShield")
        self.root.geometry("440x320")
        self.root.resizable(False, False)

        # Keep the popup above other windows when displayed.
        self.root.attributes("-topmost", True)

        # Clicking X should block the active request,
        # not terminate the application.
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close,
        )

        self.tool_label = ttk.Label(
            root,
            text="Waiting for tool request...",
            font=("Segoe UI", 12, "bold"),
        )
        self.tool_label.pack(pady=15)

        self.arguments_text = tk.Text(
            root,
            height=7,
            width=48,
            state="disabled",
        )
        self.arguments_text.pack(
            padx=15,
            pady=10,
        )

        button_frame = ttk.Frame(root)
        button_frame.pack(pady=10)

        self.block_button = ttk.Button(
            button_frame,
            text="Block",
            command=lambda: self.decide(False),
        )
        self.block_button.pack(
            side="left",
            padx=10,
        )

        self.allow_button = ttk.Button(
            button_frame,
            text="Allow",
            command=lambda: self.decide(True),
        )
        self.allow_button.pack(
            side="left",
            padx=10,
        )

        self.set_buttons_enabled(False)

        # Start hidden. The Tkinter mainloop remains alive.
        self.root.withdraw()

    def connect_bridge(self, bridge):
        self.bridge = bridge
        self.root.after(100, self.check_requests)

    def check_requests(self):
        if self.bridge is None:
            return

        # Receive newly requested authorizations.
        try:
            while True:
                request = self.bridge.requests.get_nowait()

                self.waiting_requests.append(request)

        except queue.Empty:
            pass

        # Remove requests already completed or timed out.
        try:
            while True:
                finished_id = (
                    self.bridge.finished_requests.get_nowait()
                )

                self.waiting_requests = [
                    request
                    for request in self.waiting_requests
                    if request["request_id"] != finished_id
                ]

                if self.current_request_id == finished_id:
                    self.current_request_id = None
                    self.reset_display()
                    self.root.withdraw()

        except queue.Empty:
            pass

        # Show the next pending authorization.
        if self.current_request_id is None:
            self.show_next_request()

        self.root.after(100, self.check_requests)

    def show_next_request(self):
        if self.current_request_id is not None:
            return

        if not self.waiting_requests:
            self.root.withdraw()
            return

        request = self.waiting_requests.pop(0)

        self.show_request(
            request_id=request["request_id"],
            tool_name=request["tool_name"],
            arguments=request["arguments"],
        )

    def set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"

        self.allow_button.configure(state=state)
        self.block_button.configure(state=state)

    def show_request(
        self,
        request_id,
        tool_name,
        arguments,
    ):
        self.current_request_id = request_id

        self.tool_label.configure(
            text=f"Tool: {tool_name}"
        )

        self.arguments_text.configure(state="normal")
        self.arguments_text.delete("1.0", tk.END)

        self.arguments_text.insert(
            tk.END,
            json.dumps(
                arguments,
                indent=2,
                default=str,
            ),
        )

        self.arguments_text.configure(state="disabled")

        self.set_buttons_enabled(True)

        # Display the popup only when approval is needed.
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()

    def reset_display(self):
        self.set_buttons_enabled(False)

        self.tool_label.configure(
            text="Waiting for tool request..."
        )

        self.arguments_text.configure(state="normal")
        self.arguments_text.delete("1.0", tk.END)
        self.arguments_text.configure(state="disabled")

    def decide(self, allowed):
        if self.current_request_id is None:
            return

        request_id = self.current_request_id
        self.current_request_id = None

        self.reset_display()

        # Hide the popup, but keep AgentShield alive.
        self.root.withdraw()

        # Notify the authorization manager.
        self.on_decision(request_id, allowed)

        # If another request is waiting, display it.
        self.show_next_request()

    def on_close(self):
        # Treat closing the popup as a Block decision.
        if self.current_request_id is not None:
            self.decide(False)
        else:
            self.root.withdraw()


if __name__ == "__main__":
    root = tk.Tk()

    def print_decision(request_id, allowed):
        print(
            "Decision:",
            request_id,
            allowed,
        )

    popup = ApprovalPopup(
        root,
        print_decision,
    )

    # Demonstration request.
    root.after(
        1000,
        lambda: popup.show_request(
            request_id="demo-001",
            tool_name="add_numbers",
            arguments={
                "a": 10,
                "b": 20,
            },
        ),
    )

    root.mainloop()
