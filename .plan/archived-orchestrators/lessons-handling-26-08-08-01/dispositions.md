# Per-Lesson Dispositions — lessons-handling-26-08-08-01

Every one of the 203 active lessons scanned on 2026-08-08 carries exactly one disposition
here. No lesson left the scan without one. The corpus was snapshotted verbatim into
`archive/` (208 files) before any analysis, so nothing depends on this record surviving.

## Claim labelling

Per the verify-first contract (`orchestration-model.md` § Verify-First Contract), every
claim below is labelled:

- **OBSERVED** — read directly from the lesson corpus listing or a sibling epic's `status.json`.
- **HYPOTHESIS** — inferred, carrying a named confirm/refute artifact, marked verify-at-outline.

**OBSERVED**: every lesson id, component, category and title; every sibling plan id, slug and
status; the cluster membership assignments (derived from those two OBSERVED sets).

**HYPOTHESIS (verify-at-outline)**: that each cluster's premise still holds against current
main. The operator scoped this run to cluster-level validity; per-lesson ground-truth
verification is owed by the receiving plan at its outline. Each cluster below names the
confirm/refute artifact — a file plus the symbol within it — that settles its premise.

## Routing rule applied

| Destination | Takes |
|-------------|-------|
| `review-apparatus` | PR-review / review-bot reliability. Tested FIRST, wins outright. |
| `code-intelligence-substrate` | Token/context economy, code-navigation substrate, scope derivation. |
| `truthful-signals` | Everything else — confident-signal-hides-a-caveat, false green, vacuous guard. |

---

## C01 — derive-verification emits a build_class phase-5 cannot route (8 lessons)

**Destination**: `truthful-signals` · **NEW spec** — no existing plan owns it.
**Confirm/refute artifact**: `manage-architecture` `derive-verification` command handler, and
`manage-execution-manifest`'s `unresolvable_step` branch in the composer.

⭐ **The flagship dedup win of this run.** Five lessons filed on three different days by three
different components describe ONE defect: `derive-verification` emits `compile` /
`test-compile` build_class commands that manifest compose cannot map to a phase-5 canonical.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-28-15-001 | clustered-into C01 (primary) |
| 2026-07-28-15-002 | clustered-into C01 — duplicate of -15-001 |
| 2026-07-28-19-001 | clustered-into C01 — duplicate of -15-001 |
| 2026-07-28-20-001 | clustered-into C01 — duplicate of -15-001 |
| 2026-07-28-21-001 | clustered-into C01 — duplicate of -15-001 |
| 2026-07-27-15-001 | clustered-into C01 — the missing write-back flag that blocks the stamp |
| 2026-07-27-23-003 | clustered-into C01 — compose-time force-out via `lane=off` not removed |
| 2026-08-03-14-005 | clustered-into C01 — sonar-roundtrip pruned while compose logged unresolvable |

## C02 — a build reports its own outcome falsely (10 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-027`** (build-ledger-is-the-build-time-oracle).
**Confirm/refute artifact**: `build-server-client` terminal-status classification, and
`build-pyproject`'s `parse` verb where `failed=0` is derived.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-22-12-003 | clustered-into C02 (primary) — routed build outer success over a failed child |
| 2026-07-27-00-001 | clustered-into C02 — `--timeout` discarded, duration zeroed |
| 2026-07-27-00-002 | clustered-into C02 — `kind=build` exit_code 0 for timed-out builds |
| 2026-08-01-13-001 | clustered-into C02 — false red over a completed suite |
| 2026-08-02-15-006 | clustered-into C02 — two timeout authorities, duration 0 |
| 2026-08-08-12-001 | clustered-into C02 — pytest COLLECTION ERROR reads green |
| 2026-07-16-16-003 | clustered-into C02 — adaptively-lowered timeout silently kills |
| 2026-06-16-23-001 | clustered-into C02 — build-error classifier mis-categorizes |
| 2026-07-07-10-001 | clustered-into C02 — extractor must anchor to the summary line |
| 2026-07-22-20-005 | clustered-into C02 — fallout measured on an unverified interpreter |

## C03 — a freshness gate admits a tree whose tests never ran (4 lessons)

