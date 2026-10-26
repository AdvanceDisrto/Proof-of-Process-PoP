"use strict";

const express = require("express");
const { WebSocketServer, WebSocket } = require("ws");
const pty = require("node-pty");
const crypto = require("crypto");
const path = require("path");
const http = require("http");
const { ReceiptChain, sha256 } = require("./receipt-chain");

const PORT = Number(process.env.PORT || 8443);
const HOST = process.env.SOVEREIGN_TERMINAL_HOST || "127.0.0.1";
const HOME = process.env.HOME || process.env.USERPROFILE || process.cwd();
const DATA_DIR = process.env.SOVEREIGN_TERMINAL_DATA || path.join(HOME, ".sovereign-terminal");
const TOKEN = process.env.SOVEREIGN_TERMINAL_TOKEN || "";

function tokenMatches(candidate) {
  if (!TOKEN) return false;
  const a = Buffer.from(sha256(String(candidate)));
  const b = Buffer.from(sha256(TOKEN));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

function createApp() {
  const chain = new ReceiptChain(DATA_DIR);
  const app = express();
  app.use(express.static(path.join(__dirname, "public")));
  app.get("/identity", (_req, res) => {
    res.type("text/plain").send(chain.publicKey.export({ type: "spki", format: "pem" }));
  });
  app.get("/chain/status", (_req, res) => res.json(chain.verify()));

  const server = http.createServer(app);
  const wss = new WebSocketServer({ server, path: "/terminal", maxPayload: 1024 * 1024 });

  wss.on("connection", (ws) => {
    let authenticated = false;
    let shell = null;
    let sessionId = null;
    let inputBuffer = "";
    let outputBuffer = "";

    function send(message) {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
    }

    function spawnShell() {
      sessionId = crypto.randomBytes(16).toString("hex");
      const executable = process.platform === "win32" ? "powershell.exe" : (process.env.SHELL || "bash");
      shell = pty.spawn(executable, [], {
        name: "xterm-256color", cols: 80, rows: 24, cwd: HOME, env: process.env,
      });
      shell.onData((data) => {
        outputBuffer += data;
        send({ type: "output", data });
      });
      shell.onExit(({ exitCode, signal }) => {
        send({ type: "receipt", receipt: chain.append({
          session_id: sessionId,
          event: "SESSION_EXIT",
          exit_code: exitCode,
          signal,
          boundary: "PTY_PROCESS_EXIT",
        }) });
      });
      send({ type: "ready", session_id: sessionId, chain_head: chain.head });
    }

    function recordEnterBoundary() {
      const commandText = inputBuffer.trim();
      if (!commandText) return;
      const receipt = chain.append({
        session_id: sessionId,
        event: "COMMAND_INPUT_BOUNDARY",
        command_text: commandText,
        command_hash: "sha256:" + sha256(Buffer.from(inputBuffer, "utf8")),
        observed_output_before_enter_hash: "sha256:" + sha256(Buffer.from(outputBuffer, "utf8")),
        observed_output_before_enter_bytes: Buffer.byteLength(outputBuffer),
        boundary: "ENTER_DELIMITED_INPUT",
        execution_status: "UNOBSERVED",
        exit_code: null,
        proves: "input bytes were observed at the PTY boundary",
        does_not_prove: "command completion, exit status, or exact command-to-output attribution",
      });
      outputBuffer = "";
      send({ type: "receipt", receipt });
    }

    ws.on("message", (raw) => {
      let message;
      try { message = JSON.parse(raw.toString()); }
      catch { ws.close(4400, "invalid json"); return; }

      if (!authenticated) {
        if (message.type !== "auth" || !tokenMatches(message.token)) {
          send({ type: "error", error: "unauthorized" });
          ws.close(4401, "unauthorized");
          return;
        }
        authenticated = true;
        spawnShell();
        return;
      }

      if (!shell) return;
      if (message.type === "input" && typeof message.data === "string") {
        for (const ch of message.data) {
          if (ch === "\r" || ch === "\n") {
            recordEnterBoundary();
            inputBuffer = "";
          } else if (ch === "\x7f" || ch === "\b") {
            inputBuffer = inputBuffer.slice(0, -1);
          } else if (ch >= " ") {
            inputBuffer += ch;
          }
        }
        shell.write(message.data);
      } else if (message.type === "resize") {
        shell.resize(
          Math.max(20, Math.min(500, Number(message.cols) || 80)),
          Math.max(5, Math.min(300, Number(message.rows) || 24)),
        );
      }
    });

    ws.on("close", () => {
      if (authenticated && sessionId) {
        chain.append({
          session_id: sessionId,
          event: "SESSION_CLOSED",
          observed_unattributed_output_hash: "sha256:" + sha256(Buffer.from(outputBuffer, "utf8")),
          observed_unattributed_output_bytes: Buffer.byteLength(outputBuffer),
          boundary: "CLIENT_DISCONNECTED",
        });
      }
      if (shell) {
        try { shell.kill(); } catch {}
      }
    });
  });

  return { app, server, chain };
}

if (require.main === module) {
  if (!TOKEN) {
    console.error("ACTION_REQUIRED: set SOVEREIGN_TERMINAL_TOKEN before starting.");
    process.exit(2);
  }
  const { server, chain } = createApp();
  server.listen(PORT, HOST, () => {
    console.log("Sovereign Terminal -> http://" + HOST + ":" + PORT);
    console.log("Chain -> " + chain.chainFile);
    console.log("Chain verification -> " + JSON.stringify(chain.verify()));
  });
}

module.exports = { createApp, tokenMatches };
