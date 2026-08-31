---
name: sync-opencode
description: Deploy the generated OpenCode target tree into an OpenCode config directory with the singular→plural directory rename
user-invocable: true
mode: script-executor
allowed-tools: Bash
---

# Sync OpenCode Skill (project-local)

Deploys the generated OpenCode output at
`target/opencode/` into an OpenCode config directory
(default `~/.config/opencode/`) with the singular→plural directory
rename that OpenCode expects. The pipeline is:

```
marketplace/bundles/  →  target/opencode/  →  ~/.config/opencode/{skills,agents,commands}/
```

The middle hop (`target/opencode/`) is produced by
`marketplace/targets/generate.py --target opencode` or by an explicit
`./pw generate-opencode` invocation. This skill consumes that output as
its source of truth — it does **NOT** read directly from
`marketplace/bundles/`.

This skill is **project-local** (lives under `.claude/skills/`) because
it only makes sense for this meta-project: the plan-marshall repo where
the marketplace bundles are authored. Consumer projects that install
plan-marshall via a distribution ref have nothing to publish and
therefore do not need (and would be confused by) a `/sync-opencode`
slash command.

## Singular → plural rename

The OpenCode emitter writes singular directory names (`skill/`, `agent/`,
`command/`). OpenCode discovers components from plural directory names
(`skills/`, `agents/`, `commands/`). This skill performs the rename on
deploy:

| Source (emitter output) | Destination (OpenCode layout) |
|---|---|
| `skill/{bundle}-{skill}/` | `skills/{bundle}-{skill}/` |
| `agent/{name}.md` | `agents/{name}.md` |
| `command/{bundle}-{skill}.md` | `commands/{bundle}-{skill}.md` |

The `skill/` → `skills/` rename preserves the `{bundle}-{skill}`
namespace on each entry. Agent files are flat-named by OpenCode (no
bundle prefix); command wrappers carry the `{bundle}-{skill}` prefix
from the emitter.

## Deletion boundary

The destination (default `~/.config/opencode/`) is a shared directory
where user-managed skills also live. This skill removes only **managed
entries** — those whose names match the `{bundle}-{skill}` namespace of
the bundles being synced. The boundary:

* **Managed (may be pruned):** `skills/{bundle}-{skill}/` and
  `commands/{bundle}-{skill}.md` where `{bundle}` is one of the bundles
  being synced.
* **Never pruned:** `agents/` (flat namespace, no bundle attribution),
  entries whose names do not match the synced bundle set, entries under
  `skills/` or `commands/` whose names do not match any synced bundle.

With `--bundles NAME`, unselected bundles' entries are preserved — only
the named bundle's managed entries are eligible for pruning.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--source PATH` | optional | Source root. Default: `{cwd}/target/opencode/`. |
| `--target-dir PATH` | optional | Destination directory. Default: `~/.config/opencode/`. |
| `--bundles NAME` | optional | Restrict the sync to a single bundle. Only that bundle's managed entries are deployed; other bundles' existing entries are preserved. |
| `--dry-run` | optional | Print the TOON action list without touching the filesystem. |

## Usage Examples

```bash
/sync-opencode
```

Deploys every bundle from cwd's `target/opencode/` to
`~/.config/opencode/`.

```bash
/sync-opencode --target-dir /tmp/opencode-staging --bundles plan-marshall
```

Scoped deploy: renames and copies only the `plan-marshall` bundle's
skills and commands into a staging directory.

```bash
/sync-opencode --dry-run
```

Lists what would be deployed and removed without touching the filesystem.

## Workflow

### Step 1: Run the deploy engine

Invoke the project-local `sync_opencode.py` directly:

```bash
python3 .claude/skills/sync-opencode/scripts/sync_opencode.py
```

Scoped variant:

```bash
python3 .claude/skills/sync-opencode/scripts/sync_opencode.py \
  --source {cwd}/target/opencode --target-dir {dest} --bundles {name}
```

Dry-run:

```bash
python3 .claude/skills/sync-opencode/scripts/sync_opencode.py --dry-run
```

### Step 2: Inspect the summary

The script's TOON output reports each deployed entry (`kind,name`) and
each removed entry (`kind,name`), plus the aggregate
`deployed_count`, `removed_count`, and `summary_message`.

On `status: error`, inspect `summary_message` for the cause (source
missing, source empty, etc.).

### Step 3: Reload the session (after a deploy that changed agent set)

If the deploy altered the `agents/` directory and the running OpenCode
session must see the new agents, reload the session's plugin set.

## Critical Rules

- Always use `--target-dir` or the default `~/.config/opencode/` — never
  write into `target/opencode/` (the source of truth).
- The deletion boundary is non-negotiable: only managed entries may be
  pruned; agents are never pruned; unmanaged user entries are never
  touched.
- This skill does **NOT** invoke the generator — it consumes
  `target/opencode/` as-is. Regenerate separately before syncing.

## Related

- `/marshall-steward` — project configuration, including target
  generation prompts.
- `project:finalize-step-deploy-target` (phase-6-finalize) — produces
  `target/opencode/`, the input this skill consumes.
- `/sync-plugin-cache` — the Claude-target counterpart.