**Destination**: `code-intelligence-substrate` · **fold onto `PLAN-CIS-017`**
(freshness-gate-cannot-distinguish-test-authored-evidence) — an exact-surface match.
**Confirm/refute artifact**: `manage-change-ledger` `pre-commit-verify-freshness` handler.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-26-20-002 | clustered-into C03 (primary) — test-suite-written ledger row satisfies the gate |
| 2026-07-27-08-002 | clustered-into C03 — fresh off a quality-gate-only run |
| 2026-07-29-18-004 | clustered-into C03 — a `--help` invocation accepted as evidence |
| 2026-07-28-19-007 | clustered-into C03 — arch-constraint: markdown under `marketplace/bundles/**` IS a build input |

## C04 — vacuous guards and degenerate zeros (15 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-042`** (a-rule-that-is-green-because-it-examined-nothing).
⚠ TRUTH-042 is **RUNNING** — this arrives as a mid-flight `finding`, not a spec edit.
**Confirm/refute artifact**: each named guard's own predicate; the class sweep is TRUTH-042's D-set.

Memory records this as a recurring archetype (n≥6) *repeatedly reintroduced by a fix for it*.
Fifteen instances is the largest cluster-by-severity in the corpus.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-28-20-002 | clustered-into C04 (primary) — a guard whose predicate excludes its own motivating case |
| 2026-07-23-01-002 | clustered-into C04 — `if key is None: continue` is vacuous for the misconfigured items |
| 2026-08-03-14-004 | clustered-into C04 — RE_ENTRY_COVERAGE vacuous at exactly its trigger value |
| 2026-07-26-22-001 | clustered-into C04 — Row 2 vacuous, recipe-routed plans report false drift |
| 2026-07-26-19-001 | clustered-into C04 — `False == 0` drops the payload it exists to detect |
| 2026-07-29-18-005 | clustered-into C04 — discriminator cannot separate unknown from empty |
| 2026-08-02-15-001 | clustered-into C04 — a seeded empty container is not a declaration |
| 2026-08-03-06-001 | clustered-into C04 — structurally unreachable failure arm |
| 2026-07-28-19-006 | clustered-into C04 — non-degeneracy anchor omits the member the fix added |
| 2026-07-26-22-002 | clustered-into C04 — scans for a marker never emitted there; zero is unmeasured |
| 2026-06-24-18-003 | clustered-into C04 — missing input coerced into a signal value |
| 2026-07-29-17-001 | clustered-into C04 — a closure invariant checks completeness, never correctness |
| 2026-06-24-14-002 | clustered-into C04 — max attainable score below the gating threshold |
| 2026-07-21-11-003 | clustered-into C04 — no zero-scoped-modules branch, scoped run with a null target |
| 2026-07-16-14-001 | clustered-into C04 — classifier fail-open on multiple independent axes |

## C05 — review-bot participation and reliability (9 lessons)

**Destination**: `review-apparatus` (PR/review test fires first and wins outright).
**Folds**: `PLAN-PR-005` / `PLAN-PR-006` / `PLAN-PR-007` / `PLAN-PR-013`.
**Confirm/refute artifact**: `automatic-review`'s participation classifier and `ci pr comments`.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-28-19-002 | clustered-into C05 → `PLAN-PR-005` — participation from CONTENT; a review can arrive after the merge |
| 2026-07-28-23-001 | clustered-into C05 → `PLAN-PR-007` — a stated rate-limit ETA is a lower bound |
| 2026-07-28-23-002 | clustered-into C05 → `PLAN-PR-007` — a size-keyed refusal is unrecoverable by waiting |
| 2026-08-03-14-002 | clustered-into C05 → `PLAN-PR-013` — the re-review that caught 14 findings fired incidentally |
| 2026-06-21-21-001 | clustered-into C05 → `PLAN-PR-013` — freshness matcher naive-datetime |
| 2026-07-29-19-002 | clustered-into C05 → `PLAN-PR-007` — a negative read of async remote state is provisional |
| 2026-07-17-09-001 | clustered-into C05 — simplify can revert a fix automatic-review committed in the SAME run; no reconciliation contract exists. **NEW spec candidate** |
| 2026-08-03-14-007 | clustered-into C05 — triage leaf writes tests it structurally cannot run |
| 2026-07-16-17-004 | clustered-into C05 — a fix recipe can specify a vacuous test; prove discrimination by mutation |

## C06 — the in-house gates were silent where they claim coverage (13 lessons)

