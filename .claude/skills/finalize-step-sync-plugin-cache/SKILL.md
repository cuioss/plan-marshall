---
lane:
  class: derived-state
  cost_size: XS
name: finalize-step-sync-plugin-cache
description: Sync every harness install (Claude cache, OpenCode, Antigravity) from target/ via the unified sync engine
mode: script-executor
order: 85
mutates_source: false
default_on: false
presets: []
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Finalize Step — Sync Harness Installs (project-local)

Project-local executor for `project:finalize-step-sync-plugin-cache`.
Invokes the unified sync engine `marketplace/targets/sync.py` with no
`--target`, so one call syncs all three harnesses from their generated
trees:

| Harness | Source | Install location |
|---------|--------|------------------|
| `claude` | `target/claude/` | the versioned plugin cache `~/.claude/plugins/cache/plan-marshall/{bundle}/{version}/` |
| `opencode` | `target/opencode/` | `~/.config/opencode/` |
| `antigravity` | `target/antigravity/` | `~/.gemini/config/plugins/plan-marshall/` |

The step id names the Claude plugin cache; the step itself syncs every
harness install. It is the finalize-time counterpart of the
project-local `/sync-harnesses` command, which runs the same engine.

This step is **project-local** rather than a `default:` built-in for
the same reason as `project:finalize-step-deploy-target`: the sync only
makes sense for this repo (the plan-marshall meta-project). Consumer
projects have nothing to publish, so they don't get this step seeded
into their `marshal.json` defaults.

This step runs on the main checkout post-merge, after
`project:finalize-step-deploy-target` has regenerated the three target
trees from the merged source tree. Syncing the harness installs here
means the next session boot and this sync read the same authoritative
content. This step does not regenerate: the staleness guard below is
the check that the Claude tree it consumes is current.

## Staleness guard

The Claude leg of the engine lives in
`marketplace/targets/claude/cache_sync.py`. It refuses to mirror
`target/claude/` into the cache unless the tree is proven current
relative to `marketplace/bundles/`. The OpenCode and Antigravity legs
carry no staleness guard; they refuse only a missing or empty source
tree.

The guard runs these checks in order:

1. `target/claude/` exists and holds at least one bundle.
2. Every source bundle the Claude emitter selects is present in
   `target/claude/`. The expected set is the bundles under
   `marketplace/bundles/` whose own `.claude-plugin/plugin.json` admits
   `claude` through its `targets` declaration — the field absent means
   every target, the field present means the listed targets only. A
   bundle scoped to other harnesses is never expected in the Claude
   tree; a claude-admitting bundle missing from it is refused.
3. The emit sentinel `target/claude/.emit-marker.json`, written by
   `project:finalize-step-deploy-target`, exists and carries a
   `source_tree_fingerprint`.
4. The fingerprint recomputed over `marketplace/bundles/` (git's native
   `ls-files` / `hash-object` primitives) matches the sentinel's.
5. Every file under `target/claude/` matches the per-file hash manifest
   the sentinel records in `file_hashes`.

A refusal is discriminated by kind, carried in the Claude result block
as `guard_outcome`:

| `guard_outcome` | Meaning | Remedy |
|-----------------|---------|--------|
| `stale` | A check ran and observed a staleness condition: the tree or sentinel is missing, a claude-admitting bundle was not emitted, the source changed since the last emit, or the tree drifted from its manifest | Re-run `project:finalize-step-deploy-target` |
| `probe_failed` | A check could not run at all: a bundle's `plugin.json` could not be read, the fingerprint helper would not import, or `git` would not answer. The tree's freshness is unknown | Repair the probe the `summary_message` names; regenerating is not the fix |

On either kind the Claude result reports `status: error` with the
refusal text in `summary_message`, and no bundle is attempted.

The Phase 6 ordering (`project:finalize-step-deploy-target` at 81 →
`project:finalize-step-sync-plugin-cache` at 85) means the sentinel is
written immediately before this step reads it, so the guard normally
passes on the first try. A `stale` refusal here points at deploy-target
having been skipped or having failed for the Claude target, or at
concurrent edits to `marketplace/bundles/` between emit and sync.

The `--skip-staleness-guard` flag remains the escape hatch for tests and
recovery flows. Phase 6 never invokes it; only operators do, after
diagnosing why the guard refused.

