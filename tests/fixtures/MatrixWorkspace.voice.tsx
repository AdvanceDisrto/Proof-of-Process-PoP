import { useEffect, useRef, useState } from "react";
import "./matrix.css";
import MatrixTunnel from "./MatrixTunnel";
import { useKrdidIdentity } from "./KrdidIdentity";
import NuPrintPanel from "./NuPrintPanel";

const API = (import.meta.env.VITE_IGPT_EDGE_API_BASE || "https://igptm-matrix-api.innovulis-i-edge.workers.dev").replace(/\/$/, "");
// Opt-in isolated test Worker. Default remains the existing production Matrix API.
const BUDDY_PREVIEW = (import.meta.env.VITE_BUDDY_PREVIEW_URL || "").trim();
const BUDDY_CHAT_ENDPOINT = BUDDY_PREVIEW || API + "/api/buddy/chat";
type View = "buddy" | "build" | "verify" | "market" | "imine" | "evidence";
type ChatMessage = { role: "user" | "assistant"; content: string; source?: string };
type MarketQuote = { symbol: string; price_usd: number; source: string; observed_at: string };
type NewsItem = { title: string; url: string; source: string; published_at: string | null };
type CihHealth = { service: string; status: string; auth_configured: boolean; auth_provider?: string; krdid_enrolled_count?: number; signer_configured: boolean; trusted_key_configured: boolean; storage_configured: boolean; storage_provider?: string; remote_replica_configured?: boolean; remote_replica_pending_count?: number; remote_replica_acknowledged_count?: number; independent_truth_engine: string; hardware_attestation: string };
type IssuedReceipt = { body: Record<string, unknown>; body_sha256: string; signature_b64: string; key_id: string; storage_status: string; remote_replication_status?: string };
type LocalArtifact = { format: string; payload: { artifact_id: string; name: string; kind: string; intent: string; created_at: string; stage: string }; sha256: string; assurance: string; does_not_prove: string[] };
type Evidence = { label: string; status: "PASS" | "HOLD" | "LOCAL" | "REVOKED"; at: string; detail: string };
const nav: Array<{ id: View; icon: string; label: string }> = [
  { id: "buddy", icon: "✳", label: "Buddy" }, { id: "build", icon: "⌘", label: "Create" },
  { id: "verify", icon: "◇", label: "Verify" }, { id: "market", icon: "↗", label: "Markets" },
  { id: "imine", icon: "⛨", label: "iMINE" }, { id: "evidence", icon: "▤", label: "Evidence" },
];
const sequence = ["IDENTITY", "CONTRACT", "GENERATION", "VERIFICATION", "RECEIPT"];
const initialChat: ChatMessage[] = [{ role: "assistant", content: "Welcome to i™ ARTIFACTGPTm™. I’m Buddy. Ask a question, create an artifact, or inspect a receipt. I will show what was executed and what is still unverified.", source: "INTRODUCTION · LOCAL" }];