**Destination**: `review-apparatus` · **fold onto `PLAN-PR-011`**
(review-bots-catch-what-in-house-gates-cannot) — the plan is literally named for this cluster.
**Confirm/refute artifact**: each named gate's own scan scope.

Every member ends "…only the PR bot caught it". Thirteen instances is the empirical corpus
`PLAN-PR-011` needs and did not have.

| Lesson | Disposition |
|--------|-------------|
| 2026-06-22-11-001 | clustered-into C06 (primary) — doc prose mis-described a completion condition |
| 2026-06-22-12-001 | clustered-into C06 — placeholder worst-case expansion unchecked |
| 2026-06-22-13-001 | clustered-into C06 — local ruff select omits the RUF family |
| 2026-06-25-02-001 | clustered-into C06 — non-portable tokens; no in-house gate enforces it |
| 2026-06-25-10-001 | clustered-into C06 — prose paraphrases a machine-readable universe |
| 2026-06-30-15-001 | clustered-into C06 — unsorted traversal is non-deterministic across runs |
| 2026-07-08-09-001 | clustered-into C06 — copyfile writes through a stale symlink |
| 2026-07-12-18-001 | clustered-into C06 — absent vs present-but-invalid indistinguishable |
| 2026-07-14-16-002 | clustered-into C06 — only the recursion branch was ever exercised |
| 2026-07-21-12-001 | clustered-into C06 — migration seam shipped legacy-key-blind |
| 2026-07-22-10-001 | clustered-into C06 — a loose placeholder becomes a type mismatch |
| 2026-06-24-14-003 | clustered-into C06 — missing tie-break + uncleared gate-trigger state |
| 2026-07-14-17-001 | clustered-into C06 — narrow-key presence check hides a wrongly-shaped record |
| 2026-07-21-01-001 | clustered-into C06 — report claims unverified and internally inconsistent |

## C07 — a dispatched leaf has no search primitive (4 lessons)

**Destination**: `code-intelligence-substrate` · **fold onto `PLAN-CIS-002`** (lsp-shaped-query-api),
sequenced after the shipped `PLAN-CIS-001` content-search seam.
**Confirm/refute artifact**: `execution-context` agent tool declarations vs the harness runtime grant.

⭐ This cluster is first-party corroboration for CIS's own thesis, and `review-apparatus`
already delegated a related item here (`review-apparatus-005`).

| Lesson | Disposition |
|--------|-------------|
| 2026-07-29-08-001 | clustered-into C07 (primary) — arch-constraint: Grep/Glob revoked at runtime despite being declared |
| 2026-08-03-09-001 | clustered-into C07 — Grep/Glob deniable, Bash grep/find hook-blocked ⇒ no fallback |
| 2026-07-22-13-001 | clustered-into C07 — denial is non-deterministic within one session |
| 2026-07-22-20-003 | clustered-into C07 — substitution re-checked against the EXECUTING envelope's grant |

## C08 — cost and token measurement instruments (6 lessons)

**Destination**: `code-intelligence-substrate` · **folds**: `PLAN-CIS-022` (token-ledgers-disagree),
`PLAN-CIS-014` (aggregate-cost-invisible), `PLAN-CIS-013` (chat-signal-provenance).
**Confirm/refute artifact**: `manage-metrics` `cmd_enrich`, and the retrospective's
`extract-chat-signal` reducer.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-26-22-003 | clustered-into C08 (primary) → CIS-014 — platform_runtime + hook = 59% of all script wall-clock |
| 2026-07-21-15-001 | clustered-into C08 → CIS-022 — `seconds_per_task` grades operator idle time as agent cost |
| 2026-07-26-23-001 | clustered-into C08 → CIS-013 — self-reports a healthy reduction over a misclassified corpus |
| 2026-07-26-22-004 | clustered-into C08 → CIS-022 — 310 of 1519 rows permanently pending, inflating signal 70% |
| 2026-07-21-11-001 | clustered-into C08 — duration estimates ~5x stale, untrustworthy as a routing input |
| 2026-08-03-16-001 | clustered-into C08 → CIS-022 — `cmd_enrich` hardcodes the four usage fields |

## C09 — the retrospective instrument has dead sections (3 lessons)

