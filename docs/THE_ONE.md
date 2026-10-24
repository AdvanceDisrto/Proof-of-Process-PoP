# THE ONE — Epistemic Framing

This note separates three different scales that must not be collapsed into a single “minimum percentage.”

| Axis | Current figure | Meaning |
|---|---:|---|
| Architecture constant | 0.039% | Top-2 of 5,120 routing constant |
| Architecture constant | 0.088% | 90B active / 102T sparsity ratio |
| Hardware bound | 0.0059% | 6B / 102T local no-cloud ceiling in bf16 |
| Proof artifact | 0.000001% | 1M / 102T proof-of-loop run |
| Role-complete threshold | 0.001% | 1B / 102T learning-capacity threshold |

These values answer different questions and must not be ranked as though they share one axis. The 0.0059% value is a current local hardware ceiling, not a global floor. The 0.000001% value is a proof artifact, not a role-complete intelligence threshold.

## RTX 3060 feasibility

The RTX 3060 exists in 8 GB and 12 GB variants.

| Task | Feasibility |
|---|---|
| 6B bf16 inference, 12 GB SKU, <=2K context | Marginally possible; weights alone consume about 12 GB |
| 6B bf16 inference, 8 GB SKU | Not possible |
| 6B full bf16 training | Not possible on either SKU |
| QLoRA int4 adaptation | Possible on 12 GB in the roughly 6–7B range |
| bf16 test-time training | Realistically 1–3B |

Therefore the correct claim is: **6B carries the weights for inference and demonstrates QLoRA adaptation; full bf16 TTT is realistically a 1–3B regime on this hardware.**

## Reporting rule

Architecture constants, hardware bounds, and proof artifacts are separate columns in every future THE ONE presentation. None is described as the global minimum.

