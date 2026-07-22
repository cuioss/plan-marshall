# Upgrade Flow

The `upgrade` verb runs the full post-change reconciliation in ONE flow after a
change: regenerate the target tree and/or executor, reconcile `marshal.json`,
verify, then run the existing landing cycle. The verb is pure orchestration glue
over already-shipped machinery — it FIRST calls the deterministic planner
`upgrade.py plan` to obtain the fixed four-stage plan with per-stage gate
dispositions AND per-stage `sub_steps`, then drives each stage's existing
machinery honoring those dispositions.

The plan is **project-kind aware**. A `meta` project (the plan-marshall
meta-project itself) regenerates the `target/claude` tree AND the executor and
verifies with executor preflight AND a content-drift report; a `consumer`
project (a downstream project that consumes plan-marshall) gates on plugin-cache
freshness, regenerates ONLY the executor, and verifies with executor preflight
ONLY — the meta-only sub-steps (`marketplace/targets/generate.py` in Stage 1,
`content_drift_cli.py` in Stage 3) are absent from a consumer plan and MUST NOT
be attempted. Both kinds end Stage 1 with the plugin-cache retention sweep. The
planner detects the kind or is told it explicitly; this flow runs exactly the
`sub_steps` the plan emitted for the resolved kind. The single entry that is
consumer-only — `cache-freshness-check` — and the reason for that asymmetry are
documented in § "Meta/consumer cache-freshness asymmetry" below.

This reference is loaded from two entry points (see [`../SKILL.md`](../SKILL.md)):
Main Menu option 5 ("Upgrade"), and the `upgrade` early verb check (which passes
the `integrate` value from `/marshall-steward upgrade [integrate=true]`).

`{repo_root}` below is the main-checkout repository root the steward is running
against. All git invocations use the explicit `git -C {repo_root} …` form (never
`cd {repo_root} && git …`), all mutations go through scripts (never hand-edits),
and all CI/PR operations go through the `tools-integration-ci:ci` abstraction
(never `gh`/`glab` directly).

## The four stages

The four stages and their order are fixed. Each stage runs the `sub_steps` the
plan emitted for the resolved `project_kind`; the meta/consumer matrix below
names them (Stages 2 and 4 are kind-invariant, Stages 1 and 3 drop meta-only
sub-steps on a consumer).

```text
  Stage 1  regenerate-targets   meta:     regenerate-target-tree + regenerate-executor  [mutating]
                                          + cache-retention-sweep
                                consumer: cache-freshness-check + regenerate-executor
                                          + cache-retention-sweep
                                └─ nested gate: cache-retention-prune (still prompts)
  Stage 2  reconcile-config     both:     reconcile-marshal-json                        [mutating]
                                └─ nested gate: build-map re-seed (still prompts)
  Stage 3  verify               meta:     executor-preflight + content-drift-report     [read-only]
                                consumer: executor-preflight
  Stage 4  land                 both:     run-landing-cycle                             [mutating]
                                └─ nested gates: land/leave + branch-reuse (still prompt)
```

## Step 0: Obtain the stage plan

