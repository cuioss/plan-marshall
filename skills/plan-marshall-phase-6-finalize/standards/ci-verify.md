---
lane:
  class: core
  cost_size: XS
name: default:ci-verify
description: "Deterministic ci-verify executor — classify CI run failures into the multi-failure-mode taxonomy and emit one structured triage finding per failing check (requires: [ci-complete] in consume-failures mode)"
order: 22
requires: [ci-complete]
mutates_source: false
head_dependent: true
default_on: true
presets:
  - standard
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# ci-verify Standards

Standards for the `default:ci-verify` finalize step — an **inline
deterministic executor** (`scripts/ci_verify.py`), NOT a dispatched
execution-context workflow. The CI-check classification is a fixed
taxonomy-table lookup, so the green pass-through pays no LLM envelope
and only a genuinely-red CI routes to the LLM `verification-feedback`
triage. This extends the dispatch-granularity "find the LLM core"
model (`../extension-api/standards/dispatch-granularity.md` § 5) rather
than contradicting it — the wrapping step earns no envelope for the
green pass-through.

The executor is placed on the inline pure-executor roster alongside
`push` and `branch-cleanup`. The step's `ext-point-finalize-step`
frontmatter lives HERE (this standards doc carries `name:
default:ci-verify`, `order: 22`, `default_on: true`), mirroring how
`branch-cleanup.md` — also a pure executor — carries its finalize-step
frontmatter in `standards/`.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

**This document's own application of it**, which the shared statement does not carry: an absent `ci_final_status` is an **unread** CI verdict, never a green one. The two calls this document makes — `ci_complete_precondition resolve` and `ci_verify run` — are the pair that decides whether CI was read at all, so a missing verdict here fails closed rather than passing through.

## Executor contract

The dispatcher runs the executor inline through the executor proxy after
the `consume-failures` precondition resolves. It threads the settled CI
verdict from the precondition envelope into the script:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_verify run \
  --plan-id {plan_id} --pr-number {pr_number} --worktree-path {worktree_path} \
  --provider {github|gitlab} \
  --final-status {success|failure|none|timeout} \
  --wait-outcome {completed|deadline_exceeded} \
  --head-sha {head_sha}