**Destination**: `code-intelligence-substrate` · **fold onto `PLAN-CIS-020`**
(retrospective-report-sections-structurally-dead).
**Confirm/refute artifact**: `plan-retrospective` compile-report producer set.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-27-08-005 | clustered-into C09 (primary) — Executive Summary has no producer, always empty |
| 2026-08-03-14-003 | clustered-into C09 — retrospective capture overwrites the execution session_id |
| 2026-07-29-09-002 | clustered-into C09 — record the signals that refused to lie; the counterexample set is evidence |

## C10 — finalize step ordering and instrumentation (10 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-050`**
(the-operator-report-is-an-evidence-surface-the-inbox-cannot-see), which already owns the
finalize step-order space and carries an operator no-split directive.
**Confirm/refute artifact**: `phase-6-finalize` step order registry.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-28-19-005 | clustered-into C10 (primary) — retrospective at step 17, after its input is destroyed |
| 2026-08-03-14-001 | clustered-into C10 — loop-back ceiling detected after it is crossed |
| 2026-08-03-14-006 | clustered-into C10 — operator resume after a halt emits no step instrumentation |
| 2026-07-29-18-003 | clustered-into C10 — a step before the merge window cannot capture what it reveals |
| 2026-06-28-13-001 | clustered-into C10 — a bypass branch must be documented before the dispatch it bypasses |
| 2026-07-17-09-002 | clustered-into C10 — scoped plugin-doctor misses what CI's whole-tree run catches |
| 2026-07-21-21-002 | clustered-into C10 — root-module footprint falls through the sweep un-gated |
| 2026-06-21-01-001 | clustered-into C10 — self-modifying plan strands its own composed manifest |
| 2026-06-25-08-003 | clustered-into C10 — simplify prompt omits the changeset-scope boundary |
| 2026-07-16-17-009 | clustered-into C10 — run a Sonar pass on the diff before push on large plans |

## C11 — plugin cache and executor regeneration staleness (6 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-059`**
(sync-plugin-cache-updates-the-cache-and-executor-and-never-the-registry).
**Confirm/refute artifact**: `sync-plugin-cache` engine's registry write path (absent).

⭐⭐ Memory records this as the **#896 pin trap**, 10–11 incidents, ~daily, and in 11/11 the gap
contained the launching plan's own target surface. Six corpus lessons corroborate it
independently.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-27-08-004 | clustered-into C11 (primary) — deployed cache serves pre-fix frontmatter; the gate that would catch it is defeated too |
| 2026-06-23-09-001 | clustered-into C11 — finalize dispatch loads renamed skills from a stale cache |
| 2026-07-10-23-002 | clustered-into C11 — rebase changes the script set but does not regenerate the executor |
| 2026-07-14-17-002 | clustered-into C11 — executor-regen bootstrap: a plan changing the generator ships a broken executor |
| 2026-07-14-16-001 | clustered-into C11 — template change must sweep test-local render helpers |
| 2026-06-20-16-002 | clustered-into C11 — finalize worktree mutation staleness-invalidates the freshness gate |

## C12 — outline scope derivation is incomplete (16 lessons)

**Destination**: `code-intelligence-substrate` · **fold onto `PLAN-CIS-015`**
(outline-plan-scope-derivation-integrity).
**Confirm/refute artifact**: `phase-3-outline` discovery-sweep pass and `manage-solution-outline`
`get-module-context`.

