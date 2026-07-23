function assetRequest(request, pathname) {
  const url = new URL(request.url);
  url.pathname = pathname;
  return new Request(url, request);
}

function candidatePaths(pathname) {
  if (pathname === "/") {
    return ["/index.html"];
  }

  const paths = [pathname];
  if (!pathname.includes(".")) {
    paths.push(`${pathname}.html`, `${pathname}/index.html`);
  }

  paths.push("/404.html");
  return paths;
}

function withCacheHeaders(response) {
  const headers = new Headers(response.headers);
  if (!headers.has("cache-control")) {
    headers.set("cache-control", "public, max-age=300");
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

const worker = {
  async fetch(request, env) {
    const assets = env.ASSETS;
    if (!assets?.fetch) {
      return new Response("Static assets are unavailable.", { status: 500 });
    }

    const url = new URL(request.url);
    for (const pathname of candidatePaths(url.pathname)) {
      const response = await assets.fetch(assetRequest(request, pathname));
      if (response.status !== 404 || pathname === "/404.html") {
        return withCacheHeaders(response);
      }
    }

    return new Response("Not found", { status: 404 });
  }
};

export default worker;
