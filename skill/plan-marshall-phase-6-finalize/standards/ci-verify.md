---
lane:
  class: core
  cost_size: XS
name: default:ci-verify
description: "Deterministic ci-verify executor — classify CI run failures into the multi-failure-mode taxonomy and emit one structured triage finding per failing check (requires: [ci-complete] in consume-failures mode)"
order: 22
requires: [ci-complete]
mutates_source: false
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
   dispatch, and return `outcome: green`.
5. **Red CI**: file exactly one taxonomy finding per failing check (plus
   the `ci_no_checks` finding on `final_status == none`) and return
   `outcome: needs_triage` carrying the distinct per-producer strings.
   The executor does NOT mark the step `done` on the red path and does
   NOT dispatch `verification-feedback` itself — it returns the
   per-producer needs-triage signal and the dispatcher runs
   `verification-feedback` (the sole LLM step, red-CI only), then records
   the terminal step outcome.

The green-early-return / no-dispatch bypass is documented BEFORE the
red-CI triage dispatch it bypasses (steps 4 → 5 above).

### Return shape

```toon
status: success | error
final_status: success | failure | none | timeout
outcome: green | needs_triage
run_id: <str>
head_sha: <str>
persisted: true | false
persist_skipped_reason: <field>   # present only when persisted == false
findings_filed: <int>
producers: [str, ...]             # present only when outcome == needs_triage
step_marked_done: true | false    # true only on the green path
```

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
`architecture-refresh`. Rationale: `create-pr` is the first moment at
which a server-side CI run exists to consume; `architecture-refresh`,
`automated-review`, and `sonar-roundtrip` all benefit from the CI
verdict already being triaged when they run. Placing `ci-verify`
between `automated-review` and `sonar-roundtrip` would be wrong —
`automated-review` can itself depend on CI conclusions the reviewer-bot
observed, and waiting until then to surface CI failures delays the
loop-back signal unnecessarily.

The canonical default order:

```text
pre-submission-self-review
push
create-pr
ci-verify          ← here
architecture-refresh
automated-review
sonar-roundtrip
record-metrics
archive-plan
branch-cleanup
validation
lessons-capture
```

## Precondition mode

`ci-verify` declares `requires: [ci-complete]` in its frontmatter
(same as `automated-review` and `sonar-roundtrip`), but unlike those
two it is the *only* consumer that runs the precondition in
`consume-failures` mode (Step 3 of [`../SKILL.md`](../SKILL.md) §
"Precondition resolution"). In this mode the resolver runs the same
wait loop but threads `final_status ∈ {success, failure, none,
timeout}` and `failing_checks` through to the executor WITHOUT
short-circuiting the step to `failed`. Existing consumers keep the
default `strict` mode and observe no behaviour change.

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
| a | Sonar quality-gate failure | Sonar provider (NOT a GitHub check) | n/a (out of ci-verify scope) | n/a | `sonar-roundtrip` triage; ci-verify MUST NOT double-report |
| b | Build / test / lint / coverage failure | CI check whose `workflow_name` matches a build profile | `ci-verify-build` | `ci_build_failure` | Open fix-task on failing module; loop_back |
| c | Policy-workflow failure (license/cla, dep-review, codeql) | CI check whose `workflow_name` does NOT match a build profile | `ci-verify-policy` | `ci_policy_failure` | Depends on policy: accept / suppress / fix |
| d | Explicit `conclusion=failure` | per-check conclusion | (b) or (c) above | (b) or (c) above | per-row |
| e | Cancelled (`conclusion=cancelled`) | per-check conclusion | `ci-verify-cancelled` | `ci_cancelled` | accept (manual cancellation) / retry |
| f | Action required | per-check conclusion | `ci-verify-action-required` | `ci_action_required` | operator approval; accept after approval |
| g | Stale (`conclusion=stale`) | per-check conclusion | `ci-verify-stale` | `ci_stale` | re-run CI (HEAD advanced past check's commit) |
| h | Timeout (`conclusion=timed_out` OR wait-deadline) | per-check conclusion / `wait_outcome=deadline_exceeded` | `ci-verify-timeout` | `ci_timeout` | retry / accept (flaky infra) |
| i | No checks reported (`final_status=none`) | zero checks across PR | `ci-verify-missing` | `ci_no_checks` | confirm CI is configured; accept if intentional |
| j | CI never ran vs CI ran red | distinguished by (i) vs (b..h) | n/a — handled by row choice | n/a | covered by per-row producer split |

### Notes on the taxonomy

- **Definitive conclusions win over the deadline fallback.** Rows (e)
  cancelled, (f) action_required, and (g) stale are evaluated BEFORE the
  (h) timeout row because the timeout row fires on the run-level
  `wait_outcome=deadline_exceeded` signal in addition to a per-check
  `timed_out` conclusion. A check that concluded `cancelled` /
  `action_required` / `stale` before the run hit its wait deadline keeps
  its own definitive producer; only a check WITHOUT a definitive
  failure/cancel/action/stale conclusion (e.g. still pending) falls
  through to the timeout row under `deadline_exceeded`.

- **Row (a) is explicitly excluded** from ci-verify's scope. Sonar's
  quality-gate is fetched by `sonar-roundtrip` from the Sonar API, not
  from the GitHub-checks surface. If a project has wired Sonar as a
  GitHub status check, that check appears under row (c)
  `ci_policy_failure` — ci-verify still files a finding but
  `sonar-roundtrip` remains the authoritative consumer of the Sonar
  quality gate.

- **Build profile membership** (row b vs row c) is determined by the
  architecture-resolved build-command canonical names (`verify`,
  `quality-gate`, `module-tests`, `coverage`). A failing check whose
  `workflow_name` contains one of those tokens produces a
  `ci-verify-build` finding; non-matching names produce
  `ci-verify-policy` findings. The match rule is single-sourced in the
  executor; projects whose CI labels diverge from the
  architecture-resolved names override the match rule via the
  `architecture` skill's configuration, not here.

- **Distinct producer strings** are the dispatch keys for the triage
  workflow. Each producer is registered with `ext-triage-{domain}`
  separately so domain plugins can attach producer-specific triage
  hints (e.g., `ext-triage-plugin` can short-circuit `ci_no_checks`
  to "accept" for plans that opt out of CI). Adding new producers
  does NOT require new finding-types in `tools-file-ops/constants.py`;
  all of them resolve to `triage`.

- **Finding subtype** is carried in the finding's `message` body as a
  prefix tag `[ci_build_failure]`, `[ci_policy_failure]`, etc., so
  retrospectives and `manage-findings list --type triage` can grep
  for specific subtypes without a schema change.

- **One finding per failing check.** A PR with three build-failure
  checks plus one stale check produces four findings (three under
  `ci-verify-build` + one under `ci-verify-stale`), each carrying the
  appropriate producer + subtype. The executor returns the distinct
  producer strings; the dispatcher runs ONE `verification-feedback`
  invocation per producer string, NOT per finding.

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
against the new HEAD's CI run. This is enforced by `ci-verify`'s
membership in `HEAD_DEPENDENT_STEPS` in [`../SKILL.md`](../SKILL.md).
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
