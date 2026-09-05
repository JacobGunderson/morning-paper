from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "work" / "gocomics-chrome"


def browser_is_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9222), timeout=0.2):
            return True
    except OSError:
        return False


def main() -> None:
    configured = os.environ.get("MORNING_PAPER_CHROME")
    candidates = [
        Path(configured) if configured else None,
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ]
    executable = next((path for path in candidates if path and path.is_file()), None)
    if not executable:
        raise SystemExit(
            "Google Chrome was not found. Set MORNING_PAPER_CHROME to its executable path."
        )

    if browser_is_ready():
        print("The dedicated GoComics Chrome window is already ready.")
        return

    PROFILE.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [
            str(executable),
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=9222",
            f"--user-data-dir={PROFILE}",
            "https://www.gocomics.com/",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(40):
        if browser_is_ready():
            print("Opened the dedicated GoComics Chrome window.")
            print("Keep it open, sign in there if needed, then run: npm run refresh:local")
            return
        if process.poll() is not None:
            raise SystemExit(
                "Chrome exited before its local collector connection opened. "
                "Close any old collector Chrome window and run this command again."
            )
        time.sleep(0.25)
    raise SystemExit(
        "Chrome opened, but its local collector connection did not become ready on port 9222."
    )


if __name__ == "__main__":
    main()
