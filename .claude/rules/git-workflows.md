# Git Workflow

## Branch Strategy

### Creating Branches for Features
- Switch to `main` and ensure it is up-to-date (pull if needed) before creating a new branch
- If a branch with the same feature already exists, switch to it instead of creating a new one
- For new features and adjustments (excluding README, AI assistant files, docs, etc.), always create a branch from `main`

### Branching from Issues
- When fixing code mentioned in an issue, create a branch specifically for that issue

### Pull Request Creation
- After pushing a branch to remote, create a corresponding PR
- If a similar feature PR is already open, ask the user whether to contribute to that PR instead

### Before Switching or Committing Branches
- Check if the current branch is behind `main` with conflicting changes
- If so, rebase `main` into the current branch before committing or switching

## Commit Rules

- **Separate commits by feature/responsibility**: Group changes by feature or responsibility area, not by file type alone. Example:
  - `feat: add MediaLoader node` — all files for this feature (node class, utils, etc.)
  - `refactor: extract FFmpeg helpers` — refactor shared utilities
  - `feat: add thumbnail mode to ImagePreview` — UI for a specific feature
  - `feat: add zh-CN translations for ImageLoader` — localization for a specific node/feature
- **dist directory commits separately**: Changes to the dist directory should not be mixed with other feature commits. After frontend builds, submit dist changes as a separate commit: `ci: update bundled frontend assets`
- **Use `git diff` to guide grouping**: Before committing, run `git diff` to see all changes and group files that logically belong together into the same commit
- **Frontend changes require build**: Before any git commit that modifies frontend code (`.tsx`, `.ts`, CSS, or assets), you MUST run `cd frontend && bun run build:release` first to update the bundled output in `dist/release`
- Commit message format follows standard convention (see below)
```
<type>: <description>

<optional body>
```

Type: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

Note: Attribution disabled globally via ~/.claude/settings.json.

## Pre-Push Review

Before pushing code, run code reviews using specialized agents:

| Review Type | Agent | When to Run |
|-------------|-------|-------------|
| React/Frontend | `react-review` | Frontend code changes (`.tsx`, `.ts` in `frontend/`) |
| Python/Backend | `python-review` | Backend code changes (`.py` files) |
| Localization | `localize-review` | i18n changes or new/translated strings |

**Workflow:**
1. Run all applicable reviews before pushing
2. Address any issues found
3. Re-run review if major changes made
4. Only push after all reviews pass

**Example commands:**
```bash
# Frontend review
claude --print "Use react-review agent to review frontend changes"
# Backend review
claude --print "Use python-review agent to review backend changes"
# Localization review
claude --print "Use localize-review agent to review i18n changes"
```

## Pull Request Workflow

When creating PRs:
1. Analyze full commit history (not just latest commit)
2. Use `git diff [base-branch]...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan with TODOs
5. Push with `-u` flag if new branch

