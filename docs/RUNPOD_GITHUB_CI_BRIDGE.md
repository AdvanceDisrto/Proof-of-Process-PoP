# i™ / iNNOVULIS — GitHub Actions ↔ RunPod operator bridge

This reviewed GitHub Actions integration authenticates to **RunPod** using an
operator-owned GitHub Actions secret, verifies an **existing** pod, and optionally
uses an independently pinned SSH host key to run a **real AMD Vulkan/wgpu + Z3**
software smoke test on that pod.

## Evidence boundaries

- The pull request triggers only CPU-side Rust compilation and Z3 tests, not RunPod.
- The RunPod connection job runs **only** via manual workflow_dispatch after
  the workflow is approved and merged to the default branch.
- The GPU job runs only when the operator explicitly chooses `mode=gpu`.
- The GPU job does not create/stop/delete pods, upload private evidence,
  deploy production, or merge code.
- `DAGE_GPU_SMOKE=PASS` means a physical **AMD** Vulkan adapter executed the
  declared WGSL DAG dependency-propagation kernel and matched the CPU reference.
  It does **not** prove cryptographic signatures on GPU, real sensor accuracy,
  external witnessing, mathematical truth outside the Z3 theory, or full DAGE
  offscreen rendering performance. No simulated GPU or llvmpipe can pass.
- An existing RunPod pod may continue billing while running; the workflow
  intentionally does not stop/delete resources it did not create.

## Operator setup (do not paste any credentials into a ChatGPT conversation)

In the GitHub repository, open Settings → Environments and configure a
protected environment named `runpod-gpu` with required reviewers.

Within that GitHub environment (or repository Actions secrets and variables),
configure:

| Name | Type | Value |
|------|------|-------|
| `RUNPOD_API_KEY` | Actions secret | Operator-generated RunPod API key, least privilege allowed |
| `RUNPOD_POD_ID` | Actions variable | ID of an existing RunPod pod |
| `RUNPOD_SSH_HOST` | Actions variable | Pod's public TCP SSH host from RunPod connection instructions |
| `RUNPOD_SSH_PORT` | Actions variable | Pod's TCP SSH port |
| `RUNPOD_SSH_PRIVATE_KEY` | Actions secret | PEM/OpenSSH private key for a designated CI SSH account authorized on that pod |
| `RUNPOD_SSH_KNOWN_HOSTS` | Actions secret | Independently verified host-key line for that exact host and port |

The pod must have the corresponding CI SSH *public* key configured. For a
nonstandard port, OpenSSH known_hosts uses `[hostname]:port ssh-ed25519 ...`.
Verify the host fingerprint out of band. The workflow deliberately **does not**
use `StrictHostKeyChecking=no`.

RunPod Official OAuth in ChatGPT is **not** propagated to GitHub Actions.
RunPod API credentials must be configured in GitHub by an authorized operator.
The GitHub connector in this session can create source and workflows but does
not expose a method to write Actions secrets or set RunPod connection values.

RunPod pod prerequisites: actual AMD GPU with working Vulkan ICD, `cargo`,
`rustc`, `pkg-config`, `vulkaninfo`, `libz3-dev`, Rust toolchain,
sufficient writable space, and a reachable SSH endpoint. The probe rejects
NVIDIA, software Vulkan, and missing dependencies instead of printing a false
physical-GPU success. AMD-specific pod availability must be confirmed before
scheduling hardware.

## Use

1. Review the PR; **do not merge until the owner approves**.
2. Once approved and merged, open Actions → "iNNOVULIS RunPod AMD DAGE GPU CI".
3. Select **Run workflow**, mode `connect`. This only checks authentication
   and verifies the pod ID exists, without provisioning or modifying it.
4. If that succeeds and the pod is preconfigured, select mode `gpu`.
   The runner uploads the *reviewed* smoke source over SSH to a uniquely
   named /tmp directory, runs actual native Z3 and Vulkan compute, checks
   `DAGE_GPU_SMOKE=PASS`, and uploads the execution log.
5. Review artifact and actual adapter info; manually stop the pod under your
   separate RunPod retention policy if appropriate. Do not delete existing pods
   without checking whether their copies/backups are verified.

## Failure handling

- Missing `RUNPOD_API_KEY` or `RUNPOD_POD_ID`: connection job fails closed.
- Wrong credentials, nonexisting pod, no SSH key, or untrusted host key:
  authenticating/SSH job fails closed.
- No *physical AMD* Vulkan adapter: explicit rejection; not a GPU acceptance.
- Missing Rust or libz3 on pod: explicit dependency failure; not a GPU acceptance.
- Hostile/untrusted PRs: no RunPod credentials are exposed on PR jobs.
- Remote GitHub Actions test success cannot be re-labeled physical sensor,
  independent-witness, ZK, or hardware-attestation acceptance.
