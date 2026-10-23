export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method.toUpperCase();

    if (method !== "GET" && method !== "POST") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: {
          "Allow": "GET, POST",
          "X-iEdge-Verification": "CLOUDFLARE_ACTIVE",
        },
      });
    }

    const originHost = env.ORIGIN_HOST || "proofofprocess.onrender.com";
    const originUrl = new URL(request.url);
    originUrl.hostname = originHost;
    originUrl.protocol = "https:";

    const headers = new Headers(request.headers);
    headers.set("X-iEdge-Verification", "CLOUDFLARE_ACTIVE");
    headers.set("X-iEdge-Timestamp", Date.now().toString());

    // Optional origin authentication. The origin must explicitly enable
    // EDGE_AUTH_REQUIRED before this becomes a hard gate.
    if (env.EDGE_SHARED_SECRET) {
      headers.set("X-iEdge-Authorization", env.EDGE_SHARED_SECRET);
    }

    const cacheable = method === "GET" && url.pathname === "/truth-boundary";
    const cache = caches.default;
    const cacheKey = new Request(originUrl.toString(), { method: "GET" });

    if (cacheable) {
      const cached = await cache.match(cacheKey);
      if (cached) {
        const response = new Response(cached.body, cached);
        response.headers.set("X-iEdge-Verification", "CLOUDFLARE_ACTIVE");
        response.headers.set("X-iEdge-Cache", "HIT");
        return response;
      }
    }

    const upstream = await fetch(originUrl, {
      method,
      headers,
      body: method === "GET" ? undefined : request.body,
    });

    const response = new Response(upstream.body, upstream);
    response.headers.set("X-iEdge-Verification", "CLOUDFLARE_ACTIVE");
    response.headers.set("X-iEdge-Timestamp", headers.get("X-iEdge-Timestamp"));
    response.headers.set("X-iEdge-Cache", cacheable ? "MISS" : "BYPASS");

    if (cacheable && upstream.ok) {
      response.headers.set("Cache-Control", "s-maxage=60");
      ctx.waitUntil(cache.put(cacheKey, response.clone()));
    }

    return response;
  },
};
