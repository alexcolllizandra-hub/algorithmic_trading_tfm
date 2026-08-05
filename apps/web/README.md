# perp-lab research platform — web (Next.js + TypeScript)

Read-only frontend for the perp-lab quantitative research platform. It renders
run artifacts served by the FastAPI quantitative API (`/api/v1`). No trading,
search or backtesting logic is reimplemented here — the Python API is the sole
authoritative adapter over the artifact directory.

## Requirements

- Node.js 22+
- The quantitative API running (default `http://localhost:8000/api/v1`)

## Install

```bash
cd apps/web
npm ci
```

## Develop

```bash
# API base is read from NEXT_PUBLIC_API_BASE (inlined at build time).
$env:NEXT_PUBLIC_API_BASE="http://localhost:8000/api/v1"   # PowerShell
npm run dev            # http://localhost:3000
```

## Quality gate (frontend)

```bash
npm run lint            # ESLint (next lint)
npm run format:check    # Prettier check
npm run typecheck       # tsc --noEmit
npm run test            # Vitest unit + contract tests
npm run build           # Next.js production build
```

## End-to-end (Playwright)

E2E runs against a **production build** served on a dedicated port
(`E2E_PORT`, default `3199`) using a same-origin **mock API** (`/mock-api/v1`)
backed by clearly-labelled synthetic fixtures — no Python service required.
`NEXT_PUBLIC_*` is inlined at build time, so the app must be built first with the
mock base:

```bash
$env:NEXT_PUBLIC_API_BASE="/mock-api/v1"
npm run build
npx playwright test
```

## Screenshots of the live platform

With the API (real artifacts) on `:8000` and the web app on `:WEB_BASE`:

```bash
$env:WEB_BASE="http://localhost:3000"
$env:API_BASE="http://localhost:8000/api/v1"
node scripts/screenshots.mjs   # -> docs/platform/screenshots/
```

## Notes

- `output: "standalone"` is enabled for the Docker image (`node server.js`).
  `next start` prints a warning under standalone output but still serves the
  build for local E2E.
- Fixtures under `src/mock/` are **synthetic** and used only for tests; every
  run surfaced in the UI carries a run-kind badge (synthetic smoke vs
  development) so fixtures can never be confused with research results.