Second-largest cluster. Memory records "plans under-scope the doc contract surface" as a
standing archetype; sixteen instances is its corpus.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-21-17-004 | clustered-into C12 (primary) — outline verifies paths exist, never that the set is complete |
| 2026-07-22-10-002 | clustered-into C12 — files entering scope after the sweep bypass assessment entirely |
| 2026-06-29-16-001 | clustered-into C12 — under-scopes the mirror contract surface |
| 2026-07-21-16-002 | clustered-into C12 — missing dependency edge between deliverables on one symbol |
| 2026-06-21-02-001 | clustered-into C12 — mandated an edit to a symbol already removed |
| 2026-06-20-12-001 | clustered-into C12 — task descriptions invent CLI shapes not in the outline |
| 2026-07-25-19-001 | clustered-into C12 — corroborating outputs must share ONE input population |
| 2026-07-27-08-003 | clustered-into C12 — a criterion resting on pre-existing coverage must locate it |
| 2026-07-29-19-001 | clustered-into C12 — a staged spec premise expires; re-measure at outline |
| 2026-08-03-06-004 | clustered-into C12 — a plan the lifecycle consumes at a passed phase is not self-exercising |
| 2026-07-22-16-001 | clustered-into C12 — a read-only reference file flips the footprint bucket |
| 2026-07-22-20-004 | clustered-into C12 — bucket declared from narrative intent, not derived from affected files |
| 2026-07-29-18-001 | clustered-into C12 — a lane variant collapsing a phase envelope must re-home the folded writes |
| 2026-07-29-18-009 | clustered-into C12 — a plan fixing accumulate-vs-replace can reproduce it in its own run |
| 2026-07-28-19-004 | clustered-into C12 — router pre-override input overwritten by its output |
| 2026-06-29-02-001 | clustered-into C12 — get-module-context required a worktree not yet materialized |
| 2026-07-26-16-001 | clustered-into C12 — `not_yet_materialized` misreported as `worktree_resolution_failed` |

## C13 — a premise verified against the wrong artifact (6 lessons)

**Destination**: `truthful-signals` · **NEW spec** for the two live members; four are
`already-covered`.
**Confirm/refute artifact**: `phase-2-refine` verification step, and the verify-first contract
clause in `orchestration-model.md`.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-20-16-001 | clustered-into C13 (primary) — refine verified against a standards doc, not implementing source |
| 2026-07-22-01-001 | clustered-into C13 — a value from a self-rewriting learned store is not ground truth |
| 2026-07-29-18-007 | clustered-into C13 — a blind-spot-class request cannot be a scoping input |
| 2026-06-21-11-001 | **already-covered** — the expected-false-positive is documented in the refine Q-Gate contract |
| 2026-06-28-17-001 | **already-covered** — light-lane assessment-coverage false positive is documented |
| 2026-07-16-12-001 | **already-covered** — keyword_drift false positive is documented |

## C14 — phase-4 change_type and plan scoping (5 lessons)

**Destination**: `truthful-signals` · **NEW spec**.
**Confirm/refute artifact**: `phase-4-plan`'s `compose change_type` derivation.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-16-20-001 | clustered-into C14 (primary) — change_type from the first deliverable drops finalize steps |
| 2026-07-29-18-002 | clustered-into C14 — **duplicate of -20-001**, a discovery-first plan under-reports its own risk |
| 2026-06-28-18-001 | clustered-into C14 — analysis plans should use an existing architecture module |
| 2026-07-18-13-002 | clustered-into C14 — re-dispatch must touch only plan artifacts, never source |
| 2026-06-21-19-001 | clustered-into C14 — auto-fix loop burns an iteration on informational findings |

## C15 — agent working discipline (13 lessons)

**Destination**: mostly **already-covered** — these rules are live in `CLAUDE.md`, the
persona skills, and project memory. Residue folds onto `PLAN-TRUTH-016`
(skills-carry-incident-history-as-normative-prose).
**Confirm/refute artifact**: `CLAUDE.md` § Workflow Discipline (Hard Rules), and
`persona-plan-marshall-agent`.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-21-16-003 | **already-covered** — CLAUDE.md hard rule: no shell constructs; hook enforces it |
| 2026-07-21-16-004 | **already-covered** — memory + hard rule: never blind-retry a stalled dispatch |
| 2026-07-15-18-001 | **already-covered** — CLAUDE.md hard rule: workflow steps, no improvisation |
| 2026-07-17-17-001 | **already-covered** — worktree cwd pinning is a documented dispatch contract |
| 2026-07-21-12-002 | **already-covered** — quoting rule is in the script-architecture standard |
| 2026-08-03-06-002 | clustered-into C15 → TRUTH-016 — a reviewer's named site list is a detector sample |
| 2026-08-02-07-001 | clustered-into C15 → TRUTH-016 — a universally-quantified refutation must enumerate the population |
| 2026-08-03-19-001 | clustered-into C15 → TRUTH-016 — read the mechanism; timing/comment/ordering is a proxy |
| 2026-07-28-20-003 | clustered-into C15 → TRUTH-016 — relocation is not repair |
| 2026-07-29-18-008 | clustered-into C15 → TRUTH-016 — a verbatim argparse rejection across a retry is never flaky |
| 2026-07-28-11-001 | clustered-into C15 — cwd pin reverts across background-job boundaries, no escape hatch |
| 2026-07-26-22-005 | clustered-into C15 — argument-naming enforcement is opt-in; absent scripts escape entirely |
| 2026-07-15-22-001 | clustered-into C15 — best-effort cleanup in `finally` must swallow its own exception |

