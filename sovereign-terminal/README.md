# Sovereign Terminal

Mobile-first operator console for the iNNOVULIS machine.

## Proof boundary

The terminal records authenticated PTY observations as an append-only receipt chain.

An Enter-delimited receipt proves that input bytes reached the PTY boundary. It does **not** by itself prove command completion, exit status, or exact command-to-output attribution. Those require an explicit completion protocol.

## Security boundary

- Bind to loopback by default.
- Authenticate before spawning a PTY.
- Keep xterm assets local/offline.
- Put remote access behind a private mesh or authenticated tunnel.
- Verify the existing receipt chain before appending after restart.
- Never promote a failed or unobserved command to VERIFIED_PROCESS.

## Advancement law

Failure stays recorded.
Correction references the failure.
New execution runs the corrected code.
Successful evidence proves the correction.
Only successful evidence advances the chain.
