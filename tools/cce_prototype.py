"""i™ Epistemic Genesis / 1.0 bounded prototype.

The generated solver is executed in a separate child process. This is a
software proof-of-process boundary, not a kernel-grade security sandbox.
physical_gate is permanently ACTION_REQUIRED.
"""
import hashlib, json, multiprocessing as mp, os, resource, socket, time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from tools.mmr_pipeline import MerkleMountainRange

def jcs(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def sha(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()

def _child(source, grid, memory_mb, q):
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        limit = int(memory_mb) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        class DeniedSocket:
            def __init__(self, *a, **k):
                raise PermissionError("CCE sandbox network denied")
        socket.socket = DeniedSocket
        socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(
            PermissionError("CCE sandbox network denied")
        )
        ns = {"__name__": "__cce_generated__"}
        exec(compile(source, "<generated-cognition>", "exec"), ns, ns)
        result = ns["solve"](grid)
        q.put(("ok", json.dumps(result, sort_keys=True, separators=(",", ":"))))
    except BaseException as exc:
        q.put(("error", type(exc).__name__ + ": " + str(exc)))

class CCE:
    def __init__(self):
        self.key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ).hex()

    def generate_cognition(self, problem, base_failure_hash):
        source = (
            "from collections import deque\n"
            "def solve(grid):\n"
            "    goal=(len(grid)-1,len(grid[0])-1); q=deque([((0,0),[(0,0)])]); seen={(0,0)}\n"
            "    while q:\n"
            "        p,path=q.popleft()\n"
            "        if p==goal: return path\n"
            "        r,c=p\n"
            "        for n in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):\n"
            "            if 0<=n[0]<len(grid) and 0<=n[1]<len(grid[0]) and grid[n[0]][n[1]]==0 and n not in seen:\n"
            "                seen.add(n); q.append((n,path+[n]))\n"
            "    return None\n"
        )
        method_id = "method-" + hashlib.sha256(source.encode()).hexdigest()[:16]
        body = {
            "spec": "innovulis-epistemic-genesis-synthesis/1.0",
            "method_id": method_id,
            "problem_hash": sha(problem.encode()),
            "base_failure_hash": base_failure_hash,
            "language": "python",
            "source_code_hash": sha(source.encode()),
            "issuer_pubkey": self.public_key,
            "physical_gate": "ACTION_REQUIRED",
        }
        body["signature"] = self.key.sign(jcs(body)).hex()
        return method_id, source, body

    def execute(self, method_id, source, grid, timeout_ms=5000, memory_mb=256):
        q = mp.Queue()
        p = mp.Process(target=_child, args=(source, grid, memory_mb, q))
        t0 = time.time_ns(); p.start(); p.join(timeout_ms / 1000)
        if p.is_alive():
            p.kill(); p.join()
            stdout, stderr, code = "", "TIMEOUT", -1
        elif not q.empty():
            kind, value = q.get()
            if kind == "ok":
                stdout, stderr, code = value, "", 0
            else:
                stdout, stderr, code = "", value, 1
        else:
            stdout, stderr, code = "", "CHILD_EXITED_WITHOUT_RECEIPT", 1
        t1 = time.time_ns()
        return {
            "sandbox_id": "cce-multiprocessing-child",
            "method_id": method_id,
            "stdout_hash": sha(stdout.encode()),
            "stderr_hash": sha(stderr.encode()),
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": code,
            "duration_ns": t1 - t0,
            "constraints": {
                "timeout_ms": timeout_ms,
                "memory_mb": memory_mb,
                "no_network": True,
                "network_enforcement": "child_socket_policy",
                "kernel_isolation": False,
            },
            "physical_gate": "ACTION_REQUIRED",
        }

    def validate(self, execution, expected):
        expected_text = json.dumps(expected, sort_keys=True, separators=(",", ":"))
        expected_hash = sha(expected_text.encode())
        success = (
            execution["stdout_hash"] == expected_hash
            and execution["stderr_hash"] == sha(b"")
            and execution["exit_code"] == 0
        )
        return {
            "spec": "innovulis-epistemic-genesis/1.0",
            "execution": {k: execution[k] for k in (
                "sandbox_id", "stdout_hash", "stderr_hash", "exit_code", "duration_ns"
            )},
            "validation": {
                "success": success,
                "expected_hash": expected_hash,
                "actual_hash": execution["stdout_hash"],
            },
            "ilogic": {
                "truth_axis": "ESTABLISHED" if success else "REFUTED",
                "attestation_axis": "UNATTESTED",
                "tier": "VERIFIED_PROCESS" if success else "REFUTED",
                "physical_gate": "ACTION_REQUIRED",
            },
            "issuer_pubkey": self.public_key,
            "physical_gate": "ACTION_REQUIRED",
        }

def verify_epistemic_genesis(r):
    ex, v = r["execution"], r["validation"]
    derived = (
        ex["stdout_hash"] == v["expected_hash"]
        and ex["stderr_hash"] == sha(b"")
        and ex["exit_code"] == 0
    )
    errors = []
    if derived != v["success"]:
        errors.append("genesis_forgery")
    expected_truth = "ESTABLISHED" if derived else "REFUTED"
    expected_tier = "VERIFIED_PROCESS" if derived else "REFUTED"
    if r["ilogic"]["truth_axis"] != expected_truth:
        errors.append("truth_axis_mismatch")
    if r["ilogic"]["tier"] != expected_tier:
        errors.append("tier_mismatch")
    if r["physical_gate"] != "ACTION_REQUIRED":
        errors.append("physical_gate_mismatch")
    return errors

def run():
    c = CCE()
    method, source, synthesis = c.generate_cognition(
        "Find shortest path in a binary grid.", sha(b"base-attempt-failed")
    )
    grid = [[0,1,0],[0,1,0],[0,0,0]]
    expected = [[0,0],[1,0],[2,0],[2,1],[2,2]]
    execution = c.execute(method, source, grid)
    outcome = c.validate(execution, expected)
    errors = verify_epistemic_genesis(outcome)
    assert not errors, errors
    mmr = MerkleMountainRange()
    mmr.append(jcs(synthesis)); mmr.append(jcs(outcome))
    return {
        "spec": "innovulis-epistemic-genesis/1.0",
        "synthesis": synthesis,
        "execution": execution,
        "validation": outcome["validation"],
        "ilogic": outcome["ilogic"],
        "receipt_mmr_root": mmr.root(),
        "physical_gate": "ACTION_REQUIRED",
    }

if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
