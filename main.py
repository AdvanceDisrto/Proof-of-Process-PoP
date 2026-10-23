from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="i™ Proof of Process (PoP) API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "i-pop-core"}

@app.get("/reality/manifest")
def reality_manifest():
    return {
        "spec": "innovulis-reality-evidence/1.1",
        "state": "VERIFIED_PROCESS",
        "physical_gate": "ACTION_REQUIRED",
        "master_manifest_hash": None,
        "does_not_prove": [
            "absolute entirety of existence",
            "physical silicon fabrication",
            "foundry acceptance",
            "measured physical energy",
            "hardware root of trust",
            "external blockchain anchoring",
        ],
        "disclosure": "No fabricated manifest hash is returned by this API.",
    }

@app.get("/truth-boundary")
def truth_boundary():
    return {
        "physical_gate": "ACTION_REQUIRED",
        "does_not_prove": [
            "Experimental proof of quantum physics",
            "Physical silicon fabrication",
            "Foundry acceptance",
            "Measured physical energy",
            "Hardware root of trust",
        ],
        "the_central_rule": "The receipt can record reality; it cannot manufacture reality.",
    }
