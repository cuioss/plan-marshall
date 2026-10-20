# OpenCode Target Operational Rules

Guidelines and operational invariants for AI assistants operating within OpenCode environments.

## 1. Tool Invariants & Mapping

In OpenCode environments, use OpenCode's native tool capabilities:

| Action / Capability | Native OpenCode Tool | Operational Constraints |
|---------------------|----------------------|-------------------------|
| Shell execution | `shell` | Single command per call. Never chain commands. |
| View file contents | `read` | Read file contents directly; do not use `cat`, `head`, or `tail`. |
| Write / overwrite files | `write` | Create or overwrite files; do not use shell redirection or `touch`. |
| Edit existing files | `edit` | Surgical edits to existing file content. |
| Find files by pattern | `glob` | Find files matching pattern within workspace. |
| Search file content | `grep` | Search file content across workspace paths. |
| Solicit user input | `question` | Interactive user prompt. |
| Background tasks | `subagent` | Run subtasks asynchronously. |
| Invoke skill | `skill` | Load or invoke a skill into current context. |
| Fetch URL content | `webfetch` | Retrieve web pages or external resources. |

## 2. Deployed Flat Layout

OpenCode deploys skills in a flat directory namespace to support single-level lookup:

- **Global deployment**: `~/.config/opencode/skills/{bundle}-{skill}/`
- **Workspace deployment**: `.opencode/skills/{bundle}-{skill}/`
- **Identity frontmatter**: Each emitted skill carries identifying metadata in its frontmatter:
  ```yaml
  metadata:
    bundle: plan-marshall-opencode
    skill: target-rules
  ```
- **Internal references**: The subdirectories and loose files of the source skill sit directly under `{bundle}-{skill}/` — `workflow/` as much as `standards/`, `references/`, `templates/` or `scripts/`, which are examples and not the complete set. All intra-skill references resolve relative to this directory.

## 3. Command & `.plan/` Discipline

- **Single command per call**: Every `shell` invocation must execute exactly one command. Never use `&&`, `;`, `|`, trailing `&`, newlines, loops, subshells (`$()`), or heredocs.
- **Working directory**: Execute commands from the workspace root. Do not propose `cd` commands.
- **No shell file inspection**: Use native tools (`read`, `glob`, `grep`) instead of `ls`, `cat`, or shell grep.
- **Script-only access to `.plan/`**: Never read, write, or modify `.plan/` files directly. All `.plan/` operations route through the executor:
  ```bash
  python3 .plan/execute-script.py {bundle}:{skill}:{script} [args...]
  ```
- **Temporary directory**: Store all temporary and generated files in `.plan/temp/`.

## 4. Zero-Token Native Rule Delivery

When plan-marshall is installed into an OpenCode workspace via `./install.sh --workspace` or `./install.sh --emit-rules`, this specification is automatically deployed to:
```text
<workspace>/.opencode/rules/plan-marshall-target-rules.md
```
OpenCode automatically discovers and loads workspace rules into assistant context, delivering operational compliance with zero runtime tool calls.

## 5. Standing-Rules Bridge & Drift Detection

- **Two distinct files**: the deployed specification above (`.opencode/rules/plan-marshall-target-rules.md`) is written by the installer (`./install.sh --workspace` / `--emit-rules`); project setup writes the standing-rules bridge to its own file, `.opencode/rules/plan-marshall-standing-rules.md`, and never into the deployed specification file.
- **Bridge source**: the bridge CARRIES the rules of the repository's `CLAUDE.md`, generated from it at project setup. The file records `source-sha256` — the content hash of the baseline it was generated from — and the baseline stays authoritative; edit `CLAUDE.md`, then re-run setup.
- **Drift signal**: re-setup compares the recorded hash with the current baseline's content. A changed baseline reports drift (`baseline_changed`); a bridge without a recorded hash reports `source_hash_missing`; a foreign or unmarked file reports `marker_mismatch`. A change of modification time alone is not drift.
- **Reconcile path**: re-setup re-runs the bridge writer, which heals a drifted, outdated or missing bridge in the bridge file only and leaves a current bridge untouched. Setup reports the drift verdict it found BEFORE healing, so a setup that rewrote the bridge never reports a clean bridge. A bridge stub found in the deployed specification file is a clobber by an older setup — restore it by re-running `./install.sh --emit-rules`.
- **Dispatch conditional**: the `subagent`-tool subagent dispatch fires only when the tool is available in the envelope; otherwise take the explicit logged inline branch with usage unknown.

## 6. Build & Plugin Resolution

- **Resolve, never guess**: build and format commands resolve through `plan-marshall:manage-architecture:architecture resolve`, and the returned `executable` is what runs. Formatting rides the resolved `quality-gate`; there is no standalone `format` canonical, so `architecture resolve --command format` is not a thing to invent.
- **A missing plugin prefix is a stop.** `No plugin found for prefix …` means the project does not use that plugin. Report it and stop — do not retry the same goal fully qualified (`./mvnw`, an absolute plugin path) to get past the failure.
