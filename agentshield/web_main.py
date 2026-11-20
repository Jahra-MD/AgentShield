
import asyncio
import threading
import tkinter as tk
import traceback
import sys

from agentshield.ui.bridge import UIBridge
from agentshield.ui.approval_popup import ApprovalPopup
from agentshield.proxy.http_gateway import run_http_gateway


def run_server(bridge):
    try:
        asyncio.run(run_http_gateway(bridge))
    except Exception:
        traceback.print_exc(file=sys.stderr)


def main():
    bridge = UIBridge()

    root = tk.Tk()

    popup = ApprovalPopup(
        root,
        on_decision=bridge.submit_decision,
    )

    popup.connect_bridge(bridge)

    server_thread = threading.Thread(
        target=run_server,
        args=(bridge,),
        daemon=True,
    )
    server_thread.start()

    root.mainloop()


if __name__ == "__main__":
    main()