```

Field threading from the `consume-failures` precondition envelope
(`ci_complete_precondition resolve --mode consume-failures`):

- `ci_final_status` → `--final-status` (the dispatcher maps the
  precondition's `no_checks` to `none`).
- `wait_outcome` → `--wait-outcome` (constrained to the
  `{completed, deadline_exceeded}` enum — see the persist guard below).
- `head_sha` → `--head-sha` (may be empty; the required-field guard then
  skips artifact persistence for this run).

The executor's steps:

1. **Fetch the full `checks[]` array** via `ci checks status --pr-number`
   so a green run still records per-job evidence.
2. **Capture the jobs file** — write the normalized `checks[]` array to
   `.plan/temp/{plan_id}-ci-jobs-{run_id}.json`; an empty array writes
   `[]` (a deliberate `jobs_source: empty` manifest).
3. **Persist artifacts** behind the required-field guard (below).
4. **Green early return** (`final_status == success` AND no failing
   checks): mark the step `done` with `--head-at-completion`, ZERO
   dispatch, and return `outcome: green` — or `outcome: green_unrecorded`
   when that mark was refused (see "Return shape" below).
5. **Red CI**: file exactly one taxonomy finding per failing check (plus
   the `ci_no_checks` finding on `final_status == none`) and return
   `outcome: needs_triage` carrying the single producer value
   `producers: [ci-verify]`. The per-row distinction rides each finding's
   `[subtype]` tag. The executor does NOT mark the step `done` on the red
   path and does NOT dispatch `verification-feedback` itself — it returns
   the needs-triage signal and the dispatcher runs exactly ONE
   `verification-feedback` invocation with `producer=ci-verify` (the sole
   LLM step, red-CI only), then records the terminal step outcome.

The green-early-return / no-dispatch bypass is documented BEFORE the
red-CI triage dispatch it bypasses (steps 4 → 5 above).

### Return shape

```toon
status: success | error
plan_id: <str>
final_status: success | failure | none | timeout
outcome: green | green_unrecorded | needs_triage
run_id: <str>
head_sha: <str>
persisted: true | false
persist_skipped_reason: <field>   # present only when persisted == false
findings_filed: <int>
producers: [ci-verify]           # present only when outcome == needs_triage
step_marked_done: true | false    # true only when the mark returned success
step_mark_error: <str>            # present only when outcome == green_unrecorded
step_mark_message: <str>          # present only when outcome == green_unrecorded
```

`green_unrecorded` is a green CI verdict whose `mark-step-done` write was
refused: CI passed, but the step record does not say so. `step_mark_error`
carries the mark's own `error` and `step_mark_message` its `message`, so a
recorded green and a refused one are distinguishable from the payload alone.

**Dispatcher action on `green_unrecorded`**: stop with the tool's message
(`step_mark_message`, naming `step_mark_error`) and do NOT advance past the
step. The step has no `done` record, so advancing would carry the run past a
step the record still shows as unfinished.

The canonical argparse surface for the script is published in
[`../SKILL.md`](../SKILL.md); the script registers its own `run`
subcommand via `generate_executor.py`.

## Required-field + `--wait-outcome`-enum persist guard

Before invoking `manage-ci-artifacts persist`, the executor verifies ALL
required flags are non-empty — `--plan-id`, `--run-id`, `--head-sha`,
`--pr-number`, `--provider` — AND constrains `--wait-outcome` to its
`{completed, deadline_exceeded}` enum, **never copying `--final-status`'s
value into `--wait-outcome`**. `run_id` is derived from the checks' run
URLs; `head_sha` is threaded from the precondition. When any required
field is empty, the executor skips the persist call for that run (a
`persist_skipped_reason` names the missing field) and continues — artifact
persistence is advisory and MUST NOT block the green early return or step
completion. An out-of-enum `--wait-outcome` value clamps to `completed`
so the persist flag is always legal.

Moving the persist call to this validated Python site structurally
eliminates the recurring `manage-ci-artifacts persist` argparse-drift
class (the flag set and the `--wait-outcome` enum are enforced in code,
not re-typed per finalize).

`mark-step-done --step` uses the bare manifest key `ci-verify` (NOT a
`default:`-prefixed key).

## Placement

`ci-verify` runs immediately AFTER `create-pr` and BEFORE
`automatic-review`. Rationale: `create-pr` is the first moment at
which a server-side CI run exists to consume; `automatic-review` and
`sonar-roundtrip` both benefit from the CI verdict already being
triaged when they run. Placing `ci-verify` between `automatic-review`
and `sonar-roundtrip` would be wrong — `automatic-review` can itself
depend on CI conclusions the reviewer-bot observed, and waiting until
then to surface CI failures delays the loop-back signal unnecessarily.

The canonical order is each step's own `order:` frontmatter value — `ci-verify`
declares `22`, between `create-pr` (`20`) and `automatic-review` (`30`). See
[`../SKILL.md`](../SKILL.md) § "Step Types" for the authority (and the
central lane/order contract in
[`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md));
a hand-maintained copy of the full step list is not kept here — a second
enumeration of a registry-derived order has to be re-edited on every step
added, removed, or reordered, and a copy that falls behind states an order
the registry does not have.

## Precondition mode

`ci-verify` declares `requires: [ci-complete]` in its frontmatter
(same as `automatic-review` and `sonar-roundtrip`), but unlike those
two it is the *only* consumer that runs the precondition in
`consume-failures` mode (Step 3 of [`../SKILL.md`](../SKILL.md) §
"Precondition resolution"). In this mode the resolver runs the same
wait loop but threads `final_status ∈ {success, failure, none,
timeout}` and `failing_checks` through to the executor WITHOUT
short-circuiting the step to `failed`. Existing consumers keep the
default `strict` mode and observe no behaviour change.

