# i™ PoP Edge

Cloudflare Worker edge adapter for the Proof-of-Process service.

## Boundary

- Proxies GET/POST traffic to the configured Render origin.
- Adds an edge-observation header to the origin request and response.
- Caches only GET /truth-boundary for 60 seconds.
- Does not mint, infer, or synthesize a manifest hash.
- Does not establish physical silicon, physical energy, hardware attestation, or external blockchain anchoring.
- `EDGE_SHARED_SECRET` is optional until the Render origin is configured to require it.

## Deployment

The Worker can be uploaded through the Cloudflare API or Wrangler. No production route is declared in this repository configuration; a route must be explicitly attached to the intended zone.
