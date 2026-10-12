# Vox Darija — frontend

React + TypeScript + Vite + Tailwind + Zustand.

```bash
pnpm install
pnpm dev      # Vite dev server on :5173 (proxies /api to :8001)
pnpm test     # vitest
pnpm lint     # oxlint
pnpm build    # typecheck + production build
```

- `src/schema.ts` — Zod mirror of the backend schema (single source of truth).
- `src/store.ts` — Zustand store (segments, selection, undo/redo, upload).
- `src/i18n.ts` — Arabic/English UI strings + RTL layout.

Run the whole stack from the repo root with `make dev-all` (mock ASR) or
`make dev-mac` + `make frontend` (real model).