Call the deterministic planner FIRST, passing the resolved `integrate` value
(`true` when the invocation carried `integrate=true`, otherwise `false`) and
`--project-kind auto` (the planner detects `meta` vs `consumer` from the cwd via
a read-only `marketplace/targets/generate.py` + `marketplace/bundles/` presence
check; pass `meta` or `consumer` explicitly to override the detection):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:upgrade plan --integrate {integrate} --project-kind auto
```

See the [`../SKILL.md`](../SKILL.md) Canonical invocations (`upgrade — plan`) for
the verb shape. Parse the returned top-level `project_kind` and the
`stages[4]{order,key,name,mutating,top_level_gate,nested_gates,sub_steps}` list.
Each stage's `top_level_gate` is the disposition this flow honors below: `prompt`
(ask before running the stage) or `suppressed` (run without the top-level
prompt). Each stage's `sub_steps` is the exact ordered list of sub-steps to run
for the resolved kind — run exactly those, and never a sub-step absent from the
emitted list (a `consumer` plan omits the meta-only sub-steps).

## Gate contract

- **Plain mode** (`/marshall-steward upgrade`) — every stage's `top_level_gate`
  is `prompt`. Before running each of the four stages, present a top-level gate
  `AskUserQuestion` (Proceed / Skip this stage / Abort the upgrade).
- **`integrate=true`** (`/marshall-steward upgrade integrate=true`) — every
  stage's `top_level_gate` is `suppressed`. Run all four stages end-to-end
  WITHOUT the top-level prompts.
- **`integrate=true` suppresses ONLY the four top-level stage gates.** The
  **nested** gates are `integrate`-invariant and STILL prompt under
  `integrate=true`: the Stage 1 `cache-retention-prune` gate, the Stage 2
  `build-map` re-seed gate, and the Stage 4 landing land/leave + branch-reuse
  gates. `integrate=true` is therefore **not** a
  globally-unattended mode — it collapses the four stage-boundary prompts, not
  the safety gates that guard destructive or hand-editable state.
- **Do NOT modify the reused sub-flows to add suppression.** The reused
  machinery (the `build-map` drift gate, `landing-cycle.md`) keeps its own
  prompts exactly as-is; this flow never edits those sub-flows to honor
  `integrate`.

### Per-stage top-level gate

For each stage, before running its machinery:

- **`top_level_gate: prompt`** — present:

  ```text
  AskUserQuestion:
    question: "Run upgrade Stage {order} — {name}?"
    header: "Upgrade — Stage {order}"
    options:
      - label: "Proceed"
        description: "Run this stage's machinery"
      - label: "Skip this stage"
        description: "Move to the next stage without running this one"
      - label: "Abort"
        description: "Stop the upgrade; report the partial state"
    multiSelect: false
  ```

  - **Proceed** → run the stage.
  - **Skip this stage** → move to the next stage.
  - **Abort** → follow "Partial-failure and abort handling" below.

- **`top_level_gate: suppressed`** → run the stage without prompting.

## Stage 1: regenerate-targets (mutating)

Honor the Stage 1 top-level gate, then run exactly the Stage 1 `sub_steps` the
plan emitted for the resolved kind:

- **`cache-freshness-check`** (consumer only — absent from a meta plan) — the
  fail-closed gate that establishes the precondition `regenerate-executor`
  depends on: that the plugin cache the generator reads is current with the
  marketplace clone. It is Stage 1's FIRST sub-step because it is
  `regenerate-executor` that reads the (possibly unrefreshed) cache. The verb is
  read-only and mutates nothing:

  ```bash
  python3 .plan/execute-script.py plan-marshall:marshall-steward:cache_freshness check
  ```

  See the [`../SKILL.md`](../SKILL.md) Canonical invocations
  (`cache_freshness — check`) for the verb shape. Parse `freshness`,
  `refuses_upgrade`, and `remediation`. The verdict set is exactly three-valued
  and there is **no** age-based, mtime-based, or otherwise-inferred fallback that
  downgrades an unsubstantiable verdict to a guess:

  | `freshness` | Meaning | `refuses_upgrade` | Action |
  |-------------|---------|-------------------|--------|
  | `fresh` | The cache is at or ahead of the marketplace-clone manifest version | `false` | Continue to `regenerate-executor` |
  | `stale` | The cache is BEHIND the clone manifest — the consumer never refreshed | `true` | STOP the upgrade; surface `remediation` verbatim |
  | `unknown` | No cache root or clone manifest resolvable — the verdict cannot be substantiated | `true` | STOP the upgrade; surface `remediation` verbatim |

  `unknown` is terminal and refusing, never a vacuous `fresh` (ADR-009). On
  either refusing verdict, follow "Partial-failure and abort handling" below and
  report the emitted `remediation`, which names the operator commands verbatim:
  run `/plugin marketplace update` to refresh the marketplace clone, then
  reinstall the plugin (`/plugin uninstall plan-marshall` followed by
  `/plugin install plan-marshall`). Re-run `/marshall-steward upgrade` afterwards.

  Note the division of labour with Stage 3's `executor-preflight`: preflight
  compares the executor's stamp against a LOCAL manifest and answers "is my
  executor consistent with my cache?"; it is structurally incapable of seeing
  cache-versus-upstream skew. This sub-step owns that question, and preflight is
  unchanged.

- **`regenerate-target-tree`** (meta only — absent from a consumer plan) —
  regenerate the Claude target tree:

  ```bash
  python3 marketplace/targets/generate.py --target claude --output target/claude
  ```

- **`regenerate-executor`** (both kinds) — regenerate the executor. Invoke the
  post-change `generate_executor.py` **directly, by its resolved script path**
  — NOT through the `.plan/execute-script.py` proxy — so a recovery run works
  even when the currently-installed executor is broken and cannot proxy at all.
  Resolve the script path per kind: meta uses the marketplace-source generator
  (`marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py`);
  consumer uses the newest cache-version generator under the plugin cache, whose
  currency is established by the `cache-freshness-check` sub-step above — this
  sub-step establishes nothing itself and asserts no precondition of its own. Run
  its `generate` verb directly:

  ```bash
  python3 {resolved_generate_executor_path} generate
  ```

  See the `tools-script-executor` Canonical invocations (`generate_executor` →
  `generate`) for the verb shape. The generator's own self-check — the
  TEMPLATE_FORMAT_VERSION handshake, the unsubstituted-placeholder residue
  guard, and the `py_compile` self-check with atomic write — makes every regen
  path fail-safe regardless of how it is invoked: a malformed generation is
  refused with `status: error` and the pre-existing working executor is left
  byte-identical, so a regeneration can never leave a corrupt executor in place.

- **`cache-retention-sweep`** (both kinds) — prune the superseded plugin-cache
  version dirs the executor regeneration leaves behind. Run the DRY RUN first; it
  mutates nothing and reports the full keep/remove partition:

  ```bash
  python3 .plan/execute-script.py plan-marshall:marshall-steward:cache_retention sweep
  ```

  See the [`../SKILL.md`](../SKILL.md) Canonical invocations
  (`cache_retention — sweep`) for the verb shape. Parse `kept`, `removed`,
  `removed_count`, and `summary_message`. The keep-set is a strict UNION: a
  version dir is removed only when NO rule keeps it, so every `kept` row names
  the first keep-rule that fired and a run that removed nothing still explains
  itself. The two operator knobs are
  `system.retention.plugin_cache_keep_versions` (`N`, default `5`) and
  `system.retention.plugin_cache_keep_days` (`D`, default `3`) — see
  [`manage-config` data-model.md](../../manage-config/standards/data-model.md)
  § Retention Fields for their types, defaults, and the union semantics. The
  report echoes the resolved pair plus its `knob_source`, so a surprising
  keep-set is diagnosable without reading the config.

  **Nested gate — `cache-retention-prune` (STILL prompts under
  `integrate=true`).** The destructive apply is never automatic. When
  `removed_count > 0`, show the `removed` rows, then prompt:

  ```text
  AskUserQuestion:
    question: "Remove {removed_count} superseded plugin-cache version dir(s)?"
    header: "cache-retention-prune"
    options:
      - label: "Yes, prune"
        description: "Unlink the version dirs no keep-rule retained"
      - label: "No, keep everything"
        description: "Leave the cache untouched (the dry-run report stands)"
    multiSelect: false
  ```

  - **Yes** → apply the sweep:

    ```bash
    python3 .plan/execute-script.py plan-marshall:marshall-steward:cache_retention sweep --apply
    ```

  - **No** → leave the cache untouched.

  When `removed_count == 0` there is nothing to prune; report
  `summary_message` and continue without prompting. This nested gate prompts even
  when `integrate=true` suppressed the Stage 1 top-level gate.

A `consumer` plan runs `cache-freshness-check`, `regenerate-executor`, and
`cache-retention-sweep`; the meta-only `marketplace/targets/generate.py`
sub-step is absent from its `sub_steps` and MUST NOT be attempted (a consumer has
no marketplace source tree). A `meta` plan runs `regenerate-target-tree`,
`regenerate-executor`, and `cache-retention-sweep`; `cache-freshness-check` is
absent from its `sub_steps`.

> **Reload directive after executor regeneration.** Regenerating the executor may
> change the emitted agent set, and the registry is session-pinned at session
> start — so the running session must pick up the new artifacts. After this stage
> (when the executor was regenerated), resolve the harness-appropriate directive
> through the platform-runtime seam and surface it verbatim to the operator:
>
> ```bash
> python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session reload-directive
> ```
>
> On Claude the seam returns `/reload-plugins` (which picks up the regenerated
> executor / agent set live — only registered monitors would force a full
> restart, and plan-marshall registers none); on OpenCode it returns a `no-op`
> whose alternative is a full session restart. See [`../SKILL.md`](../SKILL.md) §
> "Session Reload Directive After Executor / Agent Changes" for the WHY the
> registry is session-pinned.

## Meta/consumer cache-freshness asymmetry

The Stage 1 asymmetry is exactly one entry wide, and it is deliberate:

| Kind | Gains `cache-freshness-check` | Gains `cache-retention-sweep` + `cache-retention-prune` |
|------|-------------------------------|----------------------------------------------------------|
| `meta` | **No** | Yes |
| `consumer` | **Yes** | Yes |

**Why the freshness gate is consumer-only.** The meta project keeps its own
plugin cache current through `project:finalize-step-sync-plugin-cache`, which
runs at the end of every plan's finalize phase and mirrors the freshly-generated
`target/claude/` tree into the cache. That step is **meta-project-only** (see the
repository `CLAUDE.md` § "Plugin Cache Sync"): it is a project-local skill under
`.claude/skills/`, registered in the meta project's own `marshal.json`, and
consumer projects neither ship it nor have it seeded. So the mechanism that keeps
the meta cache fresh is invisible to — and does not cover — a consumer, whose
cache is refreshed only when the operator explicitly runs
`/plugin marketplace update` and reinstalls. A consumer therefore has a real
"my cache silently fell behind" failure mode that meta does not, which is exactly
the failure the freshness gate refuses on. Adding the gate to the meta kind would
gate on a condition meta's own finalize pipeline already guarantees.

**Why the retention sweep applies to both.** Cache-version accumulation is not
asymmetric: both kinds regenerate the executor against the same versioned cache
tree and both leave superseded version dirs behind. The sweep and its
`cache-retention-prune` gate therefore run for both kinds.

## Stage 2: reconcile-config (mutating)

Honor the Stage 2 top-level gate, then reconcile `marshal.json`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config sync-defaults
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config steps-sort
```

