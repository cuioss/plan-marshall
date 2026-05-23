# ci-verify Standards

Standards counterpart to [`../workflow/ci-verify.md`](../workflow/ci-verify.md).
Codifies the multi-failure-mode taxonomy, the build-profile match rule,
the precondition mode contract, and the eager-fetch persistence
guarantee. Lesson `2026-05-18-16-001` deliverable 6 is the authoritative
source.

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

```
pre-submission-self-review
commit-push
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
timeout}` and `failing_checks` through to the step body WITHOUT
short-circuiting the step to `failed`. Existing consumers keep the
default `strict` mode and observe no behaviour change.

The flag flows from the dispatcher's resolver invocation:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:ci_complete_precondition \
  resolve --plan-id {plan_id} --worktree-path {worktree_path} \
  --pr-number {pr_number} --mode consume-failures
```

## Failure-mode taxonomy

| Row | Failure mode | Detection source | Producer string | Subtype tag | Typical fix path |
|-----|--------------|------------------|------------------|-------------|------------------|
| a | Sonar quality-gate failure | Sonar provider (NOT a GitHub check) | n/a (out of ci-verify scope) | n/a | `sonar-roundtrip` triage; ci-verify MUST NOT double-report |
| b | Build / test / lint / coverage failure | CI check whose `workflow_name` matches a build profile | `ci-verify-build` | `ci_build_failure` | Open fix-task on failing module; loop_back |
| c | Policy-workflow failure (license/cla, dep-review, codeql) | CI check whose `workflow_name` does NOT match a build profile | `ci-verify-policy` | `ci_policy_failure` | Depends on policy: accept / suppress / fix |
| d | Explicit `conclusion=failure` | per-check conclusion | (b) or (c) above | (b) or (c) above | per-row |
| e | Timeout (`conclusion=timed_out` OR wait-deadline) | per-check conclusion / `wait_outcome=deadline_exceeded` | `ci-verify-timeout` | `ci_timeout` | retry / accept (flaky infra) |
| f | Cancelled (`conclusion=cancelled`) | per-check conclusion | `ci-verify-cancelled` | `ci_cancelled` | accept (manual cancellation) / retry |
| g | Action required | per-check conclusion | `ci-verify-action-required` | `ci_action_required` | operator approval; accept after approval |
| h | Stale (`conclusion=stale`) | per-check conclusion | `ci-verify-stale` | `ci_stale` | re-run CI (HEAD advanced past check's commit) |
| i | No checks reported (`final_status=none`) | zero checks across PR | `ci-verify-missing` | `ci_no_checks` | confirm CI is configured; accept if intentional |
| j | CI never ran vs CI ran red | distinguished by (i) vs (b..h) | n/a — handled by row choice | n/a | covered by per-row producer split |

### Notes on the taxonomy

- **Row (a) is explicitly excluded** from ci-verify's scope. Sonar's
  quality-gate is fetched by `sonar-roundtrip` from the Sonar API, not
  from the GitHub-checks surface. If a project has wired Sonar as a
  GitHub status check, that check appears under row (c)
  `ci_policy_failure` — ci-verify still files a finding but
  `sonar-roundtrip` remains the authoritative consumer of the Sonar
  quality gate.

- **Build profile membership** (row b vs row c) is determined by the
  `architecture` skill's per-module build profile. The workflow body
  calls `architecture resolve --command verify` and checks whether the
  failing check's `workflow_name` matches any of the architecture-
  resolved build command names (`verify`, `quality-gate`,
  `module-tests`, `coverage`). Non-matching workflow names land in row
  (c). Projects whose CI labels diverge from the architecture-resolved
  names can override the match rule via configuration (the override
  hook is documented in the `architecture` skill's standards, not
  here, so the match rule stays single-sourced).

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
  appropriate producer + subtype. The triage dispatch is batched: ONE
  `verification-feedback` invocation per producer string, NOT per
  finding.

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
non-empty `log_path`. The workflow body captures `checks[]` from the
step-1 `ci status` envelope into a `.plan/temp/` JSON file and passes
that path to `manage-ci-artifacts persist --jobs-file …`; the manifest's
`jobs_source` field labels the outcome (`enumerated` when the array
was supplied, `empty` otherwise) so a zero-jobs manifest on a green-CI
run is structurally distinguishable from a genuine no-CI verdict. A
`jobs_source: empty` value on a green-CI run is a defect signal — not
the route by which `ci_no_checks` findings get filed (those flow from
`final_status=none` in step 1's envelope).

The persistence layer is implemented by the `manage-ci-artifacts`
skill ([`../../manage-ci-artifacts/SKILL.md`](../../manage-ci-artifacts/SKILL.md)).
Findings reference per-job log paths via `--source-path` so the
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
against the new HEAD's CI run. This is enforced by adding `ci-verify`
to `HEAD_DEPENDENT_STEPS` in [`../SKILL.md`](../SKILL.md). On every
re-fire, a new `run_id` directory is created (idempotence applies
per `run_id`, not per plan), so the audit trail accumulates.

## Cross-references

- [`automated-review.md`](automated-review.md) — sibling consumer
  that uses the precondition in `strict` mode; ci-verify's
  `consume-failures` mode is the only divergence.
- [`sonar-roundtrip.md`](sonar-roundtrip.md) — owns row (a). If a
  project wires Sonar as a GitHub check, the row-(c) finding here
  and the row-(a) finding there both reference the same upstream
  defect; the operator triages the row-(c) finding as "duplicate of
  sonar-roundtrip" or accepts via the policy producer.
- Lesson `2026-05-18-16-001` deliverable 6 — original design notes.
