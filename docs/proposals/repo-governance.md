# Proposal: repository governance

Status: proposed; required checks partly implemented (2026-11-25)
Date: 2026-11-20

The SDM is a data contract: Illuminate's pipelines, lookups and content depend on it. This proposal covers the GitHub settings and files that keep changes to it reviewed and checked. Nothing here is implemented; each item needs a decision and a repo admin.

## Current state

Checked on 2026-11-20 through the rulesets API. A classic branch-protection rule, if any, isn't visible there and needs an admin to check.

A ruleset on `main`:
- requires a pull request with 1 approval
- requires review threads to be resolved before merging
- blocks force pushes and branch deletion
- doesn't dismiss approvals when new commits are pushed, and doesn't require approval of the most recent push
- allows merge, squash and rebase merges
- has **no required status checks**

CI (`.github/workflows/ci.yml`) runs `data-lint`, `generated-fresh` and `python-qa` on every PR into `main`, but a failing run doesn't block a merge.

## Branch protection on `main`

Proposed additions to the ruleset:

1. **Required status checks:** `data-lint`, `generated-fresh` and `python-qa`.
   - Implemented 2026-11-25 for `data-lint` and `python-qa`, with the up-to-date requirement. `generated-fresh` waits for the Flare integration (follow-up F3).
   - Select them by job name. If a required job is renamed, the rule keeps waiting for the old name, and every PR shows it as expected but never reported, so nothing can merge. An intentional rename has to update the ruleset at the same time. `AGENTS.md` says to keep the names stable.
   - Require branches to be up to date before merging. `validate` compares against the PR's base, so a PR checked against an older `main` can pass and still add a violation once merged. The repo's PR volume is low, so the extra rebases cost little.
   - Without required checks, a PR retargeted to `main` that never ran CI can merge with only an approval.
2. **Human approval:** keep 1 approval from someone other than the author. AI reviews (Copilot, Claude) are advisory and never count as the approval.
3. **Approval after the last push:** consider requiring it. Today an approval carries over later pushes, so commits added after the review merge unreviewed. The cost is a re-approval after every fix.
4. **Merge methods:** consider allowing rebase only, or rebase and squash. The migration PRs used rebase-merge, so that commits such as a mechanical reformat stay separate in history. A merge commit adds nothing to a linear history.

These cover the "branch protection now" part of follow-up F3.

## CODEOWNERS

Add `.github/CODEOWNERS`, requiring a review from the owning team for:

```
/src/sdm/                       <sdm-owners>
/tools/                         <tool-owners>
/.github/                       <repo-admins>
/AGENTS.md                      <repo-admins>
/CLAUDE.md                      <repo-admins>
```

- `src/sdm/` needs owners who can judge field classification and change classification, not just code.
- `.github/` covers the workflow and the Copilot instruction files, which decide what CI and AI review enforce.
- The placeholders need real team names. Then turn on "Require review from Code Owners" in the ruleset.

## Pull request template

Add `.github/pull_request_template.md`:

```markdown
## Summary

## Change type (SDM changes)
- [ ] No SDM change
- [ ] Additive
- [ ] Deprecation
- [ ] Breaking (rename, removal or type change): `sdm_version` bumped

## Checklist
- [ ] `uv run build-sdm validate --base-ref origin/main` reports no new errors
- [ ] `generated/` regenerated with `uv run build-sdm build` and committed
- [ ] Golden snapshots refreshed if plugin output changed on purpose
- [ ] Breaking change: `sdm_version` bumped in `src/sdm/config/sdm_version.config.toml`

## If this completes a plan
- [ ] Lasting decisions recorded in an ADR
- [ ] Plan set to `Status: done` and moved to `docs/plans/archive/<Created YYYYMMDD>-<name>/`
```

CI already enforces the validate and generated items. They stay in the template as a reminder before pushing. The change type and the plan items need a human.

## Plan lifecycle check (optional)

A small script, run as a step in `data-lint` or as its own job, that fails if:
- any `docs/plans/*/README.md` outside `archive/` has `Status: done` or `Status: abandoned` (a finished plan that wasn't archived)
- any directory in `docs/plans/archive/` doesn't match `^\d{8}-[a-z0-9-]+$`
- an archived plan's date prefix doesn't match the `Created:` date in its `README.md`

This enforces the lifecycle in `docs/plans/README.md` (ADR 0005) instead of leaving it to review.

## Issue templates

Illuminate's `.github/ISSUE_TEMPLATE/` has bug report, change request, documentation, general and new content forms, with `blank_issues_enabled: false`. Adapted for this repo:

| Template | For | Fields |
|---|---|---|
| SDM change request | New or changed fields, categories, subcategories or event types | What and why, affected entries, proposed change type (additive, deprecation, breaking), affected Illuminate content |
| Field classification | Moving a field between required, recommended and optional | Field, subcategory, current and proposed tier, evidence (event definitions, alerts, widgets that use it) |
| build-sdm bug | Wrong output or a failing command | Command, expected and actual result, version (commit) |
| General | Anything else | Description |

Keep `blank_issues_enabled: false` so every issue starts from a form.

## Decisions needed

1. Required checks, and whether branches must be up to date.
2. Whether to require approval of the most recent push.
3. Allowed merge methods.
4. CODEOWNERS teams.
5. Whether to add the plan lifecycle check.
