
import asyncio
import sys
import threading
import tkinter as tk
import os
from pathlib import Path

from agentshield.proxy.stdio_proxy import main as proxy_main
from agentshield.ui.approval_popup import ApprovalPopup
from agentshield.ui.bridge import UIBridge



def run_proxy(bridge):
    import threading
    import traceback

    try:
        print(
            f"[AgentShield] Proxy thread started: "
            f"{threading.current_thread().name}",
            file=sys.stderr,
            flush=True,
        )

        asyncio.run(proxy_main(bridge))

    except BaseException:
        print(
            "[AgentShield] Proxy thread crashed:",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc(file=sys.stderr)

    finally:
        print(
            "[AgentShield] Proxy thread exited",
            file=sys.stderr,
            flush=True,
        )



def main():
    project_root = Path(__file__).resolve().parent.parent
    os.chdir(project_root)
    bridge = UIBridge()

    root = tk.Tk()

    popup = ApprovalPopup(
        root,
        on_decision=bridge.submit_decision,
    )

    popup.connect_bridge(bridge)

    proxy_thread = threading.Thread(
        target=run_proxy,
        args=(bridge,),
        daemon=True,
    )

    proxy_thread.start()

    root.mainloop()
    print(
    "[AgentShield] Tkinter mainloop starting",
    file=sys.stderr,
    flush=True,
    )
    print(
    "[AgentShield] Tkinter mainloop exited",
    file=sys.stderr,
    flush=True,
   )


if __name__ == "__main__":
    main()
