from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class FabricPayload(BaseModel):
    """Payload whose canonical source fields were hashed by the upstream Fabric."""
    data_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    origin_node_id: str
    timestamp: str
    clinical_data: dict[str, Any]
    omics_data: dict[str, Any]
    environmental_data: dict[str, Any]


class Hypothesis(BaseModel):
    root_cause: str
    proposed_intervention: str
    target_compound: str = "none"
    confidence_score: float = Field(ge=0.0, le=1.0)


class EGIReceipt(BaseModel):
    receipt_type: str = "epidemic_genesis_inference"
    pipeline_run_id: str
    input_hash: str
    hypothesis_hash: str
    model_weights_hash: str
    hardware_tee_quote: Optional[str] = None
    timestamp: str
    state: str
    physical_gate_required: bool = True


class EpidemicGenesisBrain:
    """Fail-closed scientific inference engine.

    It generates hypotheses only. It never authorizes synthesis, deployment,
    treatment, or other physical action.
    """

    def __init__(self, model_weights_path: str = "./models/egi_gnn_v1.gguf"):
        self.model_weights_path = model_weights_path
        self.model_weights_hash = self._hash_required_file(model_weights_path)

    @staticmethod
    def _hash_required_file(filepath: str) -> str:
        if not os.path.isfile(filepath):
            raise FileNotFoundError(
                f"Model weights not found: {filepath}; refusing to substitute mock weights."
            )
        hasher = hashlib.sha256()
        with open(filepath, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _canonical_source(payload: FabricPayload) -> str:
        source = payload.model_dump(exclude={"data_hash"})
        return json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def _hash_source(cls, payload: FabricPayload) -> str:
        return hashlib.sha256(cls._canonical_source(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_json(value: Any) -> str:
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _run_correlation(payload: FabricPayload) -> Hypothesis:
        toxin = payload.environmental_data.get("toxin_level", 0)
        mutation = payload.omics_data.get("proteomic_mutation", "none")
        if isinstance(toxin, (int, float)) and toxin > 50 and mutation != "none":
            return Hypothesis(
                root_cause=f"Observed environmental marker {toxin} with proteomic marker {mutation}.",
                proposed_intervention="Escalate for independent scientific review and physical evidence gating.",
                target_compound="none",
                confidence_score=0.94,
            )
        return Hypothesis(
            root_cause="No significant anomaly detected by the configured correlation rule.",
            proposed_intervention="Continue monitoring and collect additional independent evidence.",
            target_compound="none",
            confidence_score=0.99,
        )

    def analyze_fabric_data(self, payload: FabricPayload) -> EGIReceipt:
        calculated_input_hash = self._hash_source(payload)
        if not hashlib.compare_digest(calculated_input_hash, payload.data_hash.lower()):
            raise ValueError("QUARANTINED: Fabric payload hash mismatch.")

        hypothesis = self._run_correlation(payload)
        hypothesis_hash = self._hash_json(hypothesis.model_dump())
        tee_quote = os.environ.get("AMD_SEV_SNP_QUOTE") or None

        return EGIReceipt(
            pipeline_run_id=f"egi-run-{uuid.uuid4().hex}",
            input_hash=calculated_input_hash,
            hypothesis_hash=hypothesis_hash,
            model_weights_hash=self.model_weights_hash,
            hardware_tee_quote=tee_quote,
            timestamp=datetime.now(timezone.utc).isoformat(),
            state="UNVERIFIED_INFERENCE",
            physical_gate_required=True,
        )

    @staticmethod
    def handoff_state(receipt: EGIReceipt) -> dict[str, str]:
        return {
            "state": receipt.state,
            "physical_gate": "ACTION_REQUIRED",
            "materialization": "BLOCKED",
            "rule": "Inference may propose; an independent evidence gate must authorize any physical action.",
        }