function hex(bytes: ArrayBuffer): string {
  return Array.from(new Uint8Array(bytes)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
async function hash(value: string): Promise<string> {
  return hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
}
function short(value: string) { return value.length > 22 ? value.slice(0, 14) + "…" + value.slice(-6) : value; }
function canonicalJSON(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(canonicalJSON).join(",") + "]";
  const dict = value as Record<string, unknown>;
  return "{" + Object.keys(dict).sort().map((key) => JSON.stringify(key) + ":" + canonicalJSON(dict[key])).join(",") + "}";
}
function now() { return new Date().toISOString(); }
function stamp(value: string) {
  try { return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); } catch { return value; }
}

export default function MatrixWorkspace() {
  const identity = useKrdidIdentity();
  const [view, setView] = useState<View>("buddy");
  const [matrixMotion, setMatrixMotion] = useState(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
    try { return window.localStorage.getItem("i-matrix-motion") !== "paused"; }
    catch { return true; }
  });
  const [matrixSpeed, setMatrixSpeed] = useState<"drift" | "flow" | "warp">("flow");
  const toggleMatrix = () => setMatrixMotion((enabled) => {
    try { window.localStorage.setItem("i-matrix-motion", enabled ? "paused" : "playing"); } catch { /* storage may be disabled */ }
    return !enabled;
  });
  const [chat, setChat] = useState<ChatMessage[]>(initialChat);
  const [query, setQuery] = useState("");
  const [thinking, setThinking] = useState(false);
  const sendingRef = useRef(false);
  const [listening, setListening] = useState(false);
  const [spokenReplies, setSpokenReplies] = useState(() => {
    // User preference: speech enabled by default, microphone remains OFF until clicked.
    // Browsers may require a separate user gesture before actual playback.
    try { return window.localStorage.getItem("i-buddy-spoken-replies") !== "off"; }
    catch { return true; }
  });
  const spokenRepliesRef = useRef(spokenReplies);
  const recognitionRef = useRef<any>(null);
  const [utcClock, setUtcClock] = useState(() => now());
  const [headlines, setHeadlines] = useState<NewsItem[]>([]);
  const [newsState, setNewsState] = useState("CHECKING REAL NEWS");
  const [artifactName, setArtifactName] = useState("i™ Modular Computing Contract");
  const [artifactKind, setArtifactKind] = useState("DESIGN");
  const [intent, setIntent] = useState("Define an interoperable module with a verifiable input/output contract and clear evidence boundaries.");
  const [artifact, setArtifact] = useState<LocalArtifact | null>(null);
  const [localRevoked, setLocalRevoked] = useState(false);
  const [verified, setVerified] = useState("");
  const [rawReceipt, setRawReceipt] = useState("");
  const [cihHealth, setCihHealth] = useState<CihHealth | null>(null);
  const [cihHealthStatus, setCihHealthStatus] = useState("CHECKING CIH");
  const [cihIssuing, setCihIssuing] = useState(false);
  const [issuedReceipt, setIssuedReceipt] = useState<IssuedReceipt | null>(null);
  const [quotes, setQuotes] = useState<MarketQuote[]>([]);
  const [marketState, setMarketState] = useState("CHECKING SOURCE");
  const [apiState, setApiState] = useState("CHECKING");
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [statusMessage, setStatusMessage] = useState("All actions require evidence. External execution is off until authorized.");
  const endRef = useRef<HTMLDivElement>(null);

  function record(label: string, status: Evidence["status"], detail: string) {
    setEvidence((rows) => [{ label, status, at: now(), detail }, ...rows].slice(0, 18));
  }

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [chat]);
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await fetch(API + "/api/cih/health", { cache: "no-store" });
        if (!res.ok) throw new Error("CIH health unavailable");
        const state = await res.json() as CihHealth;
        if (!active) return;
        setCihHealth(state);
        setCihHealthStatus(state.status === "RUNNING" ? "CIH BACKEND REACHABLE" : "CIH BACKEND NOT READY");
      } catch {
        if (active) { setCihHealth(null); setCihHealthStatus("CIH BACKEND UNAVAILABLE"); }
      }
    };
    void load();
    const timer = window.setInterval(() => { void load(); }, 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  useEffect(() => { const id = window.setInterval(() => setUtcClock(now()), 1000); return () => window.clearInterval(id); }, []);
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const response = await fetch(API + "/api/news", { cache: "no-store" });
        if (!response.ok) throw new Error("NEWS_UNAVAILABLE");
        const data = await response.json() as { headlines?: NewsItem[] };
        if (!mounted) return;
        const valid = (data.headlines || []).filter(n => !!n.title && /^https:\/\//.test(n.url));
        setHeadlines(valid);
        setNewsState(valid.length ? "REAL HEADLINES · 5 MIN" : "NO LIVE HEADLINES");
      } catch { if(mounted) { setHeadlines([]); setNewsState("NEWS PROVIDER UNAVAILABLE"); } }
    };
    void load();
    const id = window.setInterval(() => void load(), 300000);
    return () => { mounted = false; window.clearInterval(id); };
  }, []);
  useEffect(() => () => { try { recognitionRef.current?.abort(); } catch { /* unsupported */ } window.speechSynthesis?.cancel(); }, []);
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const response = await fetch(API + "/api/status", { cache: "no-store" });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const obj = await response.json();
        if (mounted) setApiState(obj?.service === "igptm-matrix-edge" ? "EDGE REACHABLE" : "UNEXPECTED API");
      } catch { if (mounted) setApiState("EDGE UNAVAILABLE"); }
    };
    void load();
    return () => { mounted = false; };
  }, []);
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const response = await fetch(API + "/api/market", { cache: "no-store" });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const obj = await response.json() as { quotes?: MarketQuote[] };
        if (!mounted) return;
        const ok = (obj.quotes || []).filter((q) => Number.isFinite(q.price_usd) && q.price_usd > 0);
        setQuotes(ok);
        setMarketState(ok.length ? "LIVE SOURCE · 60s REFRESH" : "NO VERIFIED QUOTES");
      } catch {
        if (mounted) { setQuotes([]); setMarketState("FEED UNAVAILABLE · NO SIMULATED PRICES"); }
      }
    };
    void load();
    const id = window.setInterval(() => { void load(); }, 60_000);
    return () => { mounted = false; window.clearInterval(id); };
  }, []);

  function speak(text: string) {
    if (!spokenRepliesRef.current || !("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") return;
    try {
      window.speechSynthesis.cancel();
      const speech = new SpeechSynthesisUtterance(text.slice(0, 900));
      speech.lang = "en-US";
      speech.pitch = 0.9;
      speech.rate = 1.05;
      speech.onerror = () => setStatusMessage("Spoken playback was blocked or unavailable. The complete response remains readable.");
      window.speechSynthesis.speak(speech);
    } catch {
      setStatusMessage("Spoken playback unavailable. Text reply is still available.");
    }
  }
  async function send(voiceMessage?: string) {
    const message = (voiceMessage ?? query).trim();
    if (!message || thinking || sendingRef.current || message.length > 1500) return;
    sendingRef.current = true;
    setQuery("");
    setChat((x) => [...x, { role: "user", content: message }]);
    setThinking(true);
    try {
      const lower = message.toLowerCase();
      if (/\b(news|headlines)\b/.test(lower)) {
        const answer = headlines.length ? "Latest indexed headlines:\n" + headlines.slice(0,4).map((n,i) => (i+1)+". "+n.title+" — "+n.source).join("\n") + "\nThese are publisher headlines, not proof of truth. See linked sources in Global Intel." : "Live headlines unavailable. I won't fabricate news.";
        setChat(x => [...x, { role: "assistant", content: answer, source: headlines.length ? "PUBLIC ARTICLE INDEX" : "HOLD · NEWS UNAVAILABLE" }]);
        record("Global Intel", headlines.length ? "PASS" : "HOLD", "Actual source index; not independently verified");
        speak(answer); return;
      }
      if (/\b(btc|bitcoin)\b/.test(lower) && /\b(price|market|quote|cost)\b/.test(lower)) {
        const q = quotes.find(x => x.symbol === "BTC");
        const answer = q ? "Coinbase Bitcoin spot quote is $" + q.price_usd.toLocaleString("en-US") + " USD, retrieved " + q.observed_at + ". Indicative, not an execution quote." : "Bitcoin spot quote unavailable. No price invented.";
        setChat(x => [...x, { role: "assistant", content: answer, source: q ? "COINBASE SPOT" : "HOLD · NO LIVE QUOTE" }]);
        record("Bitcoin quote", q ? "PASS" : "HOLD", q ? "Coinbase spot source-bound" : "Unavailable");
        speak(answer); return;
      }
      const abort = new AbortController();
      const limit = window.setTimeout(() => abort.abort(), 25_000);
      let response: Response;
      try {
        response = await fetch(BUDDY_CHAT_ENDPOINT, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ message, history: chat.slice(-8).map(({ role, content }) => ({ role, content })) }),
          signal: abort.signal, cache: "no-store",
        });
      } finally {
        window.clearTimeout(limit);
      }
      const body = await response.json() as {
        reply?: string; model?: string | null; source?: string;
        error?: string; external_action?: string; llm_called?: boolean;
        clock_source?: string; receipt_issued?: boolean;
      };
      if (!response.ok || typeof body.reply !== "string" || !body.reply.trim()) {
        throw new Error(body.error || "BUDDY_INFERENCE_UNAVAILABLE");
      }
      const isDeterministic = body.llm_called === false &&
        ["EDGE_SYSTEM_CLOCK", "DETERMINISTIC_BUDDY_IDENTITY",
          "DETERMINISTIC_VOICE_CAPABILITY", "DETERMINISTIC_CAPABILITIES"].includes(body.source || "");
      const attribution = isDeterministic
        ? "DETERMINISTIC · " + body.source
        : body.llm_called === true ? "MODEL OUTPUT · UNVERIFIED · " + (body.model || "UNREPORTED")
        : "UPSTREAM RESPONSE · EXECUTION UNCONFIRMED";
      setChat((x) => [...x, { role: "assistant", content: body.reply!, source: attribution }]);
      record(isDeterministic ? "Buddy deterministic response" : "Buddy inference",
        isDeterministic || body.llm_called === true ? "PASS" : "HOLD",
        isDeterministic ? "Backend deterministic scope. No LLM, CIH signing or physical operation." :
          "Model text returned; source claims and factual correctness not independently verified.");
      speak(body.reply);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "BUDDY_INFERENCE_UNAVAILABLE";
      const isIdentity = /^(?:who are you|what are you|what is your name|what's your name|are you apple)[?.! ]*$/i.test(message);
      const fallback = isIdentity
        ? "I am Buddy™, the iNNOVULIS™ Matrix interface. This identity statement comes from the local interface; the remote inference service did not respond."
        : "Buddy's inference service did not return an answer. No model reasoning or external action was completed. You can still use the local artifact and verification controls, or try your question again.";
      setChat((x) => [...x, {
        role: "assistant", content: fallback,
        source: isIdentity ? "LOCAL UI DECLARATION · REMOTE INFERENCE UNAVAILABLE" : "HOLD · NO MODEL RESULT",
      }]);
      record("Buddy inference", "HOLD", "Fail-closed: " + detail);
      speak(fallback);
    } finally { sendingRef.current = false; setThinking(false); }
  }

  function microphone() {
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      setStatusMessage("Microphone stopped by user.");
      return;
    }
    const Ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!window.isSecureContext || !Ctor) {
      setStatusMessage("Speech recognition unsupported or insecure origin. Use text input.");
      return;
    }
    const recognition = new Ctor();
    recognitionRef.current = recognition;
    let sent = false; // Some browsers emit the final result more than once.
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => {
      setListening(true);
      setStatusMessage("Browser microphone session active with permission. One utterance; no background listening.");
    };
    recognition.onend = () => {
      setListening(false);
      if (recognitionRef.current === recognition) recognitionRef.current = null;
    };
    recognition.onerror = (event: any) => {
      setListening(false);
      const cause = typeof event?.error === "string" ? event.error : "interrupted";
      setStatusMessage("Speech recognition unavailable: " + cause + ". Text input remains available.");
    };
    recognition.onresult = (event: any) => {
      if (sent) return;
      const transcript = Array.from(event.results || [])
        .filter((r: any) => r.isFinal)
        .map((r: any) => r[0]?.transcript || "").join(" ").trim();
      if (!transcript) return;
      sent = true;
      setQuery(transcript);
      setStatusMessage("Speech transcribed by the browser; transcript is not a verified microphone attestation.");
      recognition.stop();
      void send(transcript);
    };
    try { recognition.start(); }
    catch {
      recognitionRef.current = null;
      setStatusMessage("Microphone could not start. Check browser support and microphone permission.");
    }
  }
  function toggleSpokenReplies() {
    if (!("speechSynthesis" in window) || typeof SpeechSynthesisUtterance === "undefined") {
      setStatusMessage("Speech synthesis unsupported in this browser. Text works.");
      return;
    }
    const next = !spokenReplies;
    spokenRepliesRef.current = next;
    setSpokenReplies(next);
    try { window.localStorage.setItem("i-buddy-spoken-replies", next ? "on" : "off"); } catch { /* optional */ }
    if (!next) {
      window.speechSynthesis.cancel();
      setStatusMessage("Spoken replies disabled. Microphone is independent and remains off until clicked.");
    } else {
      setStatusMessage("Spoken replies enabled. Actual playback depends on browser audio permissions.");
      try {
        const greeting = new SpeechSynthesisUtterance("Buddy voice is enabled. Just ask Buddy.");
        greeting.pitch = 0.9;
        window.speechSynthesis.speak(greeting);
      } catch { setStatusMessage("Voice enabled, but browser audio playback could not start."); }
    }
  }

  async function createLocalArtifact() {
    if (!artifactName.trim() || !intent.trim()) { setStatusMessage("Artifact name and intent are required."); return; }
    const payload: LocalArtifact["payload"] = {
      artifact_id: crypto.randomUUID(), name: artifactName.trim().slice(0, 120),
      kind: artifactKind, intent: intent.trim().slice(0, 5000),
      created_at: now(), stage: "GENERATION",
    };
    const sha256 = await hash(JSON.stringify(payload));
    const result: LocalArtifact = {
      format: "i-artifact-local-v1", payload, sha256,
      assurance: "GENERATED_LOCAL_UNSIGNED",
      does_not_prove: ["independent correctness", "trusted signer authorization", "physical execution", "deployment or certification"],
    };
    setArtifact(result);
    setLocalRevoked(false);
    setVerified("LOCAL HASH CREATED · NOT SIGNED");
    record("Artifact generated", "LOCAL", sha256);
    setStatusMessage("A real local SHA-256 artifact digest was generated. Signed receipt and independent verification remain HOLD.");
  }

  function downloadArtifact() {
    if (!artifact) return;
    const blob = new Blob([JSON.stringify(artifact, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "i-artifact-" + artifact.payload.artifact_id + ".json"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
  }

  async function verifyLocal() {
    try {
      const candidate = rawReceipt.trim() ? JSON.parse(rawReceipt) : artifact;
      if (!candidate?.payload || typeof candidate.sha256 !== "string" || candidate.format !== "i-artifact-local-v1") throw new Error("Unsupported local artifact format");
      const digest = await hash(JSON.stringify(candidate.payload));
      const ok = digest === candidate.sha256 && /^[a-f0-9]{64}$/i.test(candidate.sha256);
      const message = ok ? "LOCAL DIGEST MATCH · NO SIGNATURE VERIFIED" : "HASH MISMATCH · ARTIFACT MODIFIED";
      setVerified(message);
      record("Local digest comparison", ok ? "LOCAL" : "HOLD", message + " · " + short(digest));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid JSON";
      setVerified("VERIFICATION REJECTED · " + message);
      record("Local digest comparison", "HOLD", message);
    }
  }

  async function issueAuthenticatedReceipt() {
    if (!identity.hasLocalKey || !artifact || cihIssuing) {
      setStatusMessage("Local .krdid key and an artifact are required. Node enrollment must be verified separately.");
      return;
    }
    setCihIssuing(true);
    try {
      const evidence = { artifact_id: artifact.payload.artifact_id, artifact_sha256: artifact.sha256, kind: artifact.payload.kind };
      const payload = {
        claim: "Submitted artifact metadata matched the caller-supplied SHA-256 evidence digest",
        evidence,
        expected_evidence_sha256: await hash(canonicalJSON(evidence)),
        source_id: "artifactgptm-matrix-ui",
        parent_receipt_hashes: [] as string[],
      };
      const signedHeaders = await identity.signRequest(payload, "/api/v1/receipts");
      const response = await fetch(API + "/api/cih/receipts", {
        method: "POST",
        headers: { "content-type": "application/json", ...signedHeaders },
        body: JSON.stringify(payload),
      });
      const body = await response.json() as IssuedReceipt & { error?: string; detail?: string };
      if (!response.ok || !body.body_sha256 || !body.signature_b64) throw new Error(body.detail || body.error || "CIH issuance refused: HTTP " + response.status);
      setIssuedReceipt(body);
      setRawReceipt(JSON.stringify(body, null, 2));
      setVerified("ISSUED BY CIH · SIGNATURE NOT INDEPENDENTLY VERIFIED");
      const mirror = body.remote_replication_status || "NOT_CONFIGURED";
      setStatusMessage(body.storage_status === "LOCAL_SQLITE_COMMITTED"
        ? "CIH signed and committed the local receipt. Remote replica: " + mirror +
          ". This does not certify factual truth, hardware execution or independent consensus."
        : "CIH returned a signed receipt, but local persistence is NOT confirmed: " + (body.storage_status || "UNKNOWN"));
      record("CIH signed receipt returned", body.storage_status === "LOCAL_SQLITE_COMMITTED" ? "PASS" : "HOLD",
        "Signed integrity receipt returned; storage: " + (body.storage_status || "UNKNOWN"));
    } catch (error) {
      const message = error instanceof Error ? error.message : "CIH refused issuance";
      setStatusMessage("RECEIPT ISSUANCE BLOCKED: " + message);
      record("CIH receipt issuance", "HOLD", message);
    } finally { setCihIssuing(false); }
  }

  async function verifySigned() {
    if (!rawReceipt.trim()) { setVerified("SIGNED RECEIPT JSON REQUIRED"); return; }
    setVerified("VERIFYING TRUST-PINNED SIGNATURE…");
    try {
      const input = JSON.parse(rawReceipt);
      const response = await fetch(API + "/api/receipts/verify", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(input) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || ("HTTP " + response.status));
      setVerified(JSON.stringify(data, null, 2));
      record("Remote receipt verifier", data.integrity_valid === true ? "PASS" : "HOLD", "Verifier response received; signature result: " + (data.status || "UNKNOWN") + ". Does not prove claim truth.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      setVerified("SIGNED VERIFICATION HOLD · " + message);
      record("Remote receipt verifier", "HOLD", message);
    }
  }

  const revokeLocal = () => {
    if (!artifact) { setStatusMessage("Generate a local artifact before simulating quarantine."); return; }
    setLocalRevoked(true);
    record("iMINE policy simulation", "REVOKED", "Local view quarantined; zero data destroyed, zero tokens burned, zero hardware commands.");
    setStatusMessage("Local policy marked the draft as quarantined. No global DAG revocation, deletion, physical action, or funds movement occurred.");
  };

  const activeStage = artifact ? 3 : 1;
  return <main className="matrix-app">
    <MatrixTunnel active={matrixMotion} speed={matrixSpeed} />
    <div className="matrix-aurora" aria-hidden="true" />
    <header className="matrix-top">
      <div className="matrix-brand"><span className="matrix-brand-mark">i<sup>™</sup></span><span><strong>ARTIFACTGPTm<sup>™</sup></strong><small>POWERED BY THE i™ ECOSYSTEM</small></span></div>
      <div className="matrix-top-center"><span className="pulse-point" /> <span>HETEROGENEOUS INTELLIGENCE FABRIC</span></div>
      <div className="matrix-top-right"><time className="matrix-utc-clock" dateTime={utcClock}>{utcClock.replace("T", " ").slice(0, 19)} UTC</time><span className={"api-indicator " + (apiState === "EDGE REACHABLE" ? "ready" : "pending")}>{apiState}</span><a href="https://innovulis.com" rel="noreferrer" target="_blank">iNNOVULIS ↗</a></div>
    </header>

    <div className="matrix-layout">
      <aside className="matrix-sidebar matrix-glass">
        <div className="matrix-side-label">THE INTELLIGENCE WORKSPACE <span>01 / 05</span></div>
        <nav aria-label="Main workspace">
          {nav.map((item) => <button className={"matrix-nav " + (view === item.id ? "selected" : "")} key={item.id} onClick={() => setView(item.id)}><span>{item.icon}</span>{item.label}<b>{view === item.id ? "↗" : ""}</b></button>)}
        </nav>
        <div className="matrix-side-separator" />
        <div className="matrix-side-label">EXISTING i™ CAPABILITIES</div>
        <a href="#workspace" className="matrix-nav">⌗ <span>Full i™ Workspace</span> ↗</a>
        <a href="#agents" className="matrix-nav">⊞ <span>Agent Registry</span> ↗</a>
        <a href="#artifacts" className="matrix-nav">◇ <span>Artifact Compiler</span> ↗</a>
        <a href="#reality" className="matrix-nav">◎ <span>Reality Engine</span> ↗</a>
        <div className="matrix-sidebar-bottom">
          <div className="matrix-signal"><span>∞</span><p>One intent.<br />A chain of evidence.</p></div>
          <small>Verification is earned, never assumed.</small>
        </div>
      </aside>

      <section className="matrix-center">
        <div className="matrix-intro">
          <div className="matrix-intro-top">
            <span className="matrix-eyebrow"><i /> SOVEREIGN COMMAND INTERFACE <b>·</b> CIH ΔiΔ</span>
            <div className="matrix-motion-controls" role="group" aria-label="Realtime Matrix movement controls">
              <span className={"matrix-motion-indicator " + (matrixMotion ? "moving" : "")}>{matrixMotion ? "◉ LIVE 3D MATRIX" : "◌ MATRIX PAUSED"}</span>
              <button type="button" aria-label={matrixMotion ? "Pause Matrix movement" : "Resume Matrix movement"} aria-pressed={matrixMotion} onClick={toggleMatrix}>{matrixMotion ? "Ⅱ PAUSE" : "▶ PLAY"}</button>
              <button type="button" title="Change tunnel travel speed" aria-label={"Matrix speed: " + matrixSpeed + ". Change speed."} onClick={() => setMatrixSpeed((current) => current === "flow" ? "warp" : current === "warp" ? "drift" : "flow")}>{matrixSpeed === "warp" ? "⚡ WARP" : matrixSpeed === "drift" ? "◌ DRIFT" : "↗ FLOW"}</button>
            </div>
          </div>
          <h1>Just Ask <em>Buddy.</em><sup>™</sup></h1>
          <p>Build with intelligence. Verify with evidence. Let every artifact carry the record of what actually happened.</p>
        </div>
        <div className="matrix-ticker matrix-glass" aria-live="off">
          <div className="ticker-label"><span className="pulse-point" /> MARKET PULSE</div>
          <div className="ticker-track">
            {quotes.length ? quotes.map((q) => <div className="ticker-item" key={q.symbol}><b>{q.symbol}</b> <span>{"$" + q.price_usd.toLocaleString("en-US", { maximumFractionDigits: 2 })}</span><small>{q.source}</small></div>) : <span className="ticker-unavailable">{marketState}</span>}
            <div className="ticker-item muted">GAS FEE <span>UNAVAILABLE</span></div>
          </div>
          <button onClick={() => setView("market")}>DETAILS ↗</button>
        </div>

        {view === "buddy" && <div className="matrix-chat matrix-glass">
          <div className="matrix-pane-head"><div><span className="matrix-eyebrow">INFERENCE SURFACE / 001</span><h2>Conversation</h2></div><span className="subtle-badge">NO UNAPPROVED EXECUTION</span></div>
          <div className="matrix-chat-log" role="log" aria-live="polite">
            {chat.map((msg, i) => <article className={"matrix-message " + msg.role} key={i}>
              <span className="speaker">{msg.role === "user" ? "YOU" : "i™ BUDDY"}</span>
              <p>{msg.content}</p>{msg.source && <small>{msg.source}</small>}
            </article>)}
            {thinking && <div className="matrix-thinking">◌ Buddy request in progress · waiting for verified source status…</div>}
            <div ref={endRef} />
          </div>
          <div className="matrix-command">
            <button aria-label={listening ? "Stop microphone" : "Start microphone with permission"} aria-pressed={listening} title="Speak one request to Buddy" onClick={microphone} className={"orb-mic " + (listening ? "listening" : "")}>◉</button>
            <input maxLength={1500} aria-label="Message to Buddy" placeholder="Ask Buddy anything. Create, build, verify, explore…" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void send(); }} />
            <button className="matrix-primary" onClick={() => void send()} disabled={thinking || !query.trim()}>ASK BUDDY ↗</button>
          </div>
           <div className="matrix-voice-row"><span role="status">{listening ? "◉ MICROPHONE ACTIVE · BROWSER SESSION" : "◌ MICROPHONE OFF · CLICK TO SPEAK"}</span><button aria-pressed={spokenReplies} type="button" onClick={toggleSpokenReplies}>{spokenReplies ? "♫ SPOKEN REPLIES ON · TURN OFF" : "♫ SPOKEN REPLIES OFF · TURN ON"}</button></div>
           <div className="matrix-command-foot">{BUDDY_PREVIEW ? "CONSTITUTIONAL BUDDY PREVIEW · NOT PRODUCTION. " : ""}The microphone activates only on click and requests browser permission. Spoken replies are enabled by default but may require browser audio activation. Speech recognition can use an external browser service. Neither speech nor model output is CIH attestation.</div>
        </div>}

        {view === "build" && <div className="matrix-surface matrix-glass">
          <div className="matrix-pane-head"><div><span className="matrix-eyebrow">NATIVE ARTIFACT WORKFLOW</span><h2>Build an artifact</h2></div><span className="subtle-badge">LOCAL · NO CLOUD WRITE</span></div>
          <label>ARTIFACT NAME<input value={artifactName} maxLength={120} onChange={(e) => setArtifactName(e.target.value)} /></label>
          <label>ARTIFACT CLASS<select value={artifactKind} onChange={(e) => setArtifactKind(e.target.value)}>{["DESIGN","DOCUMENT","MODEL","SOURCE","DATASET","PACKAGE"].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>INTENT / CONTRACT<textarea rows={5} maxLength={5000} value={intent} onChange={(e) => setIntent(e.target.value)} /></label>
          <div className="matrix-form-row"><button className="matrix-primary" onClick={() => void createLocalArtifact()}>GENERATE & HASH ↗</button><a className="matrix-secondary" href="#artifacts">OPEN AUTHENTICATED COMPILER ↗</a></div>
          <p className="matrix-disclosure">Generates a real local SHA-256 digest of the serialized contract. Generation is not correctness, trusted attestation, or deployment.</p>
        </div>}

        {view === "verify" && <div className="matrix-surface matrix-glass">
          <div className="matrix-pane-head"><div><span className="matrix-eyebrow">EVIDENCE / INTEGRITY</span><h2>Inspect a receipt</h2></div><span className="subtle-badge">FAIL-CLOSED VERIFICATION</span></div>
          <p>Paste an i™ local artifact JSON or a supported signed CIH receipt. Local hash checks run in your browser; signed receipts are sent to the configured verifier only when requested.</p>
          <textarea aria-label="Receipt JSON" className="receipt-textarea" rows={9} placeholder='{"format":"i-artifact-local-v1", "payload": {...}, "sha256":"..."}' value={rawReceipt} onChange={(e) => setRawReceipt(e.target.value)} />
          <div className="matrix-form-row"><button className="matrix-primary" onClick={() => void verifyLocal()}>COMPARE LOCAL HASH</button><button className="matrix-secondary" onClick={() => void verifySigned()}>VERIFY SIGNATURE ↗</button></div>
          <pre className="matrix-verify-result" role="status">{verified || "No verification performed."}</pre>
          <section className="cih-connect-panel" aria-label="Sovereign KRDID receipt integration">
            <div className="matrix-pane-head"><div><span className="matrix-eyebrow">LOCAL .KRDID × CIH ΔiΔ</span><h2>Sovereign Evidence Index</h2></div><span className="subtle-badge">{cihHealthStatus}</span></div>
            <p>Your browser can create a non-extractable WebCrypto software key. A trusted CIH operator must enroll the public key out of band. The API verifies the signed request against its own local key registry, protects nonces against replay, and signs the receipt with the node key. No cloud identity provider is required.</p>
            <div className="cih-readiness-grid">
              <span>LOCAL SOFTWARE KEY</span><strong>{identity.label}</strong>
              <span>THIS BROWSER .KRDID</span><strong>{identity.krdid || "NOT GENERATED"}</strong>
              <span>NODE ENROLLED IDENTITIES</span><strong>{cihHealth?.auth_configured ? String(cihHealth.krdid_enrolled_count ?? "?") + " ON NODE" : "NO VERIFIED ENROLLMENT"}</strong>
              <span>ED25519 NODE SIGNER</span><strong>{cihHealth?.signer_configured ? "CONFIGURED" : "NOT CONNECTED"}</strong>
              <span>TRUSTED RECEIPT KEY</span><strong>{cihHealth?.trusted_key_configured ? "CONFIGURED" : "NOT CONNECTED"}</strong>
              <span>LOCAL SQLITE STORAGE</span><strong>{cihHealth?.storage_configured ? "NODE READY · HOST-LOCAL" : "NOT CONNECTED"}</strong>
              <span>SUPABASE OPTIONAL REPLICA</span><strong>{cihHealth?.remote_replica_configured ? "SERVER KEY CONFIGURED" : "NOT CONFIGURED · LOCAL OPERATES"}</strong>
              <span>REMOTE REPLICA QUEUE</span><strong>{cihHealth?.remote_replica_pending_count ?? "UNREPORTED"} PENDING · {cihHealth?.remote_replica_acknowledged_count ?? "?"} ACKNOWLEDGED</strong>
            </div>
            <div className="matrix-form-row">
              {!identity.hasLocalKey && !identity.isLoading && <button className="matrix-secondary" onClick={() => void identity.initialize().catch((e:unknown) => setStatusMessage(e instanceof Error ? e.message : "LOCAL_KEY_CREATION_FAILED"))}>CREATE LOCAL .KRDID SOFTWARE KEY</button>}
              {identity.enrollmentCommand && <button className="matrix-secondary" onClick={() => void navigator.clipboard.writeText(identity.enrollmentCommand!).then(() => setStatusMessage("Public key enrollment command copied. Run it on the trusted CIH backend host, not in the browser.")).catch(() => setStatusMessage("Copy failed; ensure clipboard permissions."))}>COPY TRUSTED-NODE ENROLLMENT COMMAND</button>}
              <button className="matrix-primary" disabled={!artifact || !identity.hasLocalKey || !cihHealth?.auth_configured || !cihHealth?.signer_configured || !cihHealth?.storage_configured || cihIssuing} onClick={() => void issueAuthenticatedReceipt()}>
                {cihIssuing ? "ISSUING…" : "ISSUE .KRDID SIGNED RECEIPT"}
              </button>
            </div>
            {identity.enrollmentCommand && <p><strong>Operator action required:</strong> enroll this browser's public key on the same CIH node that issues receipts. The public key can be copied safely; never share a private key. Node readiness does not verify this specific browser is enrolled.</p>}
            <p className="matrix-disclosure">No Auth0, development bearer bypass, client-supplied authority key, automatic enrollment, or fake signature. A browser CryptoKey is not hardware attestation. Supabase is optional replica storage, never an identity authority; a cloud outage cannot block local issuance. Neither SQLite nor a remote database is by itself immutable or decentralized consensus. An ephemeral CIH host may lose its local records on redeployment. No physical or scientific certification.</p>
          </section>
          <NuPrintPanel currentReceipt={issuedReceipt} quarantined={localRevoked} />
        </div>}

        {view === "market" && <div className="matrix-surface matrix-glass">
          <div className="matrix-pane-head"><div><span className="matrix-eyebrow">SOURCE-BOUND PUBLIC DATA</span><h2>Market Pulse</h2></div><span className="subtle-badge">{marketState}</span></div>
          <div className="matrix-market-grid">{["BTC","ETH","DOW","SP500","NASDAQ","GOLD","OIL","GAS FEE"].map((symbol) => {
            const q = quotes.find((p) => p.symbol === symbol);
            return <article key={symbol}><small>{symbol}</small><strong>{q ? "$" + q.price_usd.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "—"}</strong><span>{q ? q.source + " · " + stamp(q.observed_at) : "LIVE FEED NOT CONNECTED"}</span></article>;
          })}</div>
          <p className="matrix-disclosure">Displayed quotes use fetched source values, not random walks. Spot quotes are indicative, can be delayed, and are not brokerage execution prices. Missing values stay unavailable.</p>
        </div>}

        {view === "imine" && <div className="matrix-surface matrix-glass">
          <div className="matrix-pane-head"><div><span className="matrix-eyebrow">iMINE · DEFENSIVE POLICY</span><h2>Quarantine & revoke</h2></div><span className="subtle-badge">SIMULATION ONLY</span></div>
          <div className="imine-glyph">⛨ <span>NO DESTRUCTIVE COMMANDS</span></div>
          <p>When a signed receipt fails validation, the secure response is to quarantine the workflow, record the reason, and require authorized review. This local demonstration does not wipe keys, disable equipment, destroy records, burn assets, or revoke a global DAG.</p>
          <div className="matrix-form-row"><button className="matrix-secondary" onClick={revokeLocal}>SIMULATE QUARANTINE</button><button className="matrix-secondary" onClick={() => { setLocalRevoked(false); record("Policy review", "LOCAL", "Simulation reset locally."); }}>RESET LOCAL VIEW</button></div>
          <p className="matrix-disclosure">Status: {localRevoked ? "LOCAL_QUARANTINE · no remote impact" : "NOT_ARMED · no remote impact"}. Irreversible actions require separately authenticated tools and approvals.</p>
        </div>}

        {view === "evidence" && <div className="matrix-surface matrix-glass">
          <div className="matrix-pane-head"><div><span className="matrix-eyebrow">EVIDENCE INDEX · SESSION</span><h2>Action ledger</h2></div><span className="subtle-badge">SESSION ONLY</span></div>
          <p>These entries report actual actions in this browser tab. They are not signed, durable or externally audited.</p>
          <div className="matrix-evidence-list">{evidence.length ? evidence.map((item, index) => <article key={item.at + index}><b className={"evi-" + item.status.toLowerCase()}>{item.status}</b><div><strong>{item.label}</strong><span>{item.detail}</span></div><time>{stamp(item.at)}</time></article>) : <p>No session evidence yet. Generate an artifact or send a Buddy message.</p>}</div>
        </div>}

        <div className="matrix-workflow matrix-glass">
          <span className="matrix-eyebrow">EVERY ARTIFACT HAS A CHAIN</span>
          <div className="matrix-steps">{sequence.map((stage, index) => <div className={"matrix-step " + (index < activeStage ? "reached" : "")} key={stage}><b>{"0" + (index + 1)}</b><span>{stage}</span>{index !== 4 && <i>→</i>}</div>)}</div>
          <p>{artifact ? "Local generation complete. Independent verification and signed receipt are NOT earned." : "Intent entered. No generation, verification or signed receipt has been completed."}</p>
        </div>
      </section>

      <aside className="matrix-right matrix-glass">
        <div className="matrix-pane-head"><div><span className="matrix-eyebrow">ΔiΔ / PROOF OF PROCESS</span><h2>Evidence receipt</h2></div><span className="live-pixel" /></div>
        <div className={"matrix-receipt " + (localRevoked ? "quarantined" : "")}>
          <div className="receipt-topline"><span>i™ ARTIFACTGPTm™</span><b>🧾</b></div>
          <div className="receipt-orb"><span>{localRevoked ? "!" : artifact ? "⌗" : "∞"}</span></div>
          <h3>{localRevoked ? "LOCAL QUARANTINE" : issuedReceipt ? "CIH SIGNED · NOT CERTIFIED" : artifact ? "GENERATED · UNSIGNED" : "AWAITING EVIDENCE"}</h3>
          <p>{artifact ? artifact.payload.name : "No artifact has been created in this session."}</p>
          <div className="receipt-details">
            <div><span>RECEIPT CLASS</span><strong>{artifact ? "LOCAL DIGEST" : "NONE"}</strong></div>
            <div><span>ARTIFACT ID</span><code>{artifact ? short(artifact.payload.artifact_id) : "—"}</code></div>
            <div><span>SHA-256</span><code>{artifact ? short(artifact.sha256) : "NOT GENERATED"}</code></div>
            <div><span>TRUSTED SIGNATURE</span><strong>{verified.includes("SIGNATURE_VALID") && verified.includes("true") ? "VALID · SCOPED" : issuedReceipt ? "ISSUED · NOT VERIFIED" : "NOT VERIFIED"}</strong></div>
            <div><span>CERTIFIED LIVE™</span><strong>NOT AWARDED</strong></div>
          </div>
          <div className="receipt-edges" aria-hidden="true"><span>◆</span><span>◇</span><span>◆</span><span>◇</span><span>◆</span></div>
          <div className="receipt-stamp">EVIDENCE-BOUND · NO OVERCLAIMS</div>
        </div>
        <div className="matrix-right-actions">
          <button disabled={!artifact} onClick={downloadArtifact}>↓ EXPORT LOCAL ARTIFACT</button>
          <button disabled={!artifact} onClick={() => { if (artifact) { setRawReceipt(JSON.stringify(artifact, null, 2)); setView("verify"); } }}>◇ INSPECT INTEGRITY</button>
        </div>
        <section className="matrix-news-panel" aria-label="Global Intel Feed">
          <div className="matrix-news-head"><span>⌁ GLOBAL INTEL</span><span>{newsState}</span></div>
          {headlines.length ? <div className="matrix-news-list">{headlines.slice(0,5).map((n,i) => <article key={n.url+i}><span>{n.source}</span><a href={n.url} rel="noopener noreferrer" target="_blank">{n.title}</a></article>)}</div> : <p>Publisher headlines unavailable. No simulated news.</p>}
          <small>Attributed public publisher headlines · Feed may be technology-only if the global source is unavailable. Not independently verified.</small>
        </section>
        <div className="matrix-right-footer"><span>◉ LIVE API</span><strong>{apiState}</strong><small>{statusMessage}</small><a href="https://www.innovulis.com/#architecture" target="_blank" rel="noreferrer">EXPLORE THE CIH ARCHITECTURE ↗</a></div>
      </aside>
    </div>
    <footer className="matrix-footer"><span>i™ ARTIFACTGPTm™ · JUST ASK BUDDY™</span><span>Technology should serve humanity.</span><span>© 2026 STRMKRD · Proof is scoped, measured and earned.</span></footer>
    <nav className="matrix-mobile-nav" aria-label="Mobile workspace navigation">{nav.slice(0,5).map((item) => <button className={view === item.id ? "selected" : ""} onClick={() => setView(item.id)} key={item.id}><span>{item.icon}</span>{item.label}</button>)}</nav>
  </main>;
}
