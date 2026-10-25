import { Project, SyntaxKind } from "ts-morph";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

export interface iTSC_Receipt {
  status: "COMPILATION_VERIFIED" | "QUARANTINED";
  codebaseHash: string;
  violations: string[];
  timestamp: number;
}

function hashCodebase(project: Project): string {
  const astHashes = project.getSourceFiles()
    .filter(sourceFile => !sourceFile.getFilePath().includes("node_modules"))
    .map(sourceFile =>
      createHash("sha256").update(sourceFile.getFullText()).digest("hex")
    )
    .sort();
  return createHash("sha256").update(astHashes.join(":")).digest("hex");
}

function strictCompile(projectDir: string): string[] {
  const result = spawnSync("npm", ["run", "compile:strict"], {
    cwd: projectDir,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (result.status === 0) return [];
  return [
    "Strict TypeScript compilation failed.",
    ...(result.stderr || result.stdout || "tsc exited without diagnostics.")
      .trim().split("\n").slice(-40),
  ];
}

export async function compileAndAudit(projectDir: string): Promise<iTSC_Receipt> {
  console.log("🛡️ [iTSC] Initializing iTensor Sovereign Compiler...");
  const violations: string[] = [];
  const project = new Project({
    tsConfigFilePath: path.join(projectDir, "tsconfig.json"),
  });

  violations.push(...strictCompile(projectDir));

  for (const sourceFile of project.getSourceFiles()) {
    const filePath = sourceFile.getFilePath();
    if (filePath.includes("node_modules")) continue;
    const fileName = path.relative(projectDir, filePath);

    const anyNodes = sourceFile.getDescendantsOfKind(SyntaxKind.AnyKeyword);
    if (anyNodes.length > 0) {
      violations.push(`${fileName}: Banned 'any' type found (${anyNodes.length} instances).`);
    }

    sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression).forEach(call => {
      if (call.getExpression().getText() !== "JSON.stringify") return;
      const args = call.getArguments();
      if (args.length > 0 && args[0].getType().isAny()) {
        violations.push(`${fileName}: Unsafe JSON.stringify() on an 'any' type.`);
      }
    });

    sourceFile.getDescendantsOfKind(SyntaxKind.StringLiteral).forEach(literal => {
      const value = literal.getLiteralValue();
      if (value.includes("MOCK-TEE") || value.includes("signatureVerified: true")) {
        violations.push(`${fileName}: Hardcoded mock or bypass detected.`);
      }
    });
  }

  const codebaseHash = hashCodebase(project);
  const receipt: iTSC_Receipt = {
    status: violations.length === 0 ? "COMPILATION_VERIFIED" : "QUARANTINED",
    codebaseHash,
    violations,
    timestamp: Date.now(),
  };

  if (receipt.status === "COMPILATION_VERIFIED") {
    console.log(`✅ [iTSC] 0 Violations. Codebase Hash: ${codebaseHash}`);
  } else {
    console.error("🚨 [iTSC] COMPILATION QUARANTINED:");
    violations.forEach(v => console.error(`  - ${v}`));
  }
  return receipt;
}

const entrypoint = process.argv[1]
  ? path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))
  : false;

if (entrypoint) {
  const projectDir = process.cwd();
  compileAndAudit(projectDir).then(receipt => {
    fs.writeFileSync(
      path.join(projectDir, "itsc-receipt.json"),
      JSON.stringify(receipt, null, 2) + "\n",
    );
    if (receipt.status === "QUARANTINED") process.exitCode = 1;
  }).catch(error => {
    console.error(error);
    process.exitCode = 1;
  });
}
