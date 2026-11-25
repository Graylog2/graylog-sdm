# 0007. MadCap Flare project in this repo

Status: accepted
Date: 2026-11-25

## Context
ADR 0003 assumed the MadCap Flare project lived in a separate repo and left delivery of the generated HTML to it out of scope. The docs team has now added the Flare project to this repo (PR #14): `graylog-sdm.flprj` at the root, project files under `Project/`, and topics and resources under `Content/`. Flare reads topics only from `Content/`, so the generated pages must end up there.

The generated pages also linked `Resources/` at two depths (follow-up F20), because nothing recorded where they sit in the Flare project.

## Decision
- The MadCap plugin writes its output straight into the Flare project, at `Content/SDM/` (`output_dir` in `tools/build_sdm/configs/madcap_html_output.toml`). This replaces `generated/MadcapHtmlOutput/`. There is one committed copy; nothing copies or syncs pages into Flare.
- `Content/SDM/` holds only build output. `check-generated` compares the whole directory, so a hand-written file there, or a generated page edited or re-saved in Flare, fails CI. Hand-written topics and Flare resources go elsewhere under `Content/`.
- Every generated page sits one directory below `Content/SDM/` and links Flare's `Content/Resources/` as `../../Resources`. The plugin takes this from one `resources_path` setting in its config, used by every template and table.
- Flare project files (`graylog-sdm.flprj`, `Project/`, and `Content/` outside `Content/SDM/`) belong to the docs team and are maintained in Flare.
- ADR 0003 still applies, except for where the output is committed and its statement that delivery to Flare is out of scope.

## Consequences
- A source change and the Flare topics it affects land in the same PR, and Flare always builds from current output.
- Moving the pages within the Flare project means changing both `output_dir` and `resources_path`.
- Required CI jobs and their names are unchanged.
