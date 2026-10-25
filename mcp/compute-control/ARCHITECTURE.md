# Compute Control MCP — Architecture

```
                         COMPUTE CONTROL MCP
                                  |
              +-------------------+-------------------+
              |                   |                   |
           COMPUTE          CONNECTIVITY          EVIDENCE
              |                   |                   |
     GPU / CPU / VM          SSH / APIs          PoP receipts
     containers              cellular            hashes
     bare metal              telecom             provenance
     lifecycle               internet            telemetry
              |               WiFi/Bluetooth         |
              +-------------------+-------------------+
                                  |
                          AI / WORKLOADS
                                  |
                          PROVIDER ADAPTERS
                                  |
          +----------+----------+----------+----------+
          |          |          |          |          |
        RunPod      AWS       Azure       GCP      Other
          |          |          |          |
      AMD/NVIDIA   CPU/GPU   CPU/GPU    CPU/GPU
      ROCm/CUDA    VMs       VMs        VMs
```

## Adapter Contract

A provider adapter normalizes discovery, lifecycle, telemetry, networking,
and workload execution into a provider-neutral interface. Provider-specific
fields remain in an adapter payload and are referenced by the evidence envelope.

## Evidence Contract

Execution is represented as:

`intent -> provider operation -> telemetry -> artifact hashes -> PoP receipt -> optional external anchor`

The MCP never upgrades a provider observation into physical correspondence truth.

## Mutation Boundary

Lifecycle operations are policy-enforced. A provider adapter may implement
create/start/stop/restart/terminate, but the policy layer controls whether the
operation is permitted.

Physical actuation is explicitly outside this MCP. Aerial, robotic, or
high-consequence actuation must pass the existing PoP physical/sovereign gates.

## Secrets

Credentials are provider-scoped and never copied into PoP receipts. Receipts
contain provider identifiers, operation identifiers, and hashes rather than
raw secrets.

## Extension Model

New providers implement the adapter contract without changing tool semantics.
New connectivity domains and evidence backends follow the same normalized model.
