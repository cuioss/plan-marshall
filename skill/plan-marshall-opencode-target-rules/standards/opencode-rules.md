# OpenCode Target Operational Rules

Guidelines and operational invariants for AI assistants operating within OpenCode environments.

## 1. Tool Invariants & Mapping

In OpenCode environments, use OpenCode's native tool capabilities:

| Action / Capability | Native OpenCode Tool | Operational Constraints |
|---------------------|----------------------|-------------------------|
| Shell execution | `bash` | Single command per call. Never chain commands. |
| View file contents | `read` | Read file contents directly; do not use `cat`, `head`, or `tail`. |
| Write / overwrite files | `write` | Create or overwrite files; do not use shell redirection or `touch`. |
| Edit existing files | `edit` | Surgical edits to existing file content. |
| Find files by pattern | `glob` | Find files matching pattern within workspace. |
| Search file content | `grep` | Search file content across workspace paths. |
| Solicit user input | `question` | Interactive user prompt. |
| Background tasks | `task` | Run subtasks asynchronously. |
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

- **Single command per call**: Every `bash` invocation must execute exactly one command. Never use `&&`, `;`, `|`, trailing `&`, newlines, loops, subshells (`$()`), or heredocs.
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
- **Bridge source**: the bridge file is written at project setup from the `CLAUDE.md` baseline (`bridge-version` marker embedded); the baseline stays authoritative.
- **Drift signal**: re-setup compares the marker and modification times — a marker mismatch or a baseline newer than the bridge reports drift (`marker_mismatch`, `baseline_newer`).
- **Reconcile path**: re-setup re-runs the bridge writer, which heals a drifted or missing bridge in the bridge file only and leaves a current bridge untouched. A bridge stub found in the deployed specification file is a clobber by an older setup — restore it by re-running `./install.sh --emit-rules`.
- **Dispatch conditional**: the `task`-tool subagent dispatch fires only when the tool is available in the envelope; otherwise take the explicit logged inline branch with usage unknown.