## C16 — test-authoring discipline (13 lessons)

**Destination**: `truthful-signals` · **NEW spec**.
⛔ The `test-suite-quality` epic is **CLOSED and ARCHIVED at 10/10 — do not reopen a third
time**; its residue was already handed to `truthful-signals`. This cluster goes there, not back.
**Confirm/refute artifact**: `persona-module-tester` standards, and `test/_shared/_dispatch_roster.py`
as the population-derived detector reference.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-09-14-001 | clustered-into C16 (primary) — fixtures must mirror post-normalization production shape |
| 2026-07-17-08-002 | clustered-into C16 — fix the fixture, not the guard |
| 2026-07-28-08-002 | clustered-into C16 — a doc-claimed concurrency property needs an interleaving test |
| 2026-07-28-22-001 | clustered-into C16 — a path predicate must match the repo-RELATIVE path |
| 2026-08-02-15-003 | clustered-into C16 — assert the surface the caller queries, not the feeding stage |
| 2026-07-22-11-001 | clustered-into C16 — an autouse isolation fixture cannot see monkeypatch restores |
| 2026-07-23-10-001 | clustered-into C16 — `--basetemp` inside the repo tree breaks isolation tests |
| 2026-07-21-15-002 | clustered-into C16 — fail-closed guard promotion owed (deferred post-merge) |
| 2026-07-16-17-007 | clustered-into C16 — wired-flow assertions must cover every new security binding |
| 2026-07-12-15-001 | clustered-into C16 — docs-only call-shape change breaks tests plugin-doctor never runs |
| 2026-06-24-09-001 | clustered-into C16 — same-basename test files collide under pytest prepend import |
| 2026-07-21-17-001 | clustered-into C16 — shared helper needs BOTH sys.path and mypy_path registration |
| 2026-07-12-18-002 | clustered-into C16 — use getattr for a new attribute; sweep old required-flag tests |

## C17 — security hardening (6 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-011`** (provider-logging-path-containment).
⚠ TRUTH-011 is **RUNNING** — arrives as a mid-flight `finding`.
**Confirm/refute artifact**: `manage-logging` `plan_logging.log_entry` plan_id validation.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-20-00-001 | clustered-into C17 (primary) — `log_entry` does not validate client-supplied plan_id |
| 2026-07-20-20-002 | clustered-into C17 — **exact duplicate of -00-001**, filed as a hardening follow-up |
| 2026-07-17-21-001 | clustered-into C17 — lazy migration must contain every failure its side effects raise |
| 2026-07-17-21-002 | clustered-into C17 — module-level `Path.home()` fails import with no HOME |
| 2026-07-18-17-001 | clustered-into C17 — containment-verify EVERY client-settable path field |
| 2026-06-30-16-001 | clustered-into C17 — case-sensitive denylist bypassable by a case variant (CWE-178) |

## C18 — self-review completeness (9 lessons)

**Destination**: `review-apparatus` · **fold onto `PLAN-PR-018`**
(self-review-rescans-the-whole-surface-every-round).
**Confirm/refute artifact**: `ext-self-review-plan-marshall` candidate surfacers.

⭐ `PLAN-PR-018` already absorbed the scope-of-sweep-vs-scope-of-claim trap; these nine are
its empirical corpus.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-27-08-001 | clustered-into C18 (primary) — enumerate every relational case a guard's condition implies |
| 2026-07-28-08-001 | clustered-into C18 — a fix is the highest-risk moment; mandate an adversarial re-read of its own diff |
| 2026-07-29-18-006 | clustered-into C18 — audit a classifier's symmetric peers for the defect's SHAPE, not its text |
| 2026-08-02-15-004 | clustered-into C18 — apply the rule you are enforcing to your own artifacts |
| 2026-08-02-15-005 | clustered-into C18 — a test name and docstring are a coverage claim |
| 2026-07-18-05-002 | clustered-into C18 — sweep mirrored prose in one pass, not one-at-a-time |
| 2026-06-30-20-001 | clustered-into C18 — a mirroring helper must mirror the full sibling-invariant surface |
| 2026-07-18-14-001 | clustered-into C18 — normative worked-examples are a semantic surface self-review misses |
| 2026-08-03-17-001 | clustered-into C18 — an aggregation states its predicate and leaves its set implicit |

