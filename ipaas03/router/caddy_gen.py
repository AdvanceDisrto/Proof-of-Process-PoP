def render_caddyfile(services: list[dict[str, object]], cache_seconds: int = 0, upstreams: dict[str, list[tuple[str, int]]] | None = None) -> str:
    blocks: list[str] = []
    for service in services:
        name = str(service["name"])
        hostname = str(service["hostname"])
        runtime = str(service["runtime"])
        lines = [f"{hostname} {{"]
        if runtime == "static":
            lines.append("  file_server")
        else:
            targets = (upstreams or {}).get(name, [("127.0.0.1", 8000)])
            lines.append("  reverse_proxy " + " ".join(f"{host}:{port}" for host, port in targets))
            lines.append("  header_up Connection {http.request.header.Connection}")
            lines.append("  header_up Upgrade {http.request.header.Upgrade}")
        if cache_seconds > 0:
            lines.append(f'  header Cache-Control "public, max-age={cache_seconds}"')
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n".join(blocks) + ("\n" if blocks else "")