## Ordering

The canonical Phase 6 ordering surrounding this step is:

```text
default:branch-cleanup (70) →
project:finalize-step-deploy-target (81) →
project:finalize-step-sync-plugin-cache (85) →
default:record-metrics (990)
```

`order: 85` places this step immediately after
`project:finalize-step-deploy-target` (so the installs mirror the
just-regenerated `target/` content), post-`branch-cleanup` on the main
checkout. This step is the single project-level owner of on-main
executor regeneration: once the Claude cache has synced it regenerates
`.plan/execute-script.py` against the freshly-synced cache (Execution
step 3). `integrate_into_main` performs the move-back only and does NOT
regenerate the executor — the executor stays a per-tree derived artifact
(ADR-002). Coupling regen to this step (the canonical "sync → regenerate
executor" sequence) closes the no-worktree staleness gap: the regen runs
in BOTH worktree and no-worktree finalize flows because it is just a
finalize step, not a move-back side effect.

Inside the step the order is fixed:

```text
sync (1) → regenerate executor (3) → daemon reconcile (3b) →
repin or report (3c) → parity verdict → mark step complete (4)
```

The parity verdict is read **last**, from the repin script's own result,
so the step records the registry as it stands when the step ends rather
than as the engine saw it before the repin.

## Inputs

- `{plan_id}` — required. Used for logging.

## Execution

Inline-only — this step does NOT delegate to a Task agent. The sync
engine is a fast Python script with deterministic output.

### 1. Invoke the unified sync engine

```bash
python3 marketplace/targets/sync.py
```

With no `--target` the engine attempts `claude`, `opencode` and
`antigravity` in that order — each one even when an earlier one failed —
and prints one aggregate TOON document:

- `status` — `success` | `partial` | `error`.
- `targets[3]{target,status,summary_message}` — one row per harness.
- One result block per harness (`claude:`, `opencode:`, `antigravity:`)
  carrying that harness's own fields: `synced_count` and
  `synced[N]{bundle,version,status}` for Claude, `deployed_count` and
  `removed_count` for OpenCode and Antigravity.

The `claude:` block carries two further members that separate the cache
sync from the registry pin:

- `cache_status` — `success` | `partial` | `error`: the outcome of the
  cache sync alone. The block's `status` differs from it only when a
  registry that is behind lowered a `success` to `partial`.
- `registry_parity` — when present, the last block, ending with the engine's `verdict`:
  `in_parity`, `behind`, `ahead` or `unreadable`. This is the registry as
  the engine saw it, **before** Step 3c; the verdict the step records is
  the one Step 3c reads afterwards.

The engine exits `0` only on aggregate `success`. Read each harness's
result from the document, not from the exit code.

### 2. Parse the result

The step's outcome is decided by each harness's **own install** and by
the **final** registry verdict, not by the aggregate `status`. The
aggregate is `partial` when the Claude registry is merely behind, which
Step 3c may close in the same run.

| Condition | Outcome |
|-----------|---------|
| OpenCode or Antigravity reports a `status` other than `success` | `outcome=failed` |
| Claude reports a `cache_status` other than `success` | `outcome=failed` |
| The final registry verdict (Step 3c) is `behind` | `outcome=failed` |
| None of the above | `outcome=done` |

The first two rows are readable now; the third is not known until Step 3c
has run, so the outcome is settled there. A `behind` verdict in the
engine's own `registry_parity` block is superseded when Step 3c's repin
closed the gap. The final verdicts `ahead` and `unreadable` are reported
and do not fail the step.

One failing harness never hides the other two: the `targets[]` table
reports each harness on its own row, and Steps 3, 3b and 3c below key on
the Claude `cache_status` alone. For every harness whose own install did
not sync, surface that row's `summary_message`.

### 3. Regenerate the on-main executor (when the Claude cache synced)

When the `claude:` result block reports `cache_status: success`,
regenerate `.plan/execute-script.py` against the freshly-synced host
cache. This runs on the main checkout, so the generator's cwd-relative
resolution writes main's executor with mappings that point at the
just-synced cache — refreshing the on-main mapping after a plan that
changed the marketplace script *set*. This step is the meta-project-only
owner of on-main executor regeneration, and it runs in BOTH worktree and
no-worktree finalize flows (closing the no-worktree staleness gap).

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate
```

Regeneration is **unconditional-after-successful-sync** of the Claude
cache (always re-deriving the executor from the fresh cache is cheap,
deterministic, and eliminates the staleness class without a gating
heuristic) and **non-fatal**: a non-zero exit or failure logs a WARN and
the step still records its sync outcome — finalize must not block on a
mapping refresh.

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level WARNING \
  --message "[STATUS] (project:finalize-step-sync-plugin-cache) On-main executor regeneration failed (non-fatal); run /marshall-steward to recover"
```

The gate is the Claude `cache_status`, not the `claude` row's `status`
and not the aggregate. When OpenCode or Antigravity failed but the Claude
cache synced, the cache is complete and the regeneration still runs,
while the step records `outcome=failed` for the failing harness. The
same holds when the `claude` row reads `partial` only because the
registry is behind: the cache is complete, so the regeneration runs.
When `cache_status` reports anything other than `success`, SKIP
regeneration — the cache is incomplete or untouched, so regenerating
against it would be wrong; the step records the failure (Step 4) and an
operator recovers.

### 3b. Reconcile the build daemon (when the Claude cache synced)

The cache bump the Claude leg just performed is exactly what makes a
running `marshalld` stale: the daemon is version-pinned to the OLD
bundle copy while the fresh cache now carries a newer one. When the
`claude:` result block reports `cache_status: success` (and after the
executor regen above), run the meta-project-only reconcile so an **idle** stale daemon
is upgraded to the verified pin and a **busy** one is left running with
the deferral recorded:

```bash
python3 marketplace/targets/claude/reconcile_daemon.py
```

The script queries `manage-build-server status` and applies the idle-conditional
contract: idle-and-stale → `upgrade` (drain-then-start-verified); busy-and-stale
(anything in flight or queued) or an undeterminable running provenance →
**defer** (never drain a live build), leaving a readable `reconcile-owed` marker;
down-but-enrolled → plain `start`; already-current → no-op. An absent/disabled
build server (or a session without the executor) is a **silent no-op** via the
script's fail-open adapters, so this changes no shared-daemon behaviour and a
repository not using marshalld is unaffected.

Like the executor regen, the reconcile is **non-fatal**: it never blocks finalize.
Read its `action` / `display_detail` from the TOON and surface a one-line detail;
a `defer` is reported (the `reconcile-owed` marker persists it), never swallowed.
When `cache_status` reports anything other than `success`, SKIP the
reconcile — the cache is incomplete. A `claude` row that reads `partial`
only because the registry is behind does NOT skip it.

### 3c. Repin or report the plugin registry (when the Claude cache synced)

The cache sync moved the plugin cache forward; the plugin registry still
names the version it was pinned at, and a restarted session loads what
the registry names. Under the same gate as Steps 3 and 3b — the
`claude:` result block reports `cache_status: success` — this step
either repins the registry or reports its state, depending on a
machine-local opt-in. When `cache_status` reports anything other than
`success`, SKIP this step: nothing was synced to pin to, and no pin
token is recorded (Step 4).

Read the opt-in:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config registry-repin get
```

The setting is machine-local because the registry it gates is
machine-local; it reads `disabled` unless the operator enabled it on
this machine (see `plan-marshall:manage-run-config` § "registry-repin
get / set"). Branch on the returned `value`. When the read itself fails
— for instance because the Step 3 regeneration failed and the executor
does not yet know the verb — treat the opt-in as `disabled`: an
unreadable setting is never consent to write.

**`value: enabled`** — apply the repin:

```bash
python3 marketplace/targets/claude/registry_pin.py --apply
```

**`value: disabled`** — report only; the script writes nothing:

```bash
python3 marketplace/targets/claude/registry_pin.py
```

Either call prints one `entries` row per plan-marshall registry entry,
with its version before and after and an `action`, and ends with
`registry_parity` — the registry as it stands when the call returns.
That value is the step's **final registry verdict**: `in_parity`,
`behind`, `ahead` or `unreadable`. Read it from the document; the script
exits non-zero on `behind` and on a failed apply, so the exit code alone
does not say which.

Log the result on its own work-log line, whichever branch ran:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-sync-plugin-cache) Registry repin: mode {mode}, verdict {registry_parity}, {repinned_count} entry(ies) repinned"
```

`{mode}` is the script's `mode` (`apply` or `dry_run`) and
`{repinned_count}` the number of `entries` rows whose `action` is
`repinned`. When the script reports `status: error`, log its `message`
at WARNING as well; the outcome still follows the final verdict.

The final verdict settles the outcome row Step 2 left open: `behind`
records `outcome=failed`. That is the case on a machine where the
opt-in is `disabled` and the registry is behind — the cache is current,
the pin is not, and a restarted session would still load the pinned
version. The remedy is the operator's: run the `--apply` form above, or
enable the opt-in.

### 4. Mark step complete

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status \
  mark-step-done --plan-id {plan_id} --phase 6-finalize \
  --step project:finalize-step-sync-plugin-cache \
  --outcome {done|failed} \
  --display-detail "{display_detail}"
```

`{display_detail}` names the per-target result. It is plain ASCII and
at most 80 characters (the limit is owned by
`phase-6-finalize/standards/external-step-contract.md`), so it carries
counts and tokens only; free-form text goes to the work log.

It takes one of two forms. Both end, whenever Step 3c ran, with a **pin
token** naming the final registry verdict:

| Pin token | Final registry verdict |
|-----------|------------------------|
| `ok` | `in_parity`, and Step 3c repinned no entry |
| `repinned` | `in_parity`, and Step 3c repinned at least one entry |
| `behind` | `behind` |
| `ahead` | `ahead` |
| `unreadable` | `unreadable` |

**Form 1 — every harness's own install synced** (OpenCode and
Antigravity report `status: success` and Claude reports
`cache_status: success`):

```text
cl {synced_count} oc {deployed_count} ag {deployed_count}; regen {regen}[; daemon {daemon}]; pin {pin}
```

`cl`, `oc` and `ag` abbreviate `claude`, `opencode` and `antigravity`;
each count is read from that harness's result block. The segments are:

- `regen {regen}` — `regen ok`, or `regen failed` when the Step 3 regen
  exited non-zero. A failed regen does not change the outcome, and the
  Step 3 WARNING line carries the remedy.
- `daemon {daemon}` — present only when the Step 3b reconcile did
  anything other than a plain no-op, so its result is visible at the
  step level and not only in the marker. It is `daemon failed` when the
  reconcile's `reconcile_result` is `failed` — its `action` still reads
  `upgrade` or `start` in that case, so the action alone would report a
  failed reconcile as a confirmed one — and otherwise the reconcile's
  `action` token: `daemon upgrade`, `daemon defer` or `daemon start`.
- `pin {pin}` — the pin token above.

Form 1 is used with `outcome=done`, and also with `outcome=failed` when
the only failure is a final verdict of `behind` — the detail then ends
`pin behind`. Its longest rendering,
`cl 9999999 oc 9999999 ag 9999999; regen failed; daemon upgrade; pin unreadable`,
is 78 characters, so the form stays within the limit for counts of up to
seven digits.

The reconcile's own `display_detail` is free-form and is logged, not
appended:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (project:finalize-step-sync-plugin-cache) Daemon reconcile: {reconcile_display_detail}"
```

**Form 2 — at least one harness's own install did not sync:**

```text
failed: {targets} (see work log)[; claude synced[; pin {pin}]]
```

`{targets}` is the comma-separated names, unabbreviated, of every
harness whose own install did not sync: `opencode` or `antigravity` on a
`status` other than `success`, `claude` on a `cache_status` other than
`success`. `; claude synced` is appended when the Claude `cache_status`
is `success`, so the record states that Steps 3, 3b and 3c ran; the pin
token follows it, and only then — with the Claude cache not synced
Step 3c did not run and there is no verdict to name. The regen and
daemon results of such a run are in the work log. The longest rendering,
`failed: opencode, antigravity (see work log); claude synced; pin unreadable`,
is 75 characters.

The engine's `summary_message` text is unbounded, so each failing
row's message is logged in full rather than placed in the detail:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level ERROR \
  --message "[ERROR] (project:finalize-step-sync-plugin-cache) {target}: {summary_message}"
```
