import * as fs from "node:fs";
import * as path from "node:path";
import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import * as yaml from "js-yaml";

export interface PipelineStep {
  name: string;
  run: string;
  workingDirectory?: string;
  timeoutSeconds?: number;
}

export interface PipelineJob {
  name: string;
  parallel: boolean;
  steps: PipelineStep[];
  timeoutSeconds?: number;
}

export interface DashboardStorageConfig {
  enabled: boolean;
  endpoint: string;
  bucketName: string;
  region: string;
}

export interface iCLConfig {
  pipeline: { name: string; environment: string };
  dashboard_storage?: DashboardStorageConfig;
  jobs: PipelineJob[];
}

export interface StepOutcome {
  success: boolean;
  exitCode: number | null;
  signal: NodeJS.Signals | null;
  log: string;
  timestamp: string;
  durationMs: number;
}

interface StorageExporter {
  export(jobName: string, stepName: string, outcome: StepOutcome): Promise<void>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readString(value: unknown, label: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(`Invalid ${label}`);
  return value;
}

function readBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw new Error(`Invalid ${label}`);
  return value;
}

function readPositiveInt(value: unknown, label: string, fallback: number): number {
  if (value === undefined) return fallback;
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) throw new Error(`Invalid ${label}`);
  return value;
}

function parseConfig(raw: unknown): iCLConfig {
  if (!isRecord(raw) || !isRecord(raw.pipeline) || !Array.isArray(raw.jobs)) throw new Error("Invalid iCL configuration");
  const pipeline = raw.pipeline;
  const jobs = raw.jobs.map((item, jobIndex): PipelineJob => {
    if (!isRecord(item) || !Array.isArray(item.steps)) throw new Error(`Invalid job at index ${jobIndex}`);
    const steps = item.steps.map((step, stepIndex): PipelineStep => {
      if (!isRecord(step)) throw new Error(`Invalid step at ${jobIndex}/${stepIndex}`);
      return {
        name: readString(step.name, `steps[${jobIndex}][${stepIndex}].name`),
        run: readString(step.run, `steps[${jobIndex}][${stepIndex}].run`),
        workingDirectory: step.workingDirectory === undefined ? undefined : readString(step.workingDirectory, "workingDirectory"),
        timeoutSeconds: readPositiveInt(step.timeoutSeconds, "timeoutSeconds", 900),
      };
    });
    return {
      name: readString(item.name, `jobs[${jobIndex}].name`),
      parallel: readBoolean(item.parallel, `jobs[${jobIndex}].parallel`),
      steps,
      timeoutSeconds: readPositiveInt(item.timeoutSeconds, "job timeoutSeconds", 900),
    };
  });
  const storage = raw.dashboard_storage;
  const dashboard_storage = isRecord(storage) ? {
    enabled: readBoolean(storage.enabled, "dashboard_storage.enabled"),
    endpoint: typeof storage.endpoint === "string" ? storage.endpoint : "",
    bucketName: typeof storage.bucketName === "string" ? storage.bucketName : "",
    region: typeof storage.region === "string" && storage.region.length > 0 ? storage.region : "us-east-1",
  } : undefined;
  return {
    pipeline: {
      name: readString(pipeline.name, "pipeline.name"),
      environment: readString(pipeline.environment, "pipeline.environment"),
    },
    dashboard_storage,
    jobs,
  };
}

class S3LogExporter implements StorageExporter {
  private readonly client: S3Client;
  constructor(private readonly config: DashboardStorageConfig) {
    const accessKeyId = process.env.ICL_STORAGE_KEY_ID;
    const secretAccessKey = process.env.ICL_STORAGE_SECRET;
    if (!accessKeyId || !secretAccessKey) throw new Error("Configured dashboard storage requires ICL_STORAGE_KEY_ID and ICL_STORAGE_SECRET");
    this.client = new S3Client({
      endpoint: config.endpoint,
      region: config.region,
      forcePathStyle: true,
      credentials: { accessKeyId, secretAccessKey },
    });
  }
  async export(jobName: string, stepName: string, outcome: StepOutcome): Promise<void> {
    const key = `logs/${this.config.pipelineName ?? "icl"}/${jobName}/${stepName.replace(/[^a-zA-Z0-9._-]/g, "-").toLowerCase()}-${outcome.timestamp}.json`;
    const payload = JSON.stringify(outcome);
    await this.client.send(new PutObjectCommand({
      Bucket: this.config.bucketName,
      Key: key,
      Body: payload,
      ContentType: "application/json",
    }));
  }
}

