# Check: dispatch-topology (per-plan)

Directly verifies the roadmap's **leaf/dispatch-topology invariant**: a dispatched
subagent is a **leaf** — it returns a signal, it never issues a further
`Task:` / `execution-context` dispatch. The **only** component allowed to dispatch
further subagents is the main-context orchestrator. The canonical contract lives
in [`ref-workflow-architecture/standards/agents.md`](../../../../marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md).
This check verifies the invariant DIRECTLY from each plan's dispatch log rather
than inferring it from generic symptoms.

The deterministic computation lives in `scripts/audit.py`
(`check_dispatch_topology`); this sub-document is the interpretation guide.

## Inputs the check reads

Per scanned plan, the script reads `logs/work.log` and matches every
`[DISPATCH] (caller) target=… role=…` line — the record of one subagent spawn.
The line names the **dispatcher** via its `(bundle:skill)` caller prefix and the
spawned agent via `target=`. A bare `[DISPATCH] role=phase-N` phase-entry marker
that carries **no** `target=` is NOT a spawn record and is ignored (it is the
phase-attribution marker the sequence and input-integrity checks consume).

## Computation

For each `[DISPATCH] … target=…` line the script:

1. Extracts the `(bundle:skill)` caller prefix and increments `dispatch_count`.
2. Classifies the caller against the **allowed-dispatcher allowlist**
   (`_DISPATCH_ALLOWED_CALLER_RE`): a caller is allowed when it is the orchestrator
   (`plan-marshall:plan-marshall`) or a phase workflow the orchestrator uses as
   caller-phase context (`plan-marshall:phase-1-…` … `plan-marshall:phase-6-…`).
3. A caller that is NOT allowed is a **topology violation** — a leaf (e.g.
   `plan-marshall:execute-task`, `plan-marshall:automated-review`,
   `plan-marshall:sonar-roundtrip`, a verify / finalize leaf step, a retrospective
   aspect) that spawned a subagent. Its caller name is added to `violators`.

An **allowlist** is used rather than a leaf denylist so a newly-added leaf skill is
caught by default — the check does not need to enumerate every leaf.

## Emitted columns

```
rows[N]{plan_id,dispatch_count,leaf_dispatch,violators,severity}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `dispatch_count` | Total `target=` subagent dispatches recorded in the plan's `work.log`. |
| `leaf_dispatch` | Count of dispatches whose caller is a leaf (a topology violation). |
| `violators` | `;`-joined distinct leaf caller skills that emitted a dispatch, or empty. |
| `severity` | Uniform D1 severity column: `genuine` when `leaf_dispatch > 0`, else `informational`. |

`genuine_signal_count` counts the plans with at least one leaf-emitted dispatch. A
plan whose every dispatch came from an allowed dispatcher is `informational`.

## How the orchestrator interprets the rows

- **`leaf_dispatch > 0` (`severity: genuine`)** — a real, high-priority invariant
  violation: a subagent spawned another subagent. Name the `violators` caller
  skill(s); the fix is in the LEAF's workflow (it must return a signal to the
  orchestrator, never dispatch). A recurring violator across plans is a systemic
  signal that flows into the recurring-pattern detector and the three-gate
  lesson-filing path, keyed to the **violating leaf skill**, not the plan.
- **`leaf_dispatch == 0`** — the plan's dispatch topology conforms. Still
  `informational`, not a free "all healthy": a plan with NO `target=` dispatch
  markers at all (e.g. missing work.log) contributes no evidence — cross-read with
  input-integrity's `missing_dispatch_markers` before concluding the topology was
  actually exercised.

The `cross-check-synthesis` coupling `dispatch_topology_reentry` joins a
leaf-dispatch violation with a sequence `phase_reentry` (the extra dispatch
observed as runtime rework) — see [`cross-check-synthesis.md`](cross-check-synthesis.md).

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason.

## Critical rules

- The script is the single source of truth for the dispatch parse and the
  allowed-dispatcher allowlist. Do not re-grep the logs or re-derive the
  classification in chat.
- The allowlist (`_DISPATCH_ALLOWED_CALLER_RE`) and the dispatch-line grammar
  (`_DISPATCH_TARGET_RE`) are module constants. If the orchestrator's dispatch-line
  format or the set of allowed dispatcher contexts changes, edit `scripts/audit.py`
  rather than substituting a different reading.
- This check is read-only; it never edits `.plan/` files.