A `status: wait_pending` answer carries the still-running checks
(`running_checks`), the number of the re-wait about to be issued
(`rewait_number`) and the bound (`rewait_bound`). The
executor is NOT run on `wait_pending`: nothing has failed, so there is
nothing to classify and no finding to file. The dispatcher re-issues the
resolver instead (see [`../SKILL.md`](../SKILL.md) § "Precondition
resolution").

The bound is three re-waits per HEAD — four waits in total — held as
`MAX_PENDING_REWAITS` in `scripts/ci_complete_precondition.py`. The
resolver counts the lapses itself and resets the count when HEAD changes.
The lapse after the bound returns `wait_failed` with `ci_final_status:
timeout`. `strict` mode never returns `wait_pending`.

The flag flows from the dispatcher's resolver invocation:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_complete_precondition \
  resolve --plan-id {plan_id} --worktree-path {worktree_path} \
  --pr-number {pr_number} --mode consume-failures
```

## Failure-mode taxonomy

This table is the executor's deterministic classification contract. The
`classify_check` function in `scripts/ci_verify.py` evaluates the rows in
this order per failing check.

| Row | Failure mode | Detection source | Producer string | Subtype tag | Typical fix path |
|-----|--------------|------------------|------------------|-------------|------------------|
| a | Sonar quality-gate failure inside a build job | The persisted job log of the failing check carries the sonar-scanner marker `QUALITY GATE STATUS: FAILED`, AND the plan's execution manifest carries the `sonar-roundtrip` step | `ci-verify` | `ci_sonar_gate` | Deferral: `sonar-roundtrip` owns the gate and triages it; ci-verify files the deferral only and MUST NOT double-report it as a build or policy failure |
| b | Build / test / lint / coverage failure | A failing check whose workflow name AND job name match no policy pattern — the DEFAULT | `ci-verify` | `ci_build_failure` | Open fix-task on failing module; loop_back |
| c | Policy-workflow failure (licence/CLA, dependency review, CodeQL, labels/title) | CI check whose workflow OR job name matches the closed policy list | `ci-verify` | `ci_policy_failure` | Depends on policy: accept / suppress / fix |
| d | Explicit `conclusion=failure` | per-check conclusion | `ci-verify` | (a), (b) or (c) above | per-row |
| e | Cancelled (`conclusion=cancelled`) | per-check conclusion | `ci-verify` | `ci_cancelled` | accept (manual cancellation) / retry |
| f | Action required | per-check conclusion | `ci-verify` | `ci_action_required` | operator approval; accept after approval |
| g | Stale (`conclusion=stale`) | per-check conclusion | `ci-verify` | `ci_stale` | re-run CI (HEAD advanced past check's commit) |
| h | Timeout (`conclusion=timed_out`, OR a run still not terminal) | per-check conclusion / `wait_outcome=deadline_exceeded` with no definitively failed check | `ci-verify` | `ci_timeout` | retry / accept (flaky infra) |
| i | No checks reported (`final_status=none`) | zero checks across PR | `ci-verify` | `ci_no_checks` | confirm CI is configured; accept if intentional |
| j | CI never ran vs CI ran red | distinguished by (i) vs (b..h) | n/a — handled by row choice | n/a | covered by the per-row subtype tag |

### Notes on the taxonomy

- **Definitive conclusions win over the deadline fallback.** Rows (e)
  cancelled, (f) action_required, and (g) stale are evaluated BEFORE the
  (h) timeout row because the timeout row fires on the run-level
  `wait_outcome=deadline_exceeded` signal in addition to a per-check
  `timed_out` conclusion. A check that concluded `cancelled` /
  `action_required` / `stale` before the run hit its wait deadline keeps
  its own definitive subtype; only a check WITHOUT a definitive
  failure/cancel/action/stale conclusion (e.g. still pending) falls
  through to the timeout row under `deadline_exceeded`.

- **Row (h) has two meanings.**
  `ci_timeout` is filed for a check whose own conclusion is `timed_out`,
  and for a check that is still running when the resolver returns
  `wait_failed` / `timeout` (see "Precondition mode" above). A wait the
  resolver answers `wait_pending` files nothing: the executor is not run.
  When the executor does run under `deadline_exceeded` and at least one check has a definitive
  failing conclusion, the still-running checks are dropped from the
  failing set, so they produce no `ci_timeout` finding beside the real
  failure. Only when no check has definitively failed are the
  still-running checks kept and classified under row (h). The same rule
  applies to a failing set threaded in from the precondition.

- **Row (a) is a deferral, not a second report.** A Sonar quality gate
  surfaced inside a Maven build job carries the scanner's own marker in the
  job log (`QUALITY GATE STATUS: FAILED`). When the plan's execution manifest
  carries the `sonar-roundtrip` step, that step owns the gate, so ci-verify
  files a `ci_sonar_gate` deferral instead of a build or policy finding. When
  the manifest does not carry the step — or cannot be read at all — no owner
  exists in this run and the same check stays a build failure, the safe
  direction. A check that failed in the same job for
  any other reason (a compile error, for example) carries no marker and stays
  a build failure.

- **Build versus policy is a closed policy list, not a build list.** A failing
  check is a `ci_build_failure` unless its workflow or job name matches one of
  the policy patterns — licence/CLA, dependency review, CodeQL, labels/title.
  An unrecognised name therefore fails toward a fix rather than toward an
  "accept"; so does a failing check whose conclusion is not one of the
  recognised failing conclusions. The list is single-sourced in the executor
  (`_POLICY_PROFILE_PATTERNS`); no configuration overrides it. Job names are
  matched too, so a build job whose name happens to carry one of those words
  (for example `license-check`) is classed as policy — the spec asks for
  workflow OR job name, and the marker words are the policy workflows' own.

- **One producer value; subtypes carry the row.** The executor returns the
  single producer string `ci-verify`, which `verification-feedback` accepts in
  its one accept-set. A taxonomy row is told apart by the finding's `[subtype]`
  title tag, never by a second producer string, so no taxonomy label can be
  refused as an `unknown_producer`.

- **Finding subtype** is carried in the finding's title as a prefix tag
  `[ci_build_failure]`, `[ci_policy_failure]`, `[ci_sonar_gate]`, etc., so
  retrospectives and `manage-findings list --type triage` can grep for specific
  subtypes without a schema change.

- **One finding per failing check.** A PR with three build-failure checks plus
  one stale check produces four findings (three tagged `[ci_build_failure]` and
  one `[ci_stale]`), each carrying its own subtype. The executor returns
  `producers: [ci-verify]` for all of them, so the dispatcher runs ONE
  `verification-feedback` invocation with `producer=ci-verify` — one dispatch
  per run, NOT per finding.

- **Every finding is keyed on the run of its own check.** The failing-check
  finding's `--file-path` is `artifacts/ci-runs/{check_run_id}/{slug}.log`,
  where `{check_run_id}` is the run id of the CHECK that failed, not the
  run-level id of the first check, and `{slug}` is the check name slugified as
  `manage-ci-artifacts` names it (lowercase, non-alphanumeric runs collapsed to
  `-`). A check carrying no run id falls back to the
  run-level id, and to `no-run-id` when neither is known. Two failing runs at
  one head therefore file under two directories and neither overwrites the
  other's evidence. The `final_status == none` finding is the one exception: it
  names the run's manifest (`artifacts/ci-runs/{run_id}/manifest.toon`), because
  no check exists to key on. When the check carries a persisted `log_file`, that
  real pointer is the finding's `--file-path`; otherwise the constructed path is
  used. `ci checks status` fills the failing
  entry's `log_file` / `filtered_log_file`; when it cannot, it names the reason
  in `log_unavailable_reason` — the values and their discriminations are owned
  by [`api-contract.md`](../../tools-integration-ci/standards/api-contract.md) §
  "Transport shape: per-entry, NOT scalar top-level" — so an empty pointer is
  never mistaken for a log that was not needed.

## Eager-fetch and persist contract

Every ci-verify invocation persists CI run artifacts under
`artifacts/ci-runs/{run_id}/` (one manifest + one log per job) BEFORE
classification, including green-CI runs (for retrospective audit).
Multi-run loop-backs accumulate: a fresh CI run from a HEAD-advancing
commit creates a new `{run_id}` directory rather than overwriting the
previous one. No automatic pruning at finalize completion — retention
is the plan dir's lifetime.

The persist call MUST be handed the full jobs array via `--jobs-file`
so `manifest.jobs[]` enumerates every job (one row per check) with a
non-empty `log_path`. The executor captures `checks[]` from the
`ci checks status` envelope into a `.plan/temp/` JSON file and passes
that path to `manage-ci-artifacts persist --jobs-file …`; the manifest's
`jobs_source` field labels the outcome (`enumerated` when the array
was supplied, `empty` otherwise) so a zero-jobs manifest on a green-CI
run is structurally distinguishable from a genuine no-CI verdict. A
`jobs_source: empty` value on a green-CI run is a defect signal — not
the route by which `ci_no_checks` findings get filed (those flow from
`final_status=none`).

The persistence layer is implemented by the `manage-ci-artifacts`
skill ([`../../manage-ci-artifacts/SKILL.md`](../../manage-ci-artifacts/SKILL.md)).
Findings reference per-job log paths via `--file-path` so the
triager has direct evidence; the `ci_no_checks` row uses the manifest
itself as evidence.

### Read side: `read --run-id` and `read --latest`

The persist/read contract is symmetric: every persisted manifest can
be retrieved via either of the two read accessors below.

- `manage-ci-artifacts read --plan-id {plan_id} --run-id {run_id}` —
  read a specific run by identifier. Returns
  `{manifest, log_paths[]}` on success or `status: error,
  error: manifest not found for run_id={run_id}` when absent.
- `manage-ci-artifacts read --plan-id {plan_id} --latest` — read the
  most-recently-persisted manifest. Recency is determined by the
  `fetched_at` timestamp inside each manifest (never by lexicographic
  `run_id` sorting — run-id monotonicity is a GitHub-specific
  assumption no caller should bake in). Returns the same shape as
  `--run-id`, or `status: error, error: no_persisted_runs` when no
  manifests exist yet.

The two flags are mutually exclusive; the read subparser enforces
exactly one. The `--latest` accessor reuses the `list` enumeration
internally, so the predicate "which manifests are eligible?" stays in
one place; the only difference from `list` is that `--latest` picks
the newest instead of returning all rows.

## HEAD-dependent re-fire

`ci-verify` is HEAD-dependent: a loop-back commit MUST re-fire it
against the new HEAD's CI run. Membership is declared, not listed —
this doc's `head_dependent: true` frontmatter fact IS the declaration
the dispatcher's re-entry check reads (see
[`../../extension-api/standards/ext-point-finalize-step.md`](../../extension-api/standards/ext-point-finalize-step.md)
§ "Implementor Frontmatter").
The green early-return marks the step `done` with `--head-at-completion
{sha}` (the executor resolves the worktree HEAD immediately before the
`mark-step-done` call) so the dispatcher's HEAD-advance comparison can
detect a stale `done` record after a future loop-back commit advances
HEAD. On every re-fire, a new `run_id` directory is created (idempotence
applies per `run_id`, not per plan), so the audit trail accumulates.

## Cross-references

- [`automatic-review`](../../automatic-review/SKILL.md) — sibling consumer
  that uses the precondition in `strict` mode; ci-verify's
  `consume-failures` mode is the only divergence.
- [`sonar-roundtrip.md`](../workflow/sonar-roundtrip.md) — owns row (a). If a
  project wires Sonar as a GitHub check, the row-(c) finding here
  and the row-(a) finding there both reference the same upstream
  defect; the operator triages the row-(c) finding as "duplicate of
  sonar-roundtrip" or accepts via the policy producer.