See the `manage-config` Canonical invocations (`sync-defaults`, `steps-sort`) for
the verb shapes. Both are idempotent and byte-stable on an already-current config.

**Nested gate — `build-map` re-seed (STILL prompts under `integrate=true`).**
Compute the drift between the persisted `build.map` and the live-tree derivation,
then gate any re-seed behind an `AskUserQuestion` so deliberate hand-edits are
never clobbered — the same read-only drift gate the Re-Run Remediation Pass step
(c) uses (see [`../SKILL.md`](../SKILL.md)):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map drift
```

- **`in_sync: true`** → no drift; continue silently.
- **`in_sync: false`** → show the added/removed-glob diff, then prompt:

  ```text
  AskUserQuestion:
    question: "The persisted build.map differs from the live-tree derivation. Re-seed it?"
    header: "build.map drift"
    options:
      - label: "Yes, re-seed"
        description: "Overwrite build.map with the live derivation"
      - label: "No, leave as-is"
        description: "Keep the persisted build.map (preserves deliberate hand-edits)"
    multiSelect: false
  ```

  - **Yes** → re-seed via the force path:

    ```bash
    python3 .plan/execute-script.py plan-marshall:manage-config:manage-config build-map seed --force
    ```

  - **No** → leave the persisted `build.map` untouched.

This nested gate prompts even when `integrate=true` suppressed the Stage 2
top-level gate.

## Stage 3: verify (read-only)

Honor the Stage 3 top-level gate, then run exactly the Stage 3 `sub_steps` the
plan emitted for the resolved kind. Neither sub-step mutates the working tree.

**(a) `executor-preflight`** (both kinds) — executor / config staleness preflight:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor preflight
```