class NoopLogExporter implements StorageExporter {
  async export(_jobName: string, _stepName: string, _outcome: StepOutcome): Promise<void> {}
}

export class iCLEngine {
  private readonly exporter: StorageExporter;
  constructor(private readonly configPath: string) {
    const raw = fs.readFileSync(configPath, "utf8");
    this.config = parseConfig(yaml.load(raw));
    const storage = this.config.dashboard_storage;
    this.exporter = storage?.enabled
      ? new S3LogExporter({ ...storage, endpoint: storage.endpoint })
      : new NoopLogExporter();
  }
  private readonly config: iCLConfig;

  private executeStep(jobName: string, step: PipelineStep): Promise<StepOutcome> {
    const started = Date.now();
    const timestamp = new Date().toISOString();
    const cwd = path.resolve(path.dirname(this.configPath), "..", step.workingDirectory ?? ".");
    return new Promise((resolve) => {
      const child = spawn(step.run, { cwd, shell: true, env: { ...process.env, CI: "true" }, detached: true });
      let log = "";
      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stdout.on("data", (chunk: string) => { log += chunk; process.stdout.write(chunk); });
      child.stderr.on("data", (chunk: string) => { log += chunk; process.stderr.write(chunk); });
      const timeout = setTimeout(() => {
        if (child.pid !== undefined) process.kill(-child.pid, "SIGTERM");
      }, (step.timeoutSeconds ?? 900) * 1000);
      child.on("error", (error: Error) => {
        clearTimeout(timeout);
        resolve({ success: false, exitCode: null, signal: null, log: error.message, timestamp, durationMs: Date.now() - started });
      });
      child.on("close", async (code: number | null, signal: NodeJS.Signals | null) => {
        clearTimeout(timeout);
        const outcome: StepOutcome = { success: code === 0, exitCode: code, signal, log, timestamp, durationMs: Date.now() - started };
        try { await this.exporter.export(jobName, step.name, outcome); }
        catch (error: unknown) {
          const message = error instanceof Error ? error.message : String(error);
          outcome.success = false;
          outcome.log += `\n[iCL TRACE EXPORT FAILURE] ${message}\n`;
        }
        resolve(outcome);
      });
    });
  }

  private async runJob(job: PipelineJob): Promise<boolean> {
    const outcomes = job.parallel
      ? await Promise.all(job.steps.map((step) => this.executeStep(job.name, step)))
      : await this.runSequential(job);
    return outcomes.every((outcome) => outcome.success);
  }

  private async runSequential(job: PipelineJob): Promise<StepOutcome[]> {
    const outcomes: StepOutcome[] = [];
    for (const step of job.steps) {
      const outcome = await this.executeStep(job.name, step);
      outcomes.push(outcome);
      if (!outcome.success) break;
    }
    return outcomes;
  }

  async orchestrate(): Promise<number> {
    console.log(`[iCL] ${this.config.pipeline.name} / ${this.config.pipeline.environment}`);
    for (const job of this.config.jobs) {
      console.log(`[iCL JOB] ${job.name}`);
      if (!await this.runJob(job)) {
        console.error(`[iCL FAILED] ${job.name}`);
        return 1;
      }
    }
    console.log("[iCL SUCCESS] All configured jobs passed.");
    return 0;
  }
}

const entry = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (entry === path.resolve(process.cwd(), "dist/icl_engine.js")) {
  const configPath = path.resolve(process.cwd(), "icl.yaml");
  const code = await new iCLEngine(configPath).orchestrate();
  process.exitCode = code;
}