## C19 — doc-contract divergence (20 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-012`**
(canonical-block-diverges-from-argparse-choices).
**Confirm/refute artifact**: `plugin-doctor`'s `_analyze_manage_invocation.py` canonical-block reader.

Largest cluster in the corpus. Memory records doc-contract-divergence as a standing archetype.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-21-17-002 | clustered-into C19 (primary) — verify a flag against the owning skill's contract doc, not argparse |
| 2026-07-23-02-001 | clustered-into C19 — a promised telemetry field must be in the return dict |
| 2026-07-28-23-003 | clustered-into C19 — an early-return omitting doc-declared fields is a divergence |
| 2026-07-28-19-003 | clustered-into C19 — classified dispatched in one doc, inline in two; the closure test never cross-checks |
| 2026-07-27-23-002 | clustered-into C19 — a retracted `[DISPATCH]` line leaves a known-false record no detector can filter |
| 2026-08-03-06-003 | clustered-into C19 — documenting that a property is unenforced is not a fix |
| 2026-07-30-15-001 | clustered-into C19 — a centralizing refactor can silently widen a lazy contract into an eager one |
| 2026-06-24-23-001 | clustered-into C19 — literal-count-drift counts the wrong population |
| 2026-07-22-16-004 | clustered-into C19 — a hand-off command string must be validated against Action Resolution |
| 2026-07-19-12-001 | clustered-into C19 — an archived read fallback needs a guard on every sibling mutation verb |
| 2026-07-29-17-002 | clustered-into C19 — a plan-ID renumber in one epic orphans citations in another |
| 2026-08-03-18-001 | clustered-into C19 — a spec's own write-surface assertion is not disjointness evidence |
| 2026-07-29-09-001 | clustered-into C19 — a spec's measured-value table and hard constraints are leads, not evidence |
| 2026-06-25-10-001 → see C06 | (cross-listed; primary home is C06) |
| 2026-06-28-12-001 | clustered-into C19 — cross-refs must use the target doc's taxonomy version |
| 2026-06-28-17-002 | clustered-into C19 — a renumber sweep must re-home by semantic content, not number substitution |
| 2026-07-13-17-001 | clustered-into C19 — analyzers over-approximate when their model omits a runtime dispatch mechanism |
| 2026-07-20-01-001 | clustered-into C19 — anchor to symbols, never to line numbers |
| 2026-08-02-15-002 | clustered-into C19 — a precedence branch discarding a producer's output must say so on that report |
| 2026-07-29-19-001 → see C12 | (cross-listed; primary home is C12) |

## C20 — git, worktree and footprint integrity (6 lessons)

**Destination**: `truthful-signals` · **folds**: `PLAN-TRUTH-006` (baseline-reconcile-persists-merge-commit),
`PLAN-TRUTH-054` (baseline-reconcile-stale-anchor).
**Confirm/refute artifact**: `_cmd_baseline_reconcile.py`, and `workflow-integration-git`'s porcelain parser.

⚠ TRUTH-006 and TRUTH-054 share `_cmd_baseline_reconcile.py` and are already flagged for
serialization in the destination epic's anchor.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-22-21-001 | clustered-into C20 (primary) → TRUTH-006 — `--no-emit` leaves a merge commit instead of aborting |
| 2026-07-17-08-001 | clustered-into C20 — whole-output `.strip()` shifts the porcelain XY column |
| 2026-07-21-11-002 | clustered-into C20 — worktree branches off local main without asserting parity with origin |
| 2026-07-22-07-001 | clustered-into C20 — a deliberate lint deviation needs the sanctioned suppression marker |
| 2026-07-22-07-002 | clustered-into C20 — new emission on a routing seam double-emits on daemon re-entrancy |
| 2026-07-19-16-002 | clustered-into C20 — footprint classifier must fail safe and derive ownership from the whole footprint |

## C21 — execute-phase yield and artifact loss (8 lessons)

