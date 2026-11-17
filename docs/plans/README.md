# Plans

Plans describe intended work. They are not facts about the repo, and they are not decisions; see "Authority" below.

## Layout
- Each active plan has its own directory: `docs/plans/<name>/`.
  - `README.md`: the overview, with the header below and, for multi-step plans, a status table.
  - `NN-<step>.md`: optional per-step plans, usually one per PR.
- Completed and abandoned plans live in `docs/plans/archive/YYYYMMDD-<name>/`.

## Header
A plan's `README.md` starts with:

```
# <Plan title>

Status: active | done | abandoned
Created: YYYY-MM-DD
Tracking: <issue or PR link>
```

Step files carry `Status` and `Tracking`, plus a navigation line:

```
# <Plan title> — PR N of M: <step title>

Status: active | done
Tracking: <PR link>
Overview: `docs/plans/<name>/README.md`. Depends on: <step file or nothing>. Next: <step file or nothing>.
```

## Lifecycle
- **While active.** Each PR that completes a step sets that step file to `Status: done` and updates the status table in `README.md`. Nothing is deleted.
- **Completion.** The final PR:
  1. Records any lasting decisions as ADRs in `docs/decisions/`.
  2. Sets `README.md` to `Status: done`.
  3. Runs `git mv docs/plans/<name> docs/plans/archive/<YYYYMMDD>-<name>`, where the date is the plan's `Created` date (not the completion date).
- **Abandoned.** Archive the same way, with `Status: abandoned` and a one-line reason under the header.

## Authority
- ADRs in `docs/decisions/` are current decisions.
- Active plans are intent. When a plan and the code disagree, the code wins.
- `docs/plans/archive/` is history only. Don't treat it as current guidance unless asked about history.
