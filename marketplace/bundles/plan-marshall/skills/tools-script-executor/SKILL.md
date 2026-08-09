---
name: tools-script-executor
description: Universal script execution pattern via execute-script.py proxy
user-invocable: false
mode: knowledge
---

# Script Executor Skill

## Enforcement

**Execution mode**: All marketplace scripts must be executed through the executor proxy.

**Executor is cwd-pass-through. All cwd control is explicit at the call site.** See [standards/cwd-policy.md](standards/cwd-policy.md) for the single uniform cwd-relative resolution rule (ADR-002) and the cwd-unchanged invariant every script obeys.

**Prohibited actions:**
- Do not execute marketplace scripts directly by path; always use the executor notation
- Do not modify `.plan/execute-script.py` manually; regenerate via `/marshall-steward`
- Do not hard-code PYTHONPATH; the executor manages it automatically
- Do not rely on ambient cwd for path resolution inside scripts; follow [standards/cwd-policy.md](standards/cwd-policy.md)

**Constraints:**
- All scripts use `python3 .plan/execute-script.py {notation} {subcommand} {args}`
- Bootstrap pattern is only for first run when executor does not exist yet
- Plan-scoped logging requires `--plan-id` or `--audit-plan-id`
- Plan-metadata scripts resolve `.plan/` via `file_ops.get_base_dir()`, which uses the single uniform cwd walk-up (`set_base_dir()` → `PLAN_BASE_DIR` → nearest ancestor containing `.plan/local`; ADR-002) — main in phases 1-4, the pinned worktree in phase-5+. Worktree-scoped build / CI / Sonar scripts accept either `--plan-id` (auto-resolves the worktree via `manage-status get-worktree-path`) or `--project-dir` (explicit override / escape hatch — the two flags are mutually exclusive); the merge lock is the single main-anchored resolver. See `standards/cwd-policy.md`

---

## Overview

All marketplace scripts are executed through `.plan/execute-script.py`:

```bash
python3 .plan/execute-script.py {notation} {subcommand} {args...}
```

## Notation Format

Script execution notation: `{bundle}:{skill}:{script}`

| Example |
|---------|
| `plan-marshall:manage-files:manage-files` |
| `plan-marshall:build-maven:maven` |
| `plan-marshall:tools-integration-ci:ci` |

## Examples

```bash
# Document operations (typed documents) — path-allocate pattern:
# `request create` emits a metadata-only stub and returns the absolute `path`;
# the caller writes body content directly via its native Write tool.
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request create --plan-id EXAMPLE-PLAN --title "My Task" --source description
# → parse `path` from the TOON output, then: Write(path, "Task details")
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read --plan-id EXAMPLE-PLAN

# File operations (generic files)
# Inline --content is reserved for single-line scalar values with no leading "#".
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write --plan-id EXAMPLE-PLAN --file notes-tag.txt --content "single line value with no newlines and no leading hash"

# For multi-line content (markdown, TOON, JSON) OR any payload whose first line begins with "#",
# stage the body to .plan/temp/{plan_id}/ via the Write tool first, then pass --content-file. See manage-files/SKILL.md § Enforcement for the binding rule.
# Write(.plan/temp/EXAMPLE-PLAN/notes.md) with the multi-line markdown body
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write --plan-id EXAMPLE-PLAN --file notes.md --content-file .plan/temp/EXAMPLE-PLAN/notes.md

# Build operations
python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "clean verify"

# References operations
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set --plan-id EXAMPLE-PLAN --field foo --value bar
```

## Error Handling

The executor standardizes error output:

```text
SCRIPT_ERROR    {notation}    {exit_code}    {summary}
```

### Pre-spawn invocation rejection

A dispatch whose verb path or flags the target script cannot accept is refused
**before any subprocess starts**. Without this, an invented subcommand surfaced
only as a raw argparse `exit_code: 2` with usage text on stderr and **nothing on
stdout** — a shape a caller that parses stdout reads as empty rather than as a
correction.

The refusal is a `status: error` TOON on **stdout** (the same stream every other
result arrives on), with exit code `2` — the code argparse itself uses, so a
caller branching on the exit code needs no new case, and the dispatch boundary's
existing classifier already reports it as `argparse_rejection`:

