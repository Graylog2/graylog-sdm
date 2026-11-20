# Proposal: AI tooling setup for Claude and Copilot

Status: proposed
Date: 2026-11-20

The repo is developed with Claude and reviewed by Claude and GitHub Copilot. ADR 0005 decides where the standards live. This proposal covers how each tool is set up to use them. Nothing here is implemented.

## Shared

### File map

| File | Holds | Read by |
|---|---|---|
| `AGENTS.md` | Development standards | Claude (through `CLAUDE.md`); Copilot code review, which now lists `AGENTS.md` as a supported instruction file (ADR 0005) |
| `CLAUDE.md` | Only the imports `@AGENTS.md` and `@.github/copilot-instructions.md` | Claude |
| `.github/copilot-instructions.md` | Repo-wide review standards | Copilot code review; Claude (through `CLAUDE.md`) |
| `.github/instructions/sdm-data.instructions.md` | Review rules for `src/sdm/**` | Copilot code review, for matching files |
| `.github/instructions/python.instructions.md` | Review rules for `tools/**` and `tests/**` | Copilot code review, for matching files |

Claude doesn't load the path-scoped `.instructions.md` files on its own. `AGENTS.md` points to `sdm-data.instructions.md` for the full classification rules, so Claude reads it when it works on SDM data.

### Where a new standard goes

Add each standard to exactly one file, chosen by who it's for:
- Development standards, for anyone changing the repo: `AGENTS.md`.
- Review standards that apply everywhere: `.github/copilot-instructions.md`.
- Review standards for certain paths: the matching `.github/instructions/*.instructions.md`, or a new one with its own `applyTo`.

A few rules appear in both `AGENTS.md` and the Copilot files on purpose, because Copilot doesn't reliably follow links (ADR 0005). Change them in both places together.

## Claude

### Project settings

`.claude/settings.json` today allows read-only `git` and `gh` commands, asks before `gh pr comment` and `gh api`, and denies `gh pr merge`, `gh pr review` and `gh pr ready`. Proposed additions:

```json
{
  "permissions": {
    "allow": [
      "Bash(uv run build-sdm:*)",
      "Bash(uv run pytest:*)",
      "Bash(uv run ruff:*)",
      "Bash(uv run mypy:*)",
      "Bash(uv run taplo:*)"
    ],
    "deny": [
      "Edit(generated/**)",
      "Write(generated/**)"
    ]
  }
}
```

- The allow rules cover the commands in `AGENTS.md`. They run only repo code and its locked dependencies.
- The deny rules stop Claude from hand-editing generated output. `build-sdm build` still writes it, because the build runs as a shell command, not through Edit or Write.
- `uv run build-sdm build` writes into the repo. That's expected; review the diff before committing.

### Validate after edits (optional)

A `PostToolUse` hook that runs `uv run build-sdm validate --base-ref origin/main` after an Edit or Write under `src/sdm/`, and shows Claude the errors. Claude sees a new violation as soon as it makes it, not when CI fails.

- `validate` takes about 2 seconds, so filter by path: a hook that runs on every edit slows down unrelated work.
- Show only errors, not the existing warnings, or the output buries what matters.
- `origin/main` may be stale locally. The hook shouldn't fetch; an occasional false error is better than a network call on every edit.

### Claude GitHub Action (optional)

Claude Code's GitHub Action can review PRs. It reads `CLAUDE.md`, so it applies the same review standards as Copilot. It would complement Copilot, with a different model reading the same rules. It needs an API key stored as a repo secret, and adds cost per PR.

## Copilot

- **Automatic review:** turn on automatic Copilot code review for PRs into `main`, in the repo's Copilot settings or as a ruleset rule. Reviews are requested by hand today.
- **Advisory only:** Copilot's review never counts as the required approval (see `docs/proposals/repo-governance.md`).
- **Re-check the documentation** about once a quarter, and record changes in ADR 0005:
  - Size limits: the 4,000-character limit for code review instruction files was removed in 2026-06. Keep the files short anyway.
  - `AGENTS.md` support: code review now lists `AGENTS.md`. If that proves reliable, consider moving rules that are repeated in both places into `AGENTS.md` only, and keeping the Copilot files for review-only, path-scoped rules.

## Maintenance

The instruction files decide what AI tools enforce, so changes to them need review by owners. The governance proposal's CODEOWNERS entry for `/.github/`, `/AGENTS.md` and `/CLAUDE.md` covers them.

## Decisions needed

1. Whether to adopt the proposed `.claude/settings.json` additions.
2. Whether to add the validate hook.
3. Whether to add the Claude GitHub Action.
4. Whether to turn on automatic Copilot review.
