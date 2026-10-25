import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import { createExecutionReceipt } from "./receipt.js";
import { assertLifecycleAllowed, assertPhysicalActuationBlocked } from "./policy.js";

const server = new McpServer({
  name: "compute-control",
  version: "0.1.0",
});

server.registerTool(
  "compute_capabilities",
  {
    description: "Return the provider-neutral Compute Control capability contract.",
    inputSchema: z.object({}),
  },
  async () => ({
    content: [{
      type: "text",
      text: JSON.stringify({
        compute: ["cloud", "gpu", "vm", "container", "bare_metal"],
        ai: ["inference", "model_runtime", "workload_execution"],
        connectivity: ["internet", "cellular", "telecom", "wifi", "bluetooth", "wireless", "ssh"],
        crypto: ["hash", "signature_verification", "anchor_verification"],
        blockchain: ["provider_inspection", "transaction_verification", "anchor_verification"],
        lifecycle: ["create", "start", "stop", "restart", "terminate"],
        evidence: ["PoP_execution_receipt", "hashes", "provenance", "telemetry"],
      }, null, 2),
    }],
  })
);

server.registerTool(
  "authorize_lifecycle",
  {
    description: "Policy-check an instance lifecycle operation before provider execution.",
    inputSchema: z.object({
      action: z.enum(["create", "start", "stop", "restart", "terminate"]),
    }),
  },
  async ({ action }) => {
    try {
      assertLifecycleAllowed(action);
      return { content: [{ type: "text", text: JSON.stringify({ state: "AUTHORIZED", action }) }] };
    } catch (error) {
      return { content: [{ type: "text", text: JSON.stringify({ state: "ACTION_REQUIRED", action, reason: String(error) }) }] };
    }
  }
);

server.registerTool(
  "create_pop_execution_receipt",
  {
    description: "Bind a workload execution result to a PoP evidence receipt.",
    inputSchema: z.object({
      provider: z.string().min(1),
      resourceId: z.string().min(1),
      kind: z.string().min(1),
      operation: z.string().min(1),
      command: z.string().min(1),
      gitCommit: z.string().optional(),
      exitCode: z.number().int(),
      stdoutHash: z.string().min(1),
      stderrHash: z.string().min(1),
      artifactHashes: z.array(z.string()),
      externalAnchor: z.string().optional(),
    }),
  },
  async (input) => {
    const receipt = createExecutionReceipt(
      input.operation,
      { provider: input.provider, resourceId: input.resourceId, kind: input.kind as never },
      { name: input.operation, command: input.command, gitCommit: input.gitCommit },
      {
        exitCode: input.exitCode,
        startedAt: new Date().toISOString(),
        endedAt: new Date().toISOString(),
        stdoutHash: input.stdoutHash,
        stderrHash: input.stderrHash,
        artifactHashes: input.artifactHashes,
      },
      input.externalAnchor,
    );
    return { content: [{ type: "text", text: JSON.stringify(receipt, null, 2) }] };
  }
);

server.registerTool(
  "physical_actuation_policy",
  {
    description: "Report the Compute Control MCP physical-actuation boundary.",
    inputSchema: z.object({}),
  },
  async () => {
    try {
      assertPhysicalActuationBlocked();
      return { content: [{ type: "text", text: JSON.stringify({ state: "ACTION_REQUIRED" }) }] };
    } catch (error) {
      return { content: [{ type: "text", text: JSON.stringify({ state: "ACTION_REQUIRED", reason: String(error) }) }] };
    }
  }
);

void serveStdio(() => server);
console.error("Compute Control MCP running on stdio");
