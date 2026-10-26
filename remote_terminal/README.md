# i™ Remote Terminal

A mobile-first terminal surface for running Bash or another configured shell on a machine you control.

## Architecture

Phone / tablet / browser -> authenticated WebSocket -> local PTY agent -> Bash/Zsh/other shell.

The agent binds to `127.0.0.1:8768` by default. Keep it loopback-only and put it behind your existing private network/tunnel when remote access is needed. Do not expose the PTY directly to the public Internet.

## Install

```bash
python -m pip install websockets
export IREMOTE_TOKEN='replace-with-a-long-random-secret'
python remote_terminal/agent.py
```

Serve `remote_terminal/web` from the same machine using your existing PWA/static server. Vendor xterm.js locally at:

- `remote_terminal/web/vendor/xterm.js`
- `remote_terminal/web/vendor/xterm.css`

No CDN dependency is required or intended.

## Security boundary

- The token is an authentication capability, not a hardware-backed iKey.
- The PTY agent performs arbitrary commands with the operating-system permissions of the account that starts it.
- Default bind is loopback.
- Use a private mesh/VPN or authenticated tunnel for cross-device transport.
- Do not place private keys, seed phrases, or long-lived secrets in terminal history.
- Production hardening still needs origin checks, rate limiting, token rotation/pairing, TLS termination, session audit receipts, and OS sandboxing.

## Mobile controls

The PWA includes touch keys for Escape, Tab, Ctrl-C/D/Z, arrows, pipe, and tilde. It sends resize events to the PTY so interactive programs can adapt to the viewport.
