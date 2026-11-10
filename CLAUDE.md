# graylog-sdm

This repo is the authoritative source for the Graylog Security Data Model (SDM): field schema, GIM (Graylog Information Model) categories/subcategories/event types, and reserved values. Downstream repos (e.g. graylog-project-illuminate) consume it; they do not edit it.

## Source of truth rules

- Edit SDM definitions only in this repo. Never "fix" SDM content in a downstream repo.
- TODO: list authoritative source paths (e.g. `schema/`, `gim/`).
- TODO: list generated paths that must never be hand-edited, and the command that regenerates them.

## Conventions

- TODO: field naming rules (case, separators, prefixes).
- TODO: GIM category/subcategory/event type naming and code rules.
- TODO: reserved value rules.

## Change policy

- Classify every change as **additive**, **deprecation**, or **breaking**.
- Breaking changes (rename, removal, type change) require: TODO (version bump, changelog entry, downstream notice).
- Never reuse a removed field name or GIM code for a different meaning.

## Before claiming work is done

- TODO: run `<validate command>` and confirm it passes.
- TODO: run `<test command>`.
