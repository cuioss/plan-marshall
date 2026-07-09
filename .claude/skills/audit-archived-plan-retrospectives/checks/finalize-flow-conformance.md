# Check: finalize-flow-conformance (per-plan)

Directly verifies the **post-#849/#850 finalize mechanics** rather than inferring
finalize health from generic symptoms. #849 shipped a deterministic `ci_verify`
gate + an adaptive ci-wait ratchet + the widened merge mutex; #850 shipped
deterministic dist versioning. This check reads each plan's finalize roster and
persisted CI artifacts and reports where the recorded finalize flow does not
conform to that mechanics.

The deterministic computation lives in `scripts/audit.py`
(`check_finalize_flow_conformance`); this sub-document is the interpretation
guide.

## Inputs the check reads

Per scanned plan:

| Input | Field(s) read | Used for |
|-------|---------------|----------|
| `execution.toon` | `phase_6.steps` (the composed finalize roster, bare names) | `has_pr_step` (`create-pr`), `has_ci_verify_step` (`ci-verify`) |
| `artifacts/ci-runs/{run_id}/manifest.toon` | `wait_outcome`, `final_status` | CI wait/resolution outcome per persisted run |

The `phase_6.steps` roster is the composed finalize plan (each `default:`-prefixed
or bare step ID). The `artifacts/ci-runs/*/manifest.toon` files are the persisted
`ci_verify` outcomes (`wait_outcome ∈ {completed, deadline_exceeded}`,
`final_status ∈ {success, failure, none, timeout, ""}`) — one directory per CI run,
so a loop-back cascade produces N+1 run directories. The check reads the LATEST
run's `final_status`.

## Computation and flags

| Flag | Fires when | Reading |
|------|-----------|---------|
| `missing_ci_verify` | The roster contains `create-pr` (a PR was created) but NO `ci-verify` step. | The #849 deterministic CI gate is absent — a pre-#849 finalize shape that pushed a PR with no deterministic ci-verify gate. |
| `ci_wait_timeout` | Any persisted ci-run recorded `wait_outcome: deadline_exceeded`. | The adaptive ci-wait ratchet hit its budget ceiling before CI settled — the run timed out waiting. |
| `ci_unresolved(<status>)` | ≥1 ci-run exists AND the LATEST run's `final_status` is not `success` (and not empty). | Finalize did not reach a green CI on the recorded runs (`failure` / `timeout` / `none`). |

A plan that created no PR (no `create-pr` step) and persisted no ci-runs is
conformant by construction (empty `flags`) — a local-only or docs-only finalize
has no CI gate to verify.

## Emitted columns

```
rows[N]{plan_id,has_pr_step,has_ci_verify_step,ci_run_count,final_status,flags,severity}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `has_pr_step` | `true` when the roster contains `create-pr`. |
| `has_ci_verify_step` | `true` when the roster contains `ci-verify`. |
| `ci_run_count` | Count of persisted `artifacts/ci-runs/*/` run directories. |
| `final_status` | The latest persisted run's `final_status` (empty when no run). |
| `flags` | `;`-joined conformance flags (empty for a conformant plan). |
| `severity` | Uniform D1 severity column: `genuine` when any flag fired, else `informational`. |

## How the orchestrator interprets the rows

- **`missing_ci_verify`** — the plan pushed a PR with no deterministic ci-verify
  gate. On an archived plan created BEFORE #849 shipped this is expected (era
  boundary `#849`) — read it as a pre-#849 finalize shape, not a defect. On a plan
  created after #849 it is a genuine conformance gap: the deterministic gate was
  dropped from the roster.
- **`ci_wait_timeout`** — the adaptive ci-wait ratchet hit its budget. Cross-read
  with the global-log-analysis impossible/slow ci-wait rows: a recurring timeout is
  a signal the ci-wait ceiling is mis-tuned for the project's CI latency.
- **`ci_unresolved`** — the recorded CI never went green. Cross-read with
  quality-chain (`build_pending_pile`) and sequence `ci_rerun`: an unresolved CI
  that also re-ran is the shift-right rework the `finalize_gate_gap_ci_rerun`
  coupling surfaces.
- **conformant (empty `flags`)** — the finalize flow matches the post-#849
  mechanics. `informational`; do not read a conformant flow as a clearance for the
  plan's other facets.

The `cross-check-synthesis` coupling `finalize_gate_gap_ci_rerun` joins a
non-conformant finalize flow with sequence `ci_rerun` — see
[`cross-check-synthesis.md`](cross-check-synthesis.md).

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason (e.g. an archived plan predating the `#849` era boundary).

## Critical rules

- The script is the single source of truth for the roster read and the CI-manifest
  parse. Do not re-read `execution.toon` or the ci-runs manifests in chat.
- The step-name matching (`create-pr` / `ci-verify`) and the manifest field reads
  (`wait_outcome` / `final_status`) mirror the canonical finalize roster and the
  `manage-ci-artifacts` manifest schema. If either schema changes, edit
  `scripts/audit.py` rather than substituting a different reading.
- This check is read-only; it never edits `.plan/` files.