```toon
status: error
error: invalid_invocation
notation: plan-marshall:manage-tasks:manage-tasks
reason: unknown_verb
rejected: reed
accepted: add-step, ..., get, list, read, ...
message: Use `plan-marshall:manage-tasks:manage-tasks read` — registered: [...]
```

`reason` is one of `unknown_verb`, `unknown_flag`, or `missing_required_flag`.
The `message` field is the **corrective**. For `unknown_verb`, the corrective
picks the accepted verb closest to the rejected token by edit distance, within a
threshold of `max(2, len(rejected) // 2)` — a wrong guess is worse than no guess,
so a match outside that threshold is not offered. A match within threshold takes
one of two forms: a bare nearest spelling as in the example above (`reed` →
`read`), or an alias-of relation when the grouping anchor recovered one (`gett` →
"Use `... get` (an alias of `read`) — registered: [...]"). When NO accepted verb
is within threshold — an invented verb resembling nothing registered, the normal
shape for a token like `nuke` — the corrective falls back to a third form naming
no single verb: `` Use a registered verb for `{notation}`: [...] ``. For
`unknown_flag` the corrective runs the SAME nearest-match pick over the
resolved node's declared flag set, and takes one of two forms by the same
threshold rule: within threshold it names the closest declared flag
(`` Use `--plan-id` for `{notation} {verb}` — declared: [...] ``, the form a
typo'd flag actually hits — the common case the feature exists for); outside
threshold it falls back to naming the whole declared set
(`` Use a declared flag for `{notation} {verb}`: [...] ``). For
`missing_required_flag` it lists the flags still owed
(`` Add the required flag(s) to `{notation} {verb}`: [...] ``). A refusal
without a corrective would be the empty stdout this contract exists to replace.

The set `unknown_flag` advertises is the **surface-derived** union — every flag
the script's own `--help` declares on the resolved node or any ancestor of it —
and never the universal allowlist below, which the script does not declare and
which listing here would misdescribe. Membership of that allowlist is not a
reason to *withhold* a flag either: `plan-id` and `project-dir` are declared by
most scripts *and* sit on the allowlist, so the two sets are accumulated
independently rather than one subtracted from the other. Otherwise the node's
two correctives contradict each other — `unknown_flag` reports a declared set
without `--plan-id` while `missing_required_flag` on the same node demands it,
and a caller obeying the first is refused by the second.

The refusal introduces no new reporting path: it routes through the same
`log_script_execution` and dispatch-failure work-log emission a real failure
takes, and the boundary's stdout-TOON-message precedence lifts the corrective
into the work-log `detail=` field unchanged.

#### Fail-closed rule: absent knowledge is never a rejection

Rejecting is only ever done from **positive** knowledge that a token is not
accepted. Every path lacking that knowledge dispatches exactly as it did before
this check existed:

| Condition | Behaviour |
|-----------|-----------|
| The notation has no `SCRIPT_SURFACES` entry | Spawn unvalidated |
| A node's child listing is not marked confident | Stop the walk, spawn |
| The resolved node's flag set is not marked known | Skip flag checks, spawn |
| A flag's value arity is unknown while a verb is still expected | Spawn |
| A help flag appears anywhere in the invocation | Spawn (argparse prints usage) |

"A help flag" means every spelling argparse fires its help action on, not just
the long one: `--help`, `--help=...`, the short `-h`, and `-h` inside a
short-flag cluster (`-vh`). Anchoring on `--help` alone refused `manage-tasks
read -h` for its missing required flags while `manage-tasks read --help`
printed usage — a valid call refused, from a spelling difference argparse does
not make. Cluster detection is deliberately wider than argparse's own reading
(`-fh`, where argparse binds `h` as `-f`'s value, matches too), because the
surplus direction is a spawn and the deficit direction is a false refusal. A
long flag that merely begins with the word — `--helpful`, `--help-me` — is an
ordinary flag and stays fully validated.

The asymmetry is the safety argument, and it is a claim about **knowledge**, not
about the check as a whole: a derivation gap degrades to today's behaviour, so a
missing accept-set cannot manufacture a refusal and an executor generated with
no surfaces at all is a **safe** configuration rather than a broken one. What
the asymmetry does *not* buy on its own is correctness of the walk that decides
*which* node's accept-set applies — a walk that resolves the wrong node rejects
from knowledge that is real but attached to the wrong parser, and that is a
false rejection with none of the fail-open branches above involved. The
[argv walk](#resolving-argv-to-a-parser-node) is what carries that half.

Four long flags are accepted on every node regardless of the derived surface,
because each is invisible to the derivation for a structural reason: `help`
(declared by every argparse parser and deliberately stripped from each derived
set), `audit-plan-id` (consumed by the executor before the target's argparse
runs), and `plan-id` / `project-dir` (honoured on every subcommand through
parent-flag propagation but often rendered only in the root's help).

That accept-set is defined once, as `UNIVERSAL_FLAG_ARITY` in the shared
[`argparse_surface` module](../script-shared/scripts/argparse_surface.py), and
plugin-doctor's edit-time rule imports it from there. The generated executor
cannot import it — it must dispatch before any shared module is on the path —
so it carries a literal mirror, pinned to the definition by a test that fails
on divergence. The pin is behavioural: a flag accepted at dispatch time but
missing from the edit-time set is reported as a documentation defect against a
call that in fact works.

#### Resolving argv to a parser node

Deciding which node's accept-set applies means walking argv, and that walk has
to know **which flags bind a following token as their value**. A top-level
routing flag such as `--project-dir` must PRECEDE the subcommand (argparse
rejects it afterwards), so `architecture --project-dir . find --pattern P` is
the only correct spelling — and a walk that does not know `--project-dir` takes
a value reads `find` as that value, stays on the root node, and then refuses
`--pattern` against the root's flags. Nothing in the fail-open table above fires:
every input was confident, and the refusal was still wrong.

The `flag_arity` map each surface node carries is the anchor that resolves it.
It is derived narrowly — only from the option-invocation region of an option
line, never from help prose — and is a strict subset of the node's `flags` set,
which is deliberately over-collected. An **absent** key means the arity is
unknown, never that it is zero, and the walk resolves the three states
differently:

| Flag's value arity | Behaviour |
|--------------------|-----------|
| Known (`0`, `1`, `N`) | Step over exactly that many tokens; stop early at a `-`-prefixed token or end of argv |
| Unknown, and the current node still expects a verb | Abandon the walk and spawn — the next token is either the value or the verb, and both readings resolve different nodes |
| Unknown, verb path already resolved | Step over the token; it is not a verb under either reading, so nothing is lost |

The over/under asymmetry is why arity is the one anchor derived narrowly: an
over-collected FLAG only widens an accept-set, but an over-confident ARITY
re-tokenizes argv and moves the resolved node. Abbreviated spellings are **not**
accepted, because the marketplace-wide `argparse_safety` rule requires every
parser and subparser to pass `allow_abbrev=False` — no script in the tree binds
an abbreviation, so honouring one here would model a behaviour that does not
exist.

#### Where the accept-set comes from

The embedded `SCRIPT_SURFACES` map is derived at **generation time** by running
each registered script's own `--help` — never by an AST walk, which is blind to
`aliases=` and to any parser assembled in an imported module. The derivation is
owned by [`plan-marshall:script-shared`'s `argparse_surface` module](../script-shared/scripts/argparse_surface.py),
the **single source of truth** for the accept-set: plugin-doctor's edit-time
`ARGUMENT_NAMING_*` and `manage-invocation-invalid` rules read the same module,
so the edit-time and dispatch-time guards cannot disagree about what a script
accepts.

Each embedded entry carries a source digest covering the script, every `.py`
beside it, the injected shared-module directories, and the derivation's own
schema version, so a change in an **imported** module — or in the shape of the
surface itself — invalidates the dependent entry. A regeneration reuses any
entry whose digest still matches, so the generated executor is its own cache
with no additional state file; folding the schema version in is what stops a
widened node shape from being served indefinitely from entries derived under the
old one.

**Cost, and which path a slow generation is on.** A cold derivation runs one
`--help` per parser node across every registered script and takes minutes; a
regeneration over an unchanged script set performs **zero** `--help` invocations
and is effectively free. Cold cost is therefore paid on a first build, a
`CACHE_VERSION` bump, or a broad script edit — not on routine regeneration.
`TEMPLATE_FORMAT_VERSION` is deliberately not a trigger: it is not one of the
four digest inputs, so bumping it alone reuses every cached entry. A change to
the derived node shape belongs to `CACHE_VERSION`, which is a digest input
precisely so it invalidates the entries whose schema it changed. `generate` publishes `scripts_registered`, `surfaces_derived`,
`surfaces_reused`, and `surfaces_not_derivable` (the three buckets partition the
population) so a regeneration that quietly derived nothing is visible as a
number rather than inferred from a green status. `PM_SURFACE_BUDGET_SECONDS`
bounds the total derivation wall-clock; `0` disables derivation entirely.

#### Observation point: when this guard becomes live

The validation lives in the **generated** executor, so editing the template
changes nothing until an executor is regenerated from it. Concretely:

- the **main checkout's** executor and the **plugin cache** pick the change up
  only after the change lands and the cache is synced plus the executor
  regenerated, so neither is exercised by the branch that authors the change;
- a **worktree-bound** executor is regenerated at phase-5 move-in, so a run that
  regenerates its own worktree executor after editing the template *does*
  exercise the guard against the live notation set.

The consequence for a reader auditing a change to this surface: a green run is
evidence only where a regeneration actually happened. Verify against a
regenerated executor and say which one, rather than treating a passing suite as
proof the guard behaves — the synthetic suite for this feature passed while the
first live executor refused `--help` on every script.

## Execution Logging

The executor provides two-tier logging:

### Plan-Scoped Logging

When a plan ID is provided, logs to:
```text
.plan/plans/{plan-id}/script-execution.log
```

**Two ways to enable plan-scoped logging:**

| Parameter | Use Case | Behavior |
|-----------|----------|----------|
| `--plan-id` | Scripts that accept it (manage-* scripts) | Script uses value + logging picks it up |
| `--audit-plan-id` | Scripts without `--plan-id` (scan-*, analyze-*) | Stripped before passing to script, audit logging only |

**Example with --plan-id** (script uses it):
```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files write \
  --plan-id EXAMPLE-PLAN --file task.md
```

**Example with --audit-plan-id** (audit logging only, stripped):
```bash
python3 .plan/execute-script.py pm-plugin-development:tools-marketplace-inventory:scan-marketplace-inventory \
  --audit-plan-id EXAMPLE-PLAN --include-descriptions
```

The `--audit-plan-id` parameter is audit-only — it is removed before the script executes, so the script never sees it and its behavior is unaffected. The flag exists purely to route the executor's own log entry to the plan-specific audit log for scripts that don't have their own `--plan-id` parameter.

**Benefits**:
- Tied to plan lifecycle (deleted when plan archived/deleted)
- Enables per-plan audit trail

### Global Logging

Fallback when no plan context:
```text
.plan/logs/script-execution-YYYY-MM-DD.log
```

**Benefits**:
- Session-based daily logs
- Automatically cleaned by `/marshall-steward` (7 days retention)

### Log Entry Formats

**Success entries** (single-line):
```text
[2025-12-08T10:30:00Z] [INFO] [SCRIPT] plan-marshall:manage-files:manage-files add (0.15s)
```

**Error entries** (multi-line with fields):
```text
[2025-12-08T10:31:00Z] [ERROR] [SCRIPT] plan-marshall:manage-files:manage-files add (0.23s)
  exit_code: 1
  args: --plan-id EXAMPLE-PLAN --file missing.md
  stderr: FileNotFoundError: missing.md not found
```

See `plan-marshall:manage-logging` skill for full log format specification.

## Environment Variables

The executor exports environment variables to child scripts:

| Variable | Purpose | Default |
|----------|---------|---------|
| `PLAN_DIR_NAME` | Directory name for plan storage (e.g., `.plan`) | `.plan` |
| `PM_MARKETPLACE_ROOT` | Optional explicit marketplace anchor directory (must contain `marketplace/bundles`). NOT required for stale/relocated embedded paths — the executor self-heals those (see [Self-healing path resolution](#self-healing-path-resolution)). Honored by `generate_executor.py` and `script_shared.marketplace_paths.find_marketplace_path()` when resolving the marketplace tree. Overrides the script-relative walk and cwd-based fallback. The CLI flag `--marketplace-root` (on `generate` and `drift`) takes precedence when both are set. | _(unset)_ |
| `PYTHONPATH` | Cross-skill import paths | Auto-built from all script directories |

### PLAN_DIR_NAME Usage

Scripts should use this for path construction instead of hardcoding `.plan`:

```python
import os
from pathlib import Path

# Get the plan directory name
_PLAN_DIR_NAME = os.environ.get('PLAN_DIR_NAME', '.plan')

# Use in path construction
DATA_DIR = Path(_PLAN_DIR_NAME) / "project-architecture"
LOG_DIR = Path(_PLAN_DIR_NAME) / "logs"
```

**Key points**:
- Always provide `.plan` as fallback for standalone execution
- The executor uses `setdefault()` to respect existing values (e.g., from test infrastructure)
- This enables test isolation and parallel project execution without interference

## Self-healing path resolution

The executor embeds an absolute-path `SCRIPTS` map at generation time. Those
paths can go stale when the checkout (or plugin cache) the executor was
generated against is relocated. `resolve_notation` self-heals automatically — a
stale embedded path is never returned blindly:

1. **Direct embedded hit** — returned only when the embedded path still exists
   on disk. A missing path is skipped, not returned.
2. **Prefix/substring shim** — same existence guard.
3. **Target-aware resolver** — discovers the script under the target's skill
   roots (Claude plugin cache `~/.claude/plugins/cache/plan-marshall/*/skills/…`,
   or the OpenCode config roots).
4. **cwd / executor-file upward walk** — walks up from both `Path.cwd()` and the
   executor file's own location looking for a live
   `marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py` (covers the
   dev-checkout case).

Because of this, `PM_MARKETPLACE_ROOT` is **not required** to recover from a
stale/relocated embedded path — it remains only as an intentional explicit
override for pinning discovery to a specific marketplace tree (see below).

**A refusal is not a resolution failure.** Resolution runs first and to
completion; only a resolved notation reaches the
[pre-spawn invocation rejection](#pre-spawn-invocation-rejection). So a
`status: error` / `error: invalid_invocation` payload means the script WAS
found and its declared surface rejected the call — nothing above went wrong. The
two are distinguishable on sight: an unresolved notation emits the
`SCRIPT_ERROR` line on stderr and exits `1`, while a refusal emits a TOON on
stdout and exits `2`. Chasing a marketplace anchor for a refusal is a wasted
detour; read the `message` corrective instead.

## Setup

Run `/marshall-steward` to generate the executor after bundle changes.

### Pinning the marketplace anchor (worktrees / alternate checkouts)

A stale/relocated embedded path no longer needs an anchor — the executor
self-heals it (see [Self-healing path resolution](#self-healing-path-resolution)).
Pin discovery explicitly only when you deliberately want to force a *specific*
marketplace tree (e.g. invoking `generate_executor.py` from a worktree where
`Path.cwd()` would otherwise resolve to a different checkout). Two equivalent
mechanisms are supported; the CLI flag wins when both are set:

```bash
# Option A — CLI flag (preferred, single-call discipline)
python3 generate_executor.py generate --marketplace --marketplace-root /abs/path/to/checkout
python3 generate_executor.py drift    --marketplace --marketplace-root /abs/path/to/checkout

# Option B — env var as a SINGLE-COMMAND inline assignment. The assignment and
# the command MUST be one call; never a `cd`+`export` compound (an `export`
# does not persist across separate Bash calls, and the compound trips the Bash
# one-command-per-call / no-shell-constructs safety rules).
PM_MARKETPLACE_ROOT=/abs/path/to/checkout python3 /abs/path/to/checkout/.plan/execute-script.py <notation> ...
```

The path passed to `--marketplace-root` (and `PM_MARKETPLACE_ROOT`) is the
checkout root that contains `marketplace/bundles`, not the bundles directory
itself. See `script_shared.marketplace_paths.find_marketplace_path` for the
authoritative four-step resolution order (explicit param → env var →
script-relative walk → cwd discovery).

## Architecture

```text
.plan/
├── execute-script.py            # Generated executor with embedded mappings
└── local/                       # Runtime state (managed by plan-marshall)
    ├── marshall-state.toon      # Plugin root path + metadata
    └── logs/                    # Global execution logs (no plan context)
        └── script-execution-YYYY-MM-DD.log

~/.claude/plugins/cache/plan-marshall/
└── {bundle}/              # Installed plugin bundles
    └── {version}/         # Versioned bundle contents
        └── skills/...     # Skills with scripts
```

## Bootstrap Pattern (Before Executor Exists)

When `.plan/execute-script.py` doesn't exist yet (first run), use the bootstrap pattern:

### Step 1: Get Plugin Root

Check `.plan/local/marshall-state.toon` for cached `plugin_root`, or detect it:

Resolve the bootstrap script path with the `Glob` tool against the pattern `~/.claude/plugins/cache/*/plan-marshall/*/skills/marshall-steward/scripts/bootstrap_plugin.py` and capture the first match as `{BOOTSTRAP_PLUGIN}`. Then invoke it directly:

```bash
python3 "{BOOTSTRAP_PLUGIN}" get-root
```

Output:
```text
plugin_root	/Users/.../.claude/plugins/cache/plan-marshall
source	detected|cached
```

### Step 2: Execute Scripts Directly

Use the plugin root with a glob pattern for the version segment. Resolve the script path with the `Glob` tool against the pattern `${PLUGIN_ROOT}/plan-marshall/*/skills/<skill>/scr*ts/<script>.py` and capture the first match as `{SCRIPT_FILE}`. Then invoke it directly:

```bash
python3 "{SCRIPT_FILE}" <args>
```

(Replace `<skill>`, `<script>`, and `<args>` with literal values. The `scr*ts` glob refers to the skill's `scripts` subdirectory; it is written with a wildcard to avoid scanner false positives on this standards document.)

### State File Format

`.plan/local/marshall-state.toon`:
```text
plugin_root	/Users/oliver/.claude/plugins/cache/plan-marshall
detected_at	2025-12-12T10:30:00+00:00
```

This pattern enables:
- Plugin scripts to work in any project (not just the marketplace repo)
- Caching for fast subsequent lookups
- Version-agnostic paths via glob

### Version-aware bundle-path resolution

The glob patterns above resolve a script path across a single *unknown* version
segment. `select_live_version_dir` (in
`script-shared/scripts/marketplace_bundles.py`) is the version-*aware* counterpart
used inside scripts that must pick ONE version dir when several coexist in the
plugin cache. It is the **single function that decides liveness and ordering**:
every call site — `find_bundles`, `resolve_bundle_path`, `collect_script_dirs`, and
the executor preflight's own version-dir helpers — supplies only its own
*eligibility* predicate (manifest present / requested subpath present / `skills/`
present) and delegates the decision. `resolve_bundle_path` therefore contributes
only "this version dir carries the requested subpath", then falls back to the
non-versioned (marketplace) layout when no version dir qualifies.

The selector's policy: `_version_sort_key` remains the single ordering key
underneath it (parsing each version-dir name into a comparable integer tuple,
`0.1.1069` → `(0, 1, 1069)`); a `.orphaned_at` mark disqualifies a candidate
**except** on the retention-pinned newest-on-disk dir, whose mark is ignored
outright; and when every eligible dir is marked, the newest eligible dir is
returned with a diagnosable stderr line.

**Only the marker's existence is consulted — never its content.** Every clause of
that policy turns on whether `.orphaned_at` is PRESENT; nothing reads, parses, or
compares what is inside it. This is a binding invariant, not an incidental property
of the current implementation, because the field has a foreign co-producer: Claude
Code's own plugin GC writes the same filename with a raw epoch-ms payload, while our
writer (`generate_executor._mark_superseded_version_dirs`) writes ISO-8601 UTC. Two
producers write one field in two encodings, so a content-dependent rule would bind
the selector to a format this repository does not own and cannot version. The marker
is a boolean flag whose payload is deliberately opaque, and the encoding split is
inert precisely because of that.

**Two sanctioned existence-read sites implement the invariant, not one.**
`marketplace_bundles._partition_version_dirs` is the selector's read site, and the
`.orphaned_at` predicate inside `generate_executor._CLAUDE_RESOLVER_TEMPLATE` is the
mirrored read site substituted verbatim into the generated `.plan/execute-script.py`
(the runtime resolver described further down this section). Both read existence only,
and both state the invariant in their own docstring. They are not a self-synchronising
pair: the template is a deliberate policy duplicate whose docstring requires that any
change to the selector's policy be mirrored into it, so this prose, the selector, and
the template are three parties a policy change has to be carried to explicitly.

Selecting the live newest — rather than the lexically-first `iterdir` result — is
load-bearing: a stale older version dir (e.g. `1.0.0` alongside `1.0.10`) would
otherwise shadow the current one on the cross-skill import path. Routing every leg
through one selector additionally closes the *predicate-divergence* class, where a
marker-aware leg and a marker-blind leg resolved to different version dirs and the
generated executor ended up internally version-split; the executor-staleness check
surfaces the on-disk condition via `_detect_multi_version_pollution`, and
`generate_executor`'s Guard 4 refuses at write time to emit an executor whose paths
span more than one version dir per bundle.

The executor's own embedded runtime resolver (`_resolve_notation_by_target`, the
`SCRIPTS`-miss fallback substituted into the generated file) carries a deliberate,
docstring-marked **duplicate** of that policy: the generated executor is
bootstrap-free and must resolve notations before any marketplace module is
importable, so it cannot import the selector. The duplicate is minimal, consumes
the same on-disk input set, and is pinned equivalent by test.

> **Worked example — pre-merge source-edit contract.** Documenting this version-aware
> resolution in its governing skill is a worked example of the
> [pre-merge source-edit-pushability contract](../phase-6-finalize/standards/source-edit-pushability.md):
> a source (or source-doc) edit belongs in the branch that merges it, so the edit is
> pushable and rides the PR — never deferred to an unpushable post-merge finalize
> step.

## Broken Executor Recovery (Generated but Unrunnable)

This case is distinct from the [Bootstrap Pattern](#bootstrap-pattern-before-executor-exists) above. Bootstrap covers the **first-run** state where `.plan/execute-script.py` does **not yet exist**. This section covers the state where the generated executor **exists on disk but fails to run** — for example, a template import-surface change makes the embedded preamble import a symbol the runtime no longer exports, so every `python3 .plan/execute-script.py …` call aborts before reaching any script body. Because the executor itself is broken, the normal `/marshall-steward` and `/sync-plugin-cache` regeneration paths — which route through the executor — cannot be used to repair it.

### Recovery

Regenerate the executor by invoking `generate_executor.py` **directly**, bypassing the broken `.plan/execute-script.py`:

```bash
python3 marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py generate --marketplace --marketplace-root .
```

This is the same `generate_executor — generate` surface documented under [Canonical invocations](#canonical-invocations), run against the script file by its repository path rather than through the executor notation. The `--marketplace` flag selects the marketplace-source generation mode and `--marketplace-root .` pins discovery to the current checkout root (the directory that contains `marketplace/bundles`). After the direct call succeeds, the rewritten `.plan/execute-script.py` carries the corrected preamble and the normal executor-routed commands work again.

### Distinguishing the executor-unavailable cases

| Case | Symptom | Recovery |
|------|---------|----------|
| First run (bootstrap) | `.plan/execute-script.py` does not exist | [Bootstrap Pattern](#bootstrap-pattern-before-executor-exists) — resolve the plugin root, run scripts directly |
| Broken generated executor | `.plan/execute-script.py` exists but every invocation fails before reaching a script body | Run `generate_executor.py generate --marketplace --marketplace-root .` directly to rebuild it |
| Interpreter-launch abort | `python3 .plan/execute-script.py …` produces **no TOON and no `status` field at all** — the interpreter aborts at `dyld` level before the executor's own preamble runs, so there is no Python-level traceback either | Same as the broken-executor row: run `generate_executor.py generate --marketplace --marketplace-root .` directly. Re-materialise the virtual environment first when its interpreter pointer is the cause (see below) |

**Known divergence — a stale `pyvenv.cfg` interpreter pointer.** A virtual environment whose `pyvenv.cfg` names an interpreter that no longer resolves on disk aborts the launch at the dynamic-loader level: the process never reaches Python, so no in-process guard, retry, or error handler can observe it. This is stated as a fact about the environment, not a defect to fix here — the abort is **not repairable from inside the process that failed to launch**, and no repair of the third-party virtual-environment materialisation is attempted by this skill.

**Reader-facing consequence: empty output from an executor call is never to be read as success.** A call that returns nothing has not reported a clean verdict; it has reported nothing at all, which is the undetermined state. Treat it as a failure and take the recovery above. The two supporting facts, both already established elsewhere in this repository, are worth naming together: the dispatch boundary maps a negative `returncode` (a signal-terminated process) to `status: killed`, never to `success`; and the dispatch-failure work-log emission classifies the case `script_internal_failure` and carries the loader's stderr text as its detail, so the diagnostic is legible rather than empty.

## Wait Pattern (Optional)

The script executor includes a synchronous polling utility for blocking until async operations complete.

**When to Load**: Activate when implementing workflows that wait for:
- CI/CD pipeline completion
- Sonar analysis completion
- External service readiness
- Any async operation requiring polling

**Load Reference**:
```text
Read standards/wait-pattern.md
```

**Quick Usage**:

```bash
# Adaptive mode (timeout managed via run-config)
# Outer shell timeout (600s) prevents the host platform from canceling
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status --pr-number 123" \
  --success-field "status=success" \
  --failure-field "status=failure" \
  --command-key "ci:pr_checks"

# Explicit mode (custom interval)
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status --pr-number 123" \
  --success-field "status=success" \
  --failure-field "status=failure" \
  --command-key "ci:custom_check" \
  --interval 15
```

**Note**: When using Bash tool, set `timeout` parameter to `600000` (ms) to match shell timeout.

**Output** (TOON format):
```text
status          success|timeout|failure
duration_sec    Actual wait duration in seconds
polls           Number of condition checks
timeout_used_sec Timeout value used in seconds
timeout_source  explicit|adaptive|default
command_key     The command key (if adaptive)
final_result.*  Flattened fields from last check
```

## Integration with Verification

The verification skill recognizes this execution pattern:

**Allowed**:
- `python3 .plan/execute-script.py {notation} ...`

**Violation**:
- `python3 {direct_script_path} ...`

## Canonical invocations

The canonical argparse surface for the two entry-point scripts this skill registers: `await_until.py` and `generate_executor.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### await_until

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until \
  --check-cmd CHECK_CMD --success-field SUCCESS_FIELD --command-key COMMAND_KEY \
  [--failure-field FAILURE_FIELD] [--interval INTERVAL]
```

### generate_executor — generate

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate \
  [--force] [--dry-run] [--marketplace] [--marketplace-root PATH] [--target TARGET]
```

### generate_executor — verify

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor verify
```

### generate_executor — drift

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor drift \
  [--marketplace] [--marketplace-root PATH]
```

### generate_executor — paths

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor paths
```

### generate_executor — cleanup

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor cleanup \
  [--max-age-days MAX_AGE_DAYS]
```

### generate_executor — preflight

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor preflight \
  [--marketplace] [--marketplace-root PATH] [--target TARGET]
```

Deterministic executor/config staleness check against the installed `dist-manifest.json`. Regenerates the executor in place (safe derived state, ADR-002) when EITHER of two independent triggers fires: (1) its embedded `MARSHALL_VERSION` is older than the manifest's `executor_changed_at_version` (version staleness); or (2) `_detect_multi_version_pollution` finds the plugin cache carries more than one version dir per bundle, whose stale copies would shadow the current version on the cross-skill import path. Both triggers surface through the same `executor_action: regenerated` result. Config-seed staleness is reported advisory-only (`marshal.json` is never auto-mutated). **Fail-closed semantics:** when the installed `dist-manifest.json` cannot be resolved (`installed_version` is the `unknown` sentinel), no version-based staleness verdict can be substantiated, so the verb reports `marshal_status: unknown` and emits a legible warning to stderr (also carried in the `warning` field) rather than a vacuous `fresh`. Returns a seven-field TOON: `status`, `executor_action` (`fresh` | `regenerated`), `marshal_status` (`fresh` | `stale` | `unknown`), `installed_version`, `executor_version`, `marshal_version`, `warning` (the fail-closed message when `marshal_status` is `unknown`, else the empty string).
