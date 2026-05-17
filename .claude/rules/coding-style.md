---
description: Coding style guide for TypeScript and React files
paths: 
 - "src/**/*.{ts,tsx}"
---

# Frontend Coding Style

## Color System

All colors are defined as CSS custom properties in `src/styles/global.css` and mapped to Tailwind utilities via `@theme inline`. Always use these tokens — never hardcode color values.

### Enforcement

This rule is **enforced by ESLint** (`no-raw-tailwind-colors` in `eslint.config.mjs`).
The rule checks `className` props for raw Tailwind color utilities:

- **Banned prefixes**: `text-`, `border-`, `fill-`, `stroke-` combined with named colors (`zinc`, `gray`, `slate`, `red`, etc.)
- **Exception**: `bg-white` / `bg-black` are allowed — canvas node editors intentionally use explicit backgrounds

### Usage Guidelines

**Avoid raw Tailwind color classes.** Do not use:

- `text-zinc-*` / `border-zinc-*` / `text-slate-*` etc.
- `bg-[#...]` / `text-[#...]` inline hex values

**Always use theme-defined tokens:**

- Use `bg-background` instead of `bg-zinc-900`
- Use `border-border` instead of `border-zinc-600`
- Use `text-foreground` instead of `text-zinc-100`
- Use `text-muted-foreground` for secondary/subtle text

**Adding new colors.** Define it as a CSS custom property token in `src/styles/index.css` under the `@theme inline` block, then use the corresponding Tailwind utility class. Do not introduce ad-hoc Tailwind color utilities inline.

### Global CSS Variable Tokens

| Token | Tailwind class | Usage |
|-------|---------------|-------|
| `--background` | `bg-background` | Page/canvas background |
| `--foreground` | `text-foreground` | Primary text |
| `--card` | `bg-card` | Card surfaces |
| `--card-foreground` | `text-card-foreground` | Card text |
| `--muted` | `bg-muted` | Subtle fills |
| `--muted-foreground` | `text-muted-foreground` | Secondary/placeholder text |
| `--primary` | `bg-primary` / `text-primary` | Primary action color |
| `--primary-foreground` | `text-primary-foreground` | Text on primary |
| `--secondary` | `bg-secondary` | Secondary elements |
| `--accent` | `bg-accent` | Accent fills |
| `--destructive` | `bg-destructive` | Danger/error states |
| `--border` | `border-border` | Default borders |
| `--input` | `border-input` | Input borders |
| `--ring` | `ring-ring` | Focus rings |

Usage:

- Background of primary CTA buttons during active/running states
- Progress indicators or status badges for in-progress processes
