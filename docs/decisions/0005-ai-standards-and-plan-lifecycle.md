# 0005. AI standards and plan lifecycle

Status: accepted
Date: 2026-11-17

## Context
The repo is worked on with Claude (development and review) and GitHub Copilot (review). Standards must work for both without duplicating content that drifts. Plans written for agents tend to linger and get mistaken for current guidance.

GitHub documentation checked on 2026-11-17:
- Copilot code review reads `.github/copilot-instructions.md` and path-specific `.github/instructions/*.instructions.md` files (`applyTo` frontmatter). A file can opt out of code review with `excludeAgent: "code-review"`.
- Size: the 4000-character limit for code review instruction files was removed on 2026-06-12 (GitHub changelog, "Copilot code review: new configurations and controls"). The current guidance is to keep any single instruction file under about 1,000 lines; very long files may cause instructions to be overlooked.
- `AGENTS.md`: the "Customize code review" tutorial now lists `AGENTS.md` as a supported instruction file for code review. `CLAUDE.md` is not documented as read by code review.
- Code review reads instructions from the PR's head branch, so instruction changes can be tested in the same PR.

## Decision
- `AGENTS.md` is canonical for development standards for all agents and humans.
- `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md` hold review standards, written out inline. Copilot does not reliably follow links to other files, so review rules are not delegated by reference. Although code review now reads `AGENTS.md`, review-specific rules stay in the Copilot files, which are scoped by path and kept short.
- `CLAUDE.md` contains only imports: `@AGENTS.md` and `@.github/copilot-instructions.md`.
- Each plan gets its own directory, `docs/plans/<name>/`, with a `README.md` header (`Status`, `Created`, `Tracking`).
- When a plan is done or abandoned, `git mv` its directory to `docs/plans/archive/YYYYMMDD-<name>/`, where the date is the plan's `Created` date.
- Lasting decisions are recorded in ADRs before the plan is archived.
- The archive is history only and has no authority.

## Consequences
- Claude loads both development and review standards; Copilot review gets the review standards (and now `AGENTS.md`) without following links.
- Some rules appear in both `AGENTS.md` and the Copilot files. Keep them in sync when changing either.
- Instruction files have no hard size limit today; keep them short anyway.
