#!/usr/bin/env python3
"""iRemote Terminal agent: local PTY + authenticated WebSocket transport.

The agent binds to loopback by default. Put it behind a private mesh/tunnel
when remote access is required; do not expose the shell directly to the public
Internet.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import json
import os
import platform
import pty
import secrets
import signal
import struct
import termios
from pathlib import Path

import websockets
from websockets.exceptions import ConnectionClosed

ROOT = Path(__file__).resolve().parent


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_window(fd: int, rows: int, cols: int) -> None:
    rows = max(1, min(int(rows), 1000))
    cols = max(1, min(int(cols), 1000))
    import fcntl
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


async def terminal_session(ws, shell: str) -> None:
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp(shell, [shell, "-l"])

    loop = asyncio.get_running_loop()

    def on_output() -> None:
        try:
            data = os.read(fd, 65536)
        except OSError:
            data = b""
        if not data:
            loop.remove_reader(fd)
            return
        asyncio.create_task(ws.send(data))

    loop.add_reader(fd, on_output)
    try:
        async for message in ws:
            if isinstance(message, bytes):
                os.write(fd, message)
                continue
            try:
                event = json.loads(message)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "input":
                os.write(fd, str(event.get("data", "")).encode())
            elif event.get("type") == "resize":
                set_window(fd, event.get("rows", 24), event.get("cols", 80))
    except ConnectionClosed:
        pass
    finally:
        try:
            loop.remove_reader(fd)
        except Exception:
            pass
        try:
            os.kill(pid, signal.SIGHUP)
        except ProcessLookupError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass


async def authenticate(ws, expected_hash: str) -> bool:
    """Accept native Authorization header or browser first-message auth."""
    auth = ws.request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        supplied = auth.removeprefix("Bearer ").strip()
        return hmac.compare_digest(token_hash(supplied), expected_hash)

    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        if not isinstance(raw, str):
            return False
        event = json.loads(raw)
        if event.get("type") != "auth":
            return False
        supplied = str(event.get("token", ""))
        return hmac.compare_digest(token_hash(supplied), expected_hash)
    except (asyncio.TimeoutError, ConnectionClosed, json.JSONDecodeError):
        return False


async def handler(ws, expected_hash: str, shell: str) -> None:
    if not await authenticate(ws, expected_hash):
        await ws.send(json.dumps({"type": "error", "error": "unauthorized"}))
        await ws.close(code=4401, reason="unauthorized")
        return
    await ws.send(json.dumps({
        "type": "hello",
        "protocol": "IREMOTE-PTY-v1",
        "host": platform.node(),
        "platform": platform.platform(),
        "shell": shell,
    }))
    await terminal_session(ws, shell)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("IREMOTE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("IREMOTE_PORT", "8768")))
    parser.add_argument("--shell", default=os.getenv("IREMOTE_SHELL", os.getenv("SHELL", "/bin/bash")))
    args = parser.parse_args()

    token = os.getenv("IREMOTE_TOKEN") or secrets.token_urlsafe(32)
    expected_hash = token_hash(token)
    print("iRemote Terminal agent")
    print(f"listen: ws://{args.host}:{args.port}/terminal")
    if "IREMOTE_TOKEN" not in os.environ:
        print(f"one-time generated token: {token}")
        print("Set IREMOTE_TOKEN explicitly for persistent pairing.")
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        print("WARNING: non-loopback bind requested; use a private VPN/tunnel and firewall.")

    async with websockets.serve(
        lambda ws: handler(ws, expected_hash, args.shell),
        args.host,
        args.port,
        max_size=2**20,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
