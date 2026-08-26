# phase-6-finalize Required Steps

This file declares the canonical list of finalize steps that MUST be
marked done on `status.metadata.phase_steps["6-finalize"]` before the
`phase_handshake` script allows the phase to transition. It is parsed
by the `phase_steps_complete` invariant in
`plan-marshall:plan-marshall:_invariants._parse_required_steps`.

**Format**: one markdown bullet per step name. Lines that do not begin
with `- ` are ignored by the parser. Step names must match the
`--step` argument passed to `manage-status mark-step-done` at the tail
of each corresponding standards document.

**Ordering note**: declared order in this file is informational only.
Runtime execution order is `manifest.phase_6.steps` (composed at outline
time by `manage-execution-manifest:compose` and stored in
`.plan/local/plans/{plan_id}/execution.toon`). phase-6-finalize iterates
that list as written and does not re-sort or validate ordering at
runtime. The composer applies the per-step `order` frontmatter values
documented on each standards doc when assembling the manifest list.

**Activation note**: presence in this file makes a step REQUIRED for the
`phase_steps_complete` handshake when the step also appears in the
manifest. A step listed here but ABSENT from `manifest.phase_6.steps`
for the running plan is NOT enforced — the handshake checks completion
only for steps that the manifest actually scheduled. The handshake
parser MUST refuse to enforce a step that is not in the manifest;
otherwise a manifest pruning would deadlock the phase transition.

## Steps

- finalize-step-sync-baseline
- finalize-step-simplify
- finalize-step-security-audit
- push
- finalize-step-preference-emitter
- create-pr
- ci-verify
- architecture-refresh
- automatic-review
- sonar-roundtrip
- record-metrics
- archive-plan
- branch-cleanup
- validation
- lessons-capture
- adr-propose

## Step Ownership Contract

Every finalize step carries a declared **owner** —
`orchestrator-owned` or `leaf-dispatchable` — that determines which execution
context may run it. The owner is resolved deterministically by
`owner_of(step_id)` in
[`../../manage-execution-manifest/scripts/_manifest_core.py`](../../manage-execution-manifest/scripts/_manifest_core.py)
against the `ORCHESTRATOR_OWNED_STEPS` registry; the vocabulary and registry are
documented in
[`../../manage-execution-manifest/standards/manifest-schema.md`](../../manage-execution-manifest/standards/manifest-schema.md)
§ "Step ownership".

- **`orchestrator-owned`** steps sub-dispatch (they issue their own `Task:`
  dispatches — e.g. `finalize-step-plugin-doctor`,
  `default:pre-submission-self-review`, `automatic-review`,
  `finalize-step-simplify`). A dispatched `execution-context` leaf has no Task
  tool and CANNOT run them; the main-context orchestrator MUST own them.
- **`leaf-dispatchable`** steps are self-contained scripts or inline workflows
  the orchestrator MAY hand to a dispatched leaf.

Declaring the owner makes routing deterministic instead of
discovered-by-failure, and guarantees the `mark-step-done` obligation (below)
travels to the ACTUAL owner rather than being lost when the wrong context ran
the step.

**Canonicalized `mark-step-done` key.** `manage-status mark-step-done`
canonicalizes its `--step` value by stripping a leading `default:` prefix before
recording, so the recorded key always equals the bare manifest key the
dispatcher reads back — both `default:push` and `push` reconcile to `push`. This
is the write-side complement of the read-side key-normalization the
`manage-execution-manifest` id-keyed accessor family applies, and eliminates the
`step_record_mismatched_key` orphans. Step names in
the `## Steps` list above are the bare canonical keys.

## Reconciliation Contract

Before the loadability check below, `phase-6-finalize` SKILL.md Step 1.5 MUST
reconcile the frozen `manifest.phase_6.steps` against live `marshal.json`
configuration via `manage-execution-manifest reconcile --apply`. The manifest is
a write-time snapshot composed at outline time, so a plan that edits finalize
configuration during its own run reaches phase entry holding a view its own
edits invalidated.

The reconcile verb owns the fail-direction split, and this file does not restate
it: a frozen step whose standards doc is gone **and** which live config no
longer lists is DROPPED (the snapshot is merely behind); one that live config
**still** lists fails loud as `unreconcilable_step`. See
[`../../manage-execution-manifest/SKILL.md`](../../manage-execution-manifest/SKILL.md)
§ `reconcile` for the authoritative table, the narrow backfill rule, and the
fail-closed behaviour when live config is unreadable.

A reconcile that reports `reconciled: true` changes the step list, so the
dispatcher re-reads the manifest before the loadability check and the Step 3
dispatch loop.

## Loadability Contract

After the reconciliation above and before any step in `manifest.phase_6.steps`
is dispatched, `phase-6-finalize`
SKILL.md Step 1.5 MUST verify that every
built-in step's standards file is present and readable. The check is
implemented by `manage-execution-manifest validate-loadable` and runs
exactly once per phase entry, immediately after the manifest is read in
Step 2 and before the dispatch loop in Step 3.

**Scope**: the contract covers **built-in** steps only — bare names that
resolve to `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/{name}.md`
in the deployed plugin cache. External steps (`project:` / `bundle:skill`)
are NOT covered: their loadability is the responsibility of the host
plugin cache, and a missing `Skill:` reference surfaces at dispatch time
as a skill-resolution error (a different failure mode than a missing
standards file).

**Subcommand**: `manage-execution-manifest validate-loadable` accepts
either `--step-id {id}` (single-step form) or `--all` (bulk form for the
entire `manifest.phase_6.steps` list). The single-step return shape is
`{status, step_id, standards_path, loadable: bool, message?}`; the bulk
return shape is `{status, results[N]{step_id, standards_path, loadable,
message?}, unloadable_count}`. See
[`../../manage-execution-manifest/SKILL.md`](../../manage-execution-manifest/SKILL.md)
§ `validate-loadable` for the authoritative API.

**Failure shape**: on any unloadable built-in step, Step 1.5 aborts
finalize with the canonical actionable message:

> step `{step_id}` is missing standards file
> `{standards_path}` — the plan likely deleted the file without sweeping
> `marshal.json`

The reason literal is **origin-neutral**: it states why the step does not
resolve, not where the step id came from. Provenance is stated once, by the
caller that can actually establish it —
`_manifest_validation.check_emitted_steps_resolvable`, whose wrapper phrasing
names the step "in marshal.json is unresolvable" and so distinguishes a
marshal.json-authored step from a routed / composer-injected one. The
remediation hint above stays: it is advice about the likely repair, not a claim
about the origin.

Self-modifying plans that delete a `phase-6-finalize/standards/{name}.md`
without also pruning `marshal.json::plan.phase-6-finalize.steps` are the
motivating failure mode. The fail-fast guard converts a confusing
mid-dispatch failure (the dispatcher tries to load the deleted standards
file when its turn comes) into an immediate, actionable error at phase
entry.

Because the reconciliation above runs first, a plan that pruned **both** the
standards file and the `marshal.json` entry no longer trips this abort — its
frozen manifest is reconciled instead. The abort is now reserved for the
half-done sweep, which is the case it was written for.

**Activation**: presence of every built-in step in this file plus
`manifest.phase_6.steps` is the trigger. A step listed here but absent
from the manifest is NOT enforced (matching the "Activation note" rule
above). The handshake parser MUST refuse to enforce a step that is not
in the manifest; otherwise a manifest pruning would deadlock the phase
transition.