See the `tools-script-executor` Canonical invocations (`generate_executor` →
`preflight`) for the verb shape.

**(b) `content-drift-report`** (meta only — absent from a consumer plan) — the
thin CLI over the content-drift engine. Exit `0` means the emitted
`target/claude/` markdown matches a fresh emit; exit `1` means drift was detected
(or `target/claude` is not generated), with the drifted/missing/orphan paths
named in the TOON report:

```bash
python3 marketplace/targets/claude/content_drift_cli.py
```

If drift is reported, the fix is to re-run Stage 1's `generate.py` emit — the
source `.md` files under `marketplace/bundles/` are canonical and MUST NOT be
edited to satisfy the gate.

A `consumer` plan runs only `executor-preflight`; the meta-only
`content-drift-report` sub-step is absent from its `sub_steps` and MUST NOT be
attempted (a consumer has no `marketplace/targets/claude/content_drift_cli.py`).

## Stage 4: land (mutating)

Honor the Stage 4 top-level gate, then run the existing landing cycle AS-IS:

```text
Read references/landing-cycle.md
```

Execute that reference's procedure unchanged. Its nested gates — the land/leave
`AskUserQuestion` and the non-base branch-reuse confirmation — STILL prompt even
when `integrate=true` suppressed the Stage 4 top-level gate. Do NOT modify
`landing-cycle.md` to honor `integrate`.

## Partial-failure and abort handling

The upgrade flow performs **no rollback**. On a stage failure (a stage's
machinery exits non-zero or reports an error) OR an operator **Abort**:

1. **STOP at the failed / aborted stage.** Do NOT run any later stage.
2. **Report the partial state** — which stages completed, which stage stopped
   the flow, and the specific failure (e.g. the failing command and its error).
3. **Report the manual resume path** — any already-completed stages' mutations
   remain on disk (regenerated target/executor, reconciled config); the operator
   can re-run `/marshall-steward upgrade` after resolving the failure to continue
   from a clean state, or run the remaining stages' machinery by hand.

No stage is un-done. The reconciliation is forward-only.

## End-of-flow behavior

When all four stages complete (or the flow stops per the partial-failure
contract), return control to the steward's end-of-flow behavior:

- Invoked from **Main Menu option 5** → return to Main Menu Page 1.
- Invoked from the **`upgrade` early verb check** → the run ends (the verb
  bypassed the menu).
