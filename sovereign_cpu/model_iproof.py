import hashlib
import json
import os
import time
import uuid

import torch
import torch.nn as nn
import torch.optim as optim
from cryptography.hazmat.primitives.asymmetric import ed25519

# CPU-only execution.
torch.set_num_threads(8)
device = torch.device("cpu")


class GenesisModel(nn.Module):
    def __init__(self, input_dim=32, hidden_dim=64, output_dim=16):
        super().__init__()
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.layer3 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = self.layer1(x)
        x = self.relu(x)
        x = self.layer2(x)
        x = self.relu(x)
        return self.layer3(x)


def hash_weights(model):
    hasher = hashlib.sha256()
    for param in model.parameters():
        hasher.update(param.detach().cpu().numpy().tobytes())
    return hasher.hexdigest()


def generate_iproof(initial_hash, final_hash, steps_log, model_params):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    process_id = str(uuid.uuid4())

    payload = {
        "protocol": "IPROOF-iFM-v1",
        "process_id": process_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": "CPU",
        "parameters": model_params,
        "initial_state_hash": f"sha256:{initial_hash}",
        "final_state_hash": f"sha256:{final_hash}",
        "execution_trace": steps_log,
        "state": "TRAINING_VERIFIED_PROCESS",
        "parameter_claim_note": (
            "This GenesisModel architecture contains 7312 parameters; "
            "parameter count is measured from the instantiated model."
        ),
    }

    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = private_key.sign(payload_bytes)

    return {
        "payload": payload,
        "signature": signature.hex(),
        "public_key": public_key.public_bytes_raw().hex(),
        "signature_algorithm": "Ed25519",
        "signed_payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
    }


def run_genesis_training(output_path="ifm_genesis_receipt.json"):
    model = GenesisModel().to(device)
    param_count = sum(p.numel() for p in model.parameters())

    initial_hash = hash_weights(model)
    optimizer = optim.SGD(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()

    x = torch.randn(4, 32, device=device)
    y_target = torch.randn(4, 16, device=device)

    steps_log = []
    epochs = 50

    for step in range(epochs):
        optimizer.zero_grad()
        y_pred = model(x)
        loss = criterion(y_pred, y_target)
        loss.backward()

        grad_norm = sum(
            p.grad.norm().item() ** 2
            for p in model.parameters()
            if p.grad is not None
        ) ** 0.5

        optimizer.step()

        if step % 10 == 0 or step == epochs - 1:
            current_hash = hash_weights(model)
            steps_log.append(
                {
                    "step": step + 1,
                    "loss": round(loss.item(), 6),
                    "gradient_norm": round(grad_norm, 6),
                    "weight_hash": f"sha256:{current_hash}",
                }
            )

    final_hash = hash_weights(model)
    receipt = generate_iproof(
        initial_hash, final_hash, steps_log, param_count
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)

    print(json.dumps(receipt, indent=2))
    print(f"PARAMETERS={param_count}")
    print(f"INITIAL_HASH=sha256:{initial_hash}")
    print(f"FINAL_HASH=sha256:{final_hash}")
    print(f"RECEIPT={os.path.abspath(output_path)}")


if __name__ == "__main__":
    run_genesis_training()
