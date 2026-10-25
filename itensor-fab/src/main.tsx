import { useEffect, useMemo, useState } from "react";
import {
  BrainCircuit,
  CheckCircle2,
  Cpu,
  MessageSquare,
  Mic,
  Send,
  ShieldAlert,
  Sparkles,
  Terminal,
  XCircle
} from "lucide-react";
import { createRoot } from "react-dom/client";
import "./index.css";

type DieState = "RAW" | "PLANNED" | "READY_FOR_EXECUTOR" | "RECEIPT_CUT" | "FAILED";
type Mode = "chat" | "explain" | "generate";

interface Die {
  id: number;
  state: DieState;
  errorCode?: string;
}

interface BuddyResponse {
  status: "MODEL_RESPONSE" | "ACTION_REQUIRED";
  response: string;
  model: string;
  input_hash: string;
  limitations: string[];
}

interface Capabilities {
  name: string;
  model_configured: boolean;
  language_catalog: { count: number; languages: string[] };
  capabilities: string[];
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function App() {
  const [dies, setDies] = useState<Die[]>(() => Array.from({ length: 64 }, (_, id) => ({ id, state: "RAW" })));
  const [commit, setCommit] = useState("d7f5c8c56eb84375648cbf4597f4cdfee98a6c64");
  const [target, setTarget] = useState("x86_64-unknown-linux-gnu");
  const [runState, setRunState] = useState("READY");
  const [provenanceHash, setProvenanceHash] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [mode, setMode] = useState<Mode>("chat");
  const [language, setLanguage] = useState("Python");
  const [message, setMessage] = useState("Inspect this repository state and tell me what evidence is required before promotion.");
  const [code, setCode] = useState("");
  const [buddyResponse, setBuddyResponse] = useState<BuddyResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [micState, setMicState] = useState("IDLE");

  useEffect(() => {
    void fetch(API_BASE + "/api/buddy/capabilities")
      .then(async (r) => (r.ok ? r.json() : Promise.reject(new Error("capabilities HTTP " + r.status))))
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, []);

  const languages = useMemo(
    () => capabilities?.language_catalog.languages ?? ["Python", "Rust", "C++", "TypeScript"],
    [capabilities]
  );

  async function askBuddy() {
    setBusy(true);
    setBuddyResponse(null);
    try {
      const response = await fetch(API_BASE + "/api/buddy/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message, mode, language, code: code || undefined })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Buddy HTTP " + response.status);
      setBuddyResponse(data);
    } catch (error) {
      setBuddyResponse({
        status: "ACTION_REQUIRED",
        response: error instanceof Error ? error.message : "Buddy request failed closed.",
        model: "UNAVAILABLE",
        input_hash: "",
        limitations: ["No model response is claimed when the backend is unavailable."]
      });
    } finally {
      setBusy(false);
    }
  }

  async function initiateRun() {
    if (!/^[0-9a-f]{40}$/i.test(commit)) {
      setRunState("ACTION_REQUIRED");
      return;
    }
    setBusy(true);
    setProvenanceHash(null);
    setRunState("PREPARING");
    setDies(Array.from({ length: 64 }, (_, id) => ({ id, state: "PLANNED" })));
    try {
      const response = await fetch(API_BASE + "/api/fab/prepare", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ commit, target, die_count: 64 })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Fab HTTP " + response.status);
      setDies(Array.from({ length: 64 }, (_, id) => ({ id, state: "READY_FOR_EXECUTOR" })));
      setRunState(data.status);
      setProvenanceHash(data.provenance_hash);
    } catch {
      setDies(Array.from({ length: 64 }, (_, id) => ({ id, state: "FAILED", errorCode: "iEf-FAB-001" })));
      setRunState("ACTION_REQUIRED");
    } finally {
      setBusy(false);
    }
  }

  async function captureMic() {
    if (!navigator.mediaDevices?.getUserMedia) return;
    setMicState("CAPTURING");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        await fetch(API_BASE + "/api/voice/capture", {
          method: "POST",
          headers: { "content-type": blob.type || "application/octet-stream" },
          body: blob
        });
        setMicState("RECEIVED");
      };
      recorder.start();
      window.setTimeout(() => recorder.stop(), 1800);
    } catch {
      setMicState("ACTION_REQUIRED");
    }
  }

  return (
    <main className="fab-grid min-h-screen px-4 py-6 text-zinc-200 sm:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-col gap-4 border-b border-i-line pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-3 text-sm font-black tracking-[.18em] text-i-water">
              <Cpu className="h-5 w-5" /> iTENSOR FABRICATION PLANT
            </div>
            <h1 className="mt-2 text-3xl font-black tracking-[-.04em] text-white sm:text-5xl">PROCESS → EVIDENCE</h1>
            <p className="mt-2 max-w-3xl text-xs leading-6 text-i-muted">
              Terminal control surface for Buddy, iComp/iTSC evidence, and provenance receipts.
              No simulated receipt is accepted as fabrication evidence.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-i-line bg-black/30 px-3 py-2 text-[10px] font-bold tracking-widest text-i-water">
            <span className="h-2 w-2 animate-pulse rounded-full bg-i-water" /> PROVENANCE ENGINE ONLINE
          </div>
        </header>

        <section className="mt-6 grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
          <div className="glass rounded-3xl p-5 sm:p-7">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-[10px] font-black tracking-[.2em] text-i-muted">WAFER RUN CONTROL</p>
                <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                  <input value={commit} onChange={(e) => setCommit(e.target.value)} className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white" aria-label="Git commit" />
                  <input value={target} onChange={(e) => setTarget(e.target.value)} className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-xs text-white" aria-label="Target" />
                </div>
              </div>
              <button
                onClick={initiateRun}
                disabled={busy}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-i-water px-4 py-3 text-xs font-black tracking-widest text-i-water transition hover:bg-i-water hover:text-black disabled:cursor-wait disabled:opacity-40"
              >
                <Terminal className="h-4 w-4" /> {busy ? "PROCESSING…" : "PREPARE WAFER RUN"}
              </button>
            </div>

            <div className="wafer mx-auto mt-7 aspect-square w-full max-w-[620px] rounded-full border-2 border-i-line p-5 sm:p-10">
              <div className="grid h-full grid-cols-8 content-center gap-1.5 sm:gap-2">
                {dies.map((die) => {
                  const active = die.state === "PLANNED" || die.state === "READY_FOR_EXECUTOR";
                  const failed = die.state === "FAILED";
                  return (
                    <div
                      key={die.id}
                      title={"DIE " + die.id + " · " + die.state + (die.errorCode ? " · " + die.errorCode : "")}
                      className={[
                        "relative aspect-square rounded-[3px] border text-[7px] transition-all",
                        failed ? "border-amber-400/60 bg-amber-400/10 text-amber-300" :
                        active ? "die-active border-i-water/40 bg-i-water/10 text-i-water" :
                        "border-zinc-800 bg-zinc-950 text-zinc-700"
                      ].join(" ")}
                    >
                      <span className="absolute inset-0 flex items-center justify-center">{die.id.toString(16).padStart(2, "0")}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                ["RAW", dies.filter((d) => d.state === "RAW").length],
                ["PLANNED", dies.filter((d) => d.state === "PLANNED").length],
                ["READY", dies.filter((d) => d.state === "READY_FOR_EXECUTOR").length],
                ["FAILED", dies.filter((d) => d.state === "FAILED").length]
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-white/5 bg-black/20 p-3">
                  <p className="text-[9px] font-bold tracking-widest text-i-muted">{label}</p>
                  <p className="mt-1 text-lg font-black text-white">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <aside className="space-y-5">
            <div className="glass rounded-3xl p-5">
              <div className="flex items-center gap-2 text-[10px] font-black tracking-[.2em] text-i-muted">
                <ShieldAlert className="h-4 w-4" /> MASTER PROVENANCE RECEIPT
              </div>
              <div className="mt-4 rounded-2xl border border-i-line bg-black/30 p-4">
                <p className="text-xs font-black tracking-widest text-i-water">{runState}</p>
                <p className="mt-3 break-all text-[11px] leading-5 text-zinc-300">
                  {provenanceHash ?? "NO RECEIPT. A prepared run is not execution evidence."}
                </p>
              </div>
              <p className="mt-3 text-[10px] leading-5 text-i-muted">
                A preparation hash identifies the requested process. It does not claim compilation,
                physical execution, attestation, or silicon fabrication.
              </p>
            </div>

            <div className="glass rounded-3xl p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[10px] font-black tracking-[.2em] text-i-muted">
                  <BrainCircuit className="h-4 w-4" /> BUDDY BRAIN
                </div>
                <span className="text-[9px] font-bold text-i-water">{capabilities?.model_configured ? "MODEL READY" : "ACTION_REQUIRED"}</span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <select value={mode} onChange={(e) => setMode(e.target.value as Mode)} className="rounded-lg border border-white/10 bg-black/40 px-2 py-2 text-[10px] text-white">
                  <option value="chat">CHAT</option>
                  <option value="explain">EXPLAIN</option>
                  <option value="generate">GENERATE</option>
                </select>
                <select value={language} onChange={(e) => setLanguage(e.target.value)} className="rounded-lg border border-white/10 bg-black/40 px-2 py-2 text-[10px] text-white">
                  {languages.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </div>
              <textarea value={message} onChange={(e) => setMessage(e.target.value)} className="mt-2 h-24 w-full resize-none rounded-xl border border-white/10 bg-black/40 p-3 text-xs outline-none focus:border-i-water/60" />
              <textarea value={code} onChange={(e) => setCode(e.target.value)} placeholder="Optional code for Buddy to inspect…" className="mt-2 h-24 w-full resize-none rounded-xl border border-white/10 bg-black/40 p-3 text-xs outline-none focus:border-i-water/60" />
              <div className="mt-2 flex gap-2">
                <button onClick={askBuddy} disabled={busy} className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-i-water bg-i-water/5 px-3 py-2 text-[10px] font-black tracking-widest text-i-water disabled:opacity-40">
                  <Send className="h-3.5 w-3.5" /> ASK BUDDY
                </button>
                <button onClick={captureMic} className="rounded-xl border border-white/10 px-3 py-2 text-i-muted" title="Capture microphone audio">
                  <Mic className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-2 text-[9px] text-i-muted">MIC: {micState} · {capabilities?.language_catalog.count ?? "—"} registered languages</p>
              {buddyResponse && (
                <div className="mt-4 rounded-xl border border-white/10 bg-black/40 p-3">
                  <div className="flex items-center gap-2 text-[9px] font-bold tracking-widest text-i-water">
                    {buddyResponse.status === "MODEL_RESPONSE" ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                    {buddyResponse.status} · {buddyResponse.model}
                  </div>
                  <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-[11px] leading-5 text-zinc-200">{buddyResponse.response}</pre>
                  {buddyResponse.input_hash && <p className="mt-2 break-all text-[8px] text-i-muted">INPUT {buddyResponse.input_hash}</p>}
                </div>
              )}
            </div>
          </aside>
        </section>

        <section className="mt-5 grid gap-5 md:grid-cols-3">
          {[
            [Sparkles, "INTENT", "Buddy receives human intent and produces an auditable model response."],
            [Terminal, "VERIFICATION", "Prepared work advances only when the actual executor and verifier produce evidence."],
            [MessageSquare, "RECEIPT", "The receipt is the evidence surface; it never upgrades a claim beyond its proof."]
          ].map(([Icon, title, body]) => (
            <div key={title as string} className="glass rounded-2xl p-5">
              <Icon className="h-5 w-5 text-i-water" />
              <p className="mt-3 text-xs font-black tracking-widest text-white">{title as string}</p>
              <p className="mt-2 text-[10px] leading-5 text-i-muted">{body as string}</p>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