**Destination**: `truthful-signals` · **NEW spec**.
**Confirm/refute artifact**: `phase-5-execute`'s orchestrator-tier yield boundary and the
ARTIFACT emission loop.

| Lesson | Disposition |
|--------|-------------|
| 2026-08-03-17-002 | clustered-into C21 (primary) — the yield boundary lets a task's own new tests ship unexecuted |
| 2026-07-21-17-005 | clustered-into C21 — ARTIFACT emission stops after the first task of the first envelope |
| 2026-07-17-09-003 | clustered-into C21 — persist-before-gate loses data on gate failure |
| 2026-06-20-23-001 | clustered-into C21 — module-scoped verify misses project-local test dirs |
| 2026-07-16-17-008 | clustered-into C21 — behaviour-changing fixes must sweep all reactor consumers |
| 2026-06-21-00-003 | clustered-into C21 — module_testing profile must run quality-gate as well as tests |
| 2026-06-20-16-004 | clustered-into C21 — structurally-valid content omitting enumerated required points passed the gate |
| 2026-08-08-11-001 | clustered-into C21 — parametrized tests reported missing, blocking a compliant task |

## C22 — manage-* surface gaps (11 lessons)

**Destination**: `truthful-signals` · **fold onto `PLAN-TRUTH-009`** (surface-every-knob-in-marshal-json)
for the config-surface members; the rest are standalone-small.
**Confirm/refute artifact**: each named script's argparse surface vs its Canonical invocations block.

| Lesson | Disposition |
|--------|-------------|
| 2026-06-21-00-001 | clustered-into C22 (primary) — internal-id-keyed config read misses when the id diverges |
| 2026-07-07-13-001 | clustered-into C22 — `affected_files` not resynced after Q-Gate corrections |
| 2026-07-22-12-001 | clustered-into C22 — suppress repeated title-token log lines |
| 2026-07-22-14-001 | clustered-into C22 — deliverable-hash segmentation leaves the last end boundary undefined |
| 2026-07-22-21-002 | clustered-into C22 — hand-authored block-scalar TOON leaks spurious top-level keys |
| 2026-07-23-10-002 | clustered-into C22 — pointer detection gated on existence, not syntax |
| 2026-07-23-10-003 | clustered-into C22 — unguarded `read_text` raises instead of a structured refusal |
| 2026-07-26-22-006 | clustered-into C22 — `architecture enrich` writes fail the clean-main contract |
| 2026-07-16-08-001 | clustered-into C22 — a promoted analyzer gate catches synthetic test fixtures |
| 2026-06-24-14-001 | clustered-into C22 — rebase-onto-main is a viable first-class recovery |
| 2026-08-07-21-001 | clustered-into C22 — `files_exist` false-positives on external-repo plans. ⚠ **empty component/category** — corpus metadata defect in its own right |

## C23 — consumer-repo Java/CUI domain (2 lessons)

**Disposition**: `stale` for this repo's routing. Both describe `cui-http-testing` practice in a
consumer repo, name no plan-marshall surface, and no sibling epic owns a Java runtime concern.
They are **not deleted** — they remain in the corpus and in `archive/`, flagged for the owning
consumer repo rather than routed here.

| Lesson | Disposition |
|--------|-------------|
| 2026-07-16-17-015 | **stale** (for plan-marshall routing) — validate new-module ITs in CI-isolation |
| 2026-07-16-17-016 | **stale** (for plan-marshall routing) — re-anchor OP-emitted URLs in Keycloak client ITs |

---

## Disposition tally

| Disposition | Count |
|-------------|------:|
| `clustered-into` | 193 |
| `already-covered` | 8 |
| `standalone` | 0 |
| `stale` | 2 |
| **Total scanned** | **203** |

`standalone` is zero because every lesson found a cluster of two or more, or an existing
covering clause. That is the local dedup/aggregate obligation discharged: 203 lessons became
23 queue items, never 203.

## Duplicate pairs and near-duplicates found

| Duplicate set | Cluster |
|---------------|---------|
| 2026-07-28-15-001 · -15-002 · -19-001 · -20-001 · -21-001 (**5-way**) | C01 |
| 2026-07-20-00-001 · 2026-07-20-20-002 (identical title) | C17 |
| 2026-07-16-20-001 · 2026-07-29-18-002 (same defect, 13 days apart) | C14 |
