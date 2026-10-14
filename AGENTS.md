# Working on PolicyWatch

Work locally by default. The owner chooses when local changes are published by
double-clicking `PUBLISH-TO-GITHUB.bat`. Do not commit, push, or deploy changes
unless the user explicitly requests it in the current task. Local builds and
validation are encouraged and do not require publishing.

The source repository is https://github.com/rjwood11/Policy_Watch and the live
application is https://rjwood11.github.io/Policy_Watch/.

This is a Next.js static export hosted on GitHub Pages. Preserve static-export
compatibility, directory index routes, and support for the Pages repository
prefix. Use `assetPath` from `src/lib/assetPath.ts` for public-file URLs in
browser code; Next.js Link and router navigation apply the prefix themselves.
Local builds default to an empty prefix. Deployments get their prefix from
`actions/configure-pages`.

Run `npm run check` for application changes. When changing URL handling, also
verify a build with `NEXT_PUBLIC_BASE_PATH=/Policy_Watch`, then rebuild without
that variable so the local launcher continues to work at the domain root.

Keep credentials, `.env` files, dependencies, build output, and local Codex
caches out of Git. Data refresh and deployment workflows are intentionally
manual or push-triggered; do not introduce automatic source commits or
scheduled publishing without a user request.
