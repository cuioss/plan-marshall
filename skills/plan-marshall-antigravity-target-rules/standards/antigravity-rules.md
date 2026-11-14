# Google Antigravity Target Operational Rules

Guidelines and operational invariants for AI assistants operating within Google Antigravity (AGY) environments.

## 1. Tool Invariants & Mapping

In Antigravity environments, use native tool capabilities instead of shell commands or external workarounds:

| Action / Capability | Native Antigravity Tool | Operational Constraints |
|---------------------|------------------------|-------------------------|
| Shell execution | `run_command` | Sandboxed by default (`BypassSandbox: false`). Set `Cwd` within workspace. Never `cd`. |
| View file contents | `view_file` | Supports text and binary files (offset/line slicing). Do not use `cat`, `head`, `tail`, or pagers. |
| Create / overwrite files | `write_to_file` | Explicit `Overwrite` or `Append`. Do not use shell redirection or `touch`. |
| Edit existing files | `replace_file_content` | Single contiguous chunk replacement with exact text matching. |
| Find files by pattern | `find_by_name` | Glob pattern search over workspace files. |
| Content regex search | `grep_search` | Regular expression search over codebase files. |
| Solicit user input | `ask_question` | Interactive multi-choice modal. Do not ask trivial yes/no or add write-in options. |
| Background tasks | `manage_task` | Monitor, status, or cancel asynchronous jobs. |
| Subagent delegation | `invoke_subagent` | Launch concurrent subagents. Use `send_message` for inter-agent communication. |
| Timers & recurring jobs | `schedule` | One-shot timers or cron expressions. Never use `sleep` in bash. |
| Web browsing / search | `search_web`, `read_url_content` | External research and static page fetching. |

## 2. Terminal Sandbox & Command Discipline

- **Single command per call**: Every `run_command` invocation must execute exactly one command. Never use `&&`, `;`, `|`, trailing `&`, newlines, loops, subshells (`$()`), or heredocs.
- **Working directory**: The `Cwd` parameter must remain inside the active workspace. Never run `cd`.
- **No shell file inspection**: Never invoke `ls`, `cat`, `grep`, `find`, or git `grep` via bash. Use dedicated tool calls (`view_file`, `find_by_name`, `grep_search`) or structured queries (`architecture`).
- **Resolve build commands**: never hard-code a build or format command on this harness. Resolve it through `plan-marshall:manage-architecture:architecture resolve` and run the returned `executable`, so a build uses the command the architecture declares for the module. Formatting rides the resolved `quality-gate`; there is no standalone `format` canonical, so do not invent `architecture resolve --command format`.
- **A missing plugin prefix is a stop**: `No plugin found for prefix …` means the project does not use that plugin. Report it and stop — never retry the same goal fully qualified (`./mvnw`, an absolute plugin path, a different wrapper).
- **Sandbox default**: Keep `BypassSandbox: false` unless the user explicitly grants elevated execution permissions.

## 3. Reactive Task & Subagent Lifecycle

- **No polling loops**: Never poll `manage_task status` or query subagents in a sleep loop.
- **Automatic wakeup**: The Antigravity environment automatically wakes the agent upon task completion, subagent response, or timer expiry. When an asynchronous operation is running, conclude your turn or perform other work; do not block or loop.
- **Inter-agent communication**: Use `send_message` strictly for communicating with subagents by conversation ID. Never use `send_message` to communicate with the user; user communication is done via normal response text.

## 4. `.plan/` State & Script-Only Access

- **Script-only access**: Never read, write, or modify files in `.plan/` directly through filesystem tools or editor tools.
- **Executor pattern**: All `.plan/` operations must route through the generated executor:
  ```bash
  python3 .plan/execute-script.py {bundle}:{skill}:{script} [args...]
  ```
- **Temporary directory**: Store all temporary and generated scratch files in `.plan/temp/` to ensure deterministic cleanup and permission compliance.

## 5. Artifact Isolation

- **Artifact directory**: Conversation-specific artifacts, visualizations, and user-facing reports belong in `<appDataDir>/brain/<conversation-id>/`.
- **Workspace cleanliness**: Do not pollute project source trees or version-controlled directories with transient assistant artifacts or UI mockups.

## 6. Zero-Token Native Rule Delivery

When plan-marshall is installed into a workspace via `./install.sh --workspace` or `./install.sh --emit-rules`, this specification is automatically deployed to:
```text
<workspace>/.agents/rules/plan-marshall-target-rules.md
```
Antigravity automatically discovers and loads workspace rules into assistant context, delivering operational compliance with zero runtime tool calls.

## 7. Standing-Rules Bridge & Drift Detection

- **Two distinct files**: the deployed specification above (`.agents/rules/plan-marshall-target-rules.md`) is written by the installer (`./install.sh --workspace` / `--emit-rules`); project setup writes the standing-rules bridge to its own file, `.agents/rules/plan-marshall-standing-rules.md`, and never into the deployed specification file.
- **Bridge source**: the bridge CARRIES the rules of the repository's `CLAUDE.md`, generated from it at project setup. The file records `source-sha256` — the content hash of the baseline it was generated from — and the baseline stays authoritative; edit `CLAUDE.md`, then re-run setup.
- **Drift signal**: re-setup compares the recorded hash with the current baseline's content. A changed baseline reports drift (`baseline_changed`); a bridge without a recorded hash reports `source_hash_missing`; a foreign or unmarked file reports `marker_mismatch`. A change of timestamp alone is not drift. A baseline that exists but cannot be decoded reports `baseline_unreadable` as drift, and a bridge whose bytes are not UTF-8 reports `bridge_unreadable`; neither raises. With no baseline at all, a bridge that still carries rules reports `baseline_missing` as drift and the marker-only stub the writer produces is current.
- **Reconcile path**: re-setup re-runs the bridge writer, which heals a drifted, outdated or missing bridge in the bridge file only and leaves a current bridge untouched. Setup reports the drift verdict it found BEFORE healing, and it reports drift whenever the writer replaced an existing bridge that differed from what it wrote: a setup that rewrote an existing bridge never reports a clean bridge, while a first write that creates the bridge is clean. A pre-heal `in_sync` that the writer still replaced — a hand-edited body whose recorded hash matches — reports `bridge_body_replaced`, and a write the workspace refused reports `bridge_write_failed`. A bridge stub found in the deployed specification file is a clobber by an older setup — restore it by re-running `./install.sh --emit-rules`.

