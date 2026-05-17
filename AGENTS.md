# ComfyUI Easy Media

## Tech Stack

- **Backend**: Python, using comfyui-nodes-** skills to develop.
- **Frontend**: React v19, shadcn/ui + Tailwind CSS v4 for components, Lucide for icons, Bun for package manager and build, Vitest for testing.

---

## Build, Test, and Development Commands

### Adding shadcn/ui components

```bash
# From repo root
bunx shadcn add <component-name>
```

## Build

```bash
# Dev build (unminified, outputs to dist/dev) — use during normal development
bun run dev               # watch mode with hot reload → dist/dev
bun run build             # one-shot dev build → dist/dev

# Release build (minified, outputs to dist/release) — REQUIRED before git commit
bun run build:release     # production build → dist/release
```

## Code Style

### Backend

- **Reuse utils first** — Before writing new code, check `utils/` for existing utility functions; if none exists, add it there instead of duplicating code
- **File naming** — `kebab_case.py` for nodes、utils、modules; `PascalCase.py` for classes
- **Type hints** — Use type hints for all public methods and function parameters
- **Error handling** — Use `try/except` to explicitly catch exceptions; never swallow exceptions silently


### Frontend

- **TypeScript first** — strict mode, no `any` without reason
- **File naming** — `PascalCase.tsx` for components, `camelCase` for dir, `kebab-case.ts` for modules
- **Import aliases** — use `@/*` for `src/` paths
- **React components** — functional only, hooks-based
- **Never use raw HTML elements** for interactive controls — use shadcn/ui equivalents (`<Button>` not `<button>`, `<Input>` not `<input>`, `<Textarea>` not `<textarea>`, `<Select>` not `<select>`). Exception: `src/components/ui/**` (the shadcn/ui primitives themselves may use raw elements)
- **Error handling** — always handle errors explicitly; never swallow exceptions silently

---