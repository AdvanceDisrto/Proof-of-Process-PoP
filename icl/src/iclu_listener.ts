import * as http from "node:http";
import { createHmac, timingSafeEqual } from "node:crypto";
import { spawn } from "node:child_process";

const port = Number.parseInt(process.env.ICL_WEBHOOK_PORT ?? "9000", 10);
const secret = process.env.ICL_WEBHOOK_SECRET;\nconst configPath = process.env.ICL_CONFIG_PATH ?? "icl.yaml";

function verifySignature(body: Buffer, header: string | undefined): boolean {
  if (!secret || !header?.startsWith("sha256=")) return false;
  const expected = createHmac("sha256", secret).update(body).digest();
  const providedHex = header.slice("sha256=".length);
  if (!/^[0-9a-f]{64}$/i.test(providedHex)) return false;
  const provided = Buffer.from(providedHex, "hex");
  return provided.length === expected.length && timingSafeEqual(provided, expected);
}

function triggerPipeline(): void {
  const child = spawn("npm", ["run", "start"], {
    cwd: process.cwd(),
    env: { ...process.env, CI: "true", ICL_CONFIG_PATH: configPath },
    detached: true,
    stdio: "ignore",
  });
  child.unref();
}

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    const memory = process.memoryUsage();
    const healthy = memory.rss <= 1024 * 1024 * 1024;
    const body = JSON.stringify({
      status: healthy ? "HEALTHY" : "DEGRADED_MEMORY",
      uptimeSeconds: process.uptime(),
      memory: {
        rssBytes: memory.rss,
        heapTotalBytes: memory.heapTotal,
        heapUsedBytes: memory.heapUsed,
        externalBytes: memory.external,
      },
    });
    res.writeHead(healthy ? 200 : 503, { "content-type": "application/json" });
    res.end(body);
    return;
  }
  if (req.method === "POST" && req.url === "/icl-webhook") {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer | string) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
    req.on("end", () => {
      const body = Buffer.concat(chunks);
      if (!verifySignature(body, typeof req.headers["x-hub-signature-256"] === "string" ? req.headers["x-hub-signature-256"] : undefined)) {
        res.writeHead(403); res.end("Forbidden"); return;
      }
      res.writeHead(202); res.end("Accepted");
      triggerPipeline();
    });
    return;
  }
  res.writeHead(404); res.end("Not Found");
});

const memoryGuard = setInterval(() => {\n  if (process.memoryUsage().rss > 1024 * 1024 * 1024) {\n    console.error("[iCL] Memory threshold exceeded; exiting for restart policy.");\n    process.exit(78);\n  }\n}, 30_000);\nmemoryGuard.unref();\n\nif (!secret) {
  console.error("[iCL] ICL_WEBHOOK_SECRET is required; refusing to start.");
  process.exitCode = 1;
} else {
  server.listen(port, "0.0.0.0", () => console.log(`[iCL] webhook listener on :${port}`));
}
