# Run report — 410-the-pipeline-talks-to-itself-and-learns-from-the-echo (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/pipeline-self-communication-e33yu6` (harness-assigned)    **PR:** [#1231](https://github.com/cuioss/plan-marshall/pull/1231)    **Outcome:** _in progress_    **GitHub access:** GitHub MCP server (cloud path)

## Skills loaded

- `plan-marshall:ref-code-quality` (via bundle path)
- `pm-plugin-development:plugin-script-architecture` (via bundle path)
- `plan-marshall:persona-implementer` (via bundle path)
- `pm-dev-python:python-core` (via bundle path)
- `pm-dev-python:pytest-testing` (via bundle path)

## Deliverables

### D0 — GATE: population before the filter (mutates nothing)

**Question:** How many promoted hints in the existing corpus were minted from self-authored (pipeline-authored) comments?

**The corpus IS reachable here** — a correction to the plan's framing. Most of `.plan/` is git-ignored and absent from this clone, but `.gitignore` (lines 46-48) carries explicit exceptions: `!.plan/marshal.json` and `!.plan/project-architecture/`. The architecture-hint store (`.plan/project-architecture/{module}/enriched.json`) is therefore **tracked and present**, so the scan is a genuine *look*, not a *could-not-look*.

**Population scanned:** all **11** tracked `enriched.json` files — `default/` plus **10** modules (`plan-marshall`, `pm-dev-frontend`, `pm-dev-frontend-cui`, `pm-dev-java`, `pm-dev-java-cui`, `pm-dev-oci`, `pm-dev-python`, `pm-documents`, `pm-plugin-development`, `pm-requirements`). Every `best_practices[]` / `insights[]` / `tips[]` entry read; the full set grep-swept for the comment-provenance signature (`pr-comment`, `taken_into_account`, `acknowledg*`, `unattributed`, `self-author*`, `triage-summary`, `review-trigger`, `review-bot`).

**The precise provenance count is NOT recoverable — and that is stated, not hidden.** By privacy invariant (c) in `disposition-to-hint-routing.md`, the store persists only the generalized hint *string*; it retains **no** author, finding-class, raw disposition, or finding→hint linkage. A definitive count of *"hints minted from a self-authored comment"* therefore cannot be computed from the store — for that precise question the substrate genuinely cannot answer. This is labelled as a *could-not-look for the provenance question*, not dressed up as a clean zero. (A full-text scan can only show whether a hint's TEXT matches the expected artifact — it cannot prove a given hint was *not* seeded by a pipeline-authored comment.)

**The strongest reachable signal — a full-text scan of every hint — found ZERO matches for the predicted artifact.** Every comment-related preference hint present attributes to an **external review bot** (`default/` insights lines 13,15,16,17; `plan-marshall/` best-practice line 5; `pm-plugin-development/` line 3 — all about CodeRabbit / pr-agent / Sourcery meta traffic) or to **genuine operator / q-gate / user-review dispositions** (`default/` insights lines 8-9). None encodes the plan's predicted false preference — *"unattributed / pipeline-self PR comments are routinely taken into account"*. The observed `(default, pr-comment, taken_into_account)` self-minted hint is **absent from the store's text**.

**Decision this gates:** **filter alone, no corpus repair.** The decision does NOT rest on a false-precise "0"; it rests on three independent grounds: (a) the text-scan proxy found no artifact-matching hint across the complete reachable population; (b) a corpus repair is *untargetable* — the store retains no provenance to identify which hint (if any) to remove; and (c) this lane forbids mutating `.plan/`, and the fix is self-limiting (once the filter lands, the corpus stops accreting self-minted hints). Any residual, unmeasurable historical pollution — of which the proxy gives no positive evidence — would have to be handled, if ever, by a separate machine-local operation with different tooling. Recorded as Residue.

### D1 — Discriminate authorship — **EMITTER arm chosen**

**Arm chosen: the emitter.** Rationale and the rejected arm:

- The plan's hypothesis *"self-authored comments are identifiable because they are allocated through a preparation verb"* is **REFUTED from source**: the comment-preparation verb (`tools-integration-ci/scripts/ci_base.py:prepare_body`) stamps **no** marker/attribution/signature, and there is **no self-login / actor registry** anywhere in the surface (`bot_kind_for_author` returns `None` for a human author *and* for the pipeline's own posting account alike). Direct self-identification at the emitter is therefore not available.
- **But the emitter arm remains viable fail-closed.** Instead of identifying "self" (impossible), the emitter admits only findings *positively attributed to a recognized external reviewer*: a `pr-comment` finding contributes to preference learning **only when it carries a recognized reviewer `bot_kind`**. The pipeline's own comments have `bot_kind` absent (they are not registered review bots), so they are excluded — completely and unilaterally, no matter how chatty the pipeline is. This achieves D1's goal ("a self-authored comment cannot reach the disposition corpus") without a cross-epic dependency.
- **Ingest arm REJECTED:** editing `workflow-integration-github/scripts/github_pr.py` crosses into another epic's surface (explicitly out of scope), and an offer-not-transfer hand-off can sit indefinitely. D0 shows **no** ingest-level corpus pollution requiring the ingest fix. So the plan's precondition for preferring ingest ("only if D0 shows the corpus is polluted at ingest for other consumers too") is not met.
- **Divergence recorded:** the fail-closed rule also excludes *unattributed human* pr-comments (they too lack a `bot_kind`), which is broader than the plan's literal "keep external humans" phrasing. This is the defensible fail-closed choice given no signal distinguishes an external human from the pipeline-self at the emitter; and the auditor's per-comment-unique title signatures mean human pr-comments essentially never recur into a durable preference anyway. The feature's real value (tool-finding dispositions: lint/sonar/bug) is untouched.

**Where implemented:** the testable Python aggregation — `audit-archived-plan-retrospectives/scripts/audit.py:cross_preference_pattern` (the only preference surface with unit-testable aggregation; the per-plan emitter is an LLM-orchestration doc) — plus the shared contract `disposition-to-hint-routing.md` that BOTH surfaces obey, plus the emitter doc and the check doc.

### D2 — Fallback-bucket promotability (SEPARATE from D1)

**Decision: a tuple whose module resolves to the `default` fallback bucket is NOT promotable.** The `default` bucket is the sink for *unattributed* findings (no `module`, no `component`) — and the aggregation cannot detect a genuinely cross-cutting "spans modules" pattern, so `default` only ever means *unattributed*, never a real cross-cutting judgement. Promoting it routes an unverified hint to the widest blast radius (`enrich insight --module default`). Implemented as a distinct post-aggregation gate in `cross_preference_pattern`, kept visible via a new `unattributed_excluded_count` — separate from D1's pre-aggregation authorship filter, and visibly separate in the diff (separate commit).

### D3 — Failing-pre-fix test + matched negative control

See Findings / Build gate. Tests target `cross_preference_pattern`; each suppression assertion seen RED pre-fix, with module-attributed / bot-attributed negative controls that MUST still promote.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` and `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_checks.py` — **Python changed, full path taken.**

`./pw verify` → **SUCCESS**: `19639 passed, 14 skipped in 379.29s`. All three sub-steps ran: quality-gate (ruff/mypy-production 399 files/SPDX/plugin-doctor marketplace-wide), test-compile (mypy-test 734 files), module-tests (whole-tree pytest). The marketplace `test_real_marketplace_quality_gate_has_zero_findings` passed, so the doc edits introduced no plugin-doctor findings. Per-commit `./pw quality-gate` ran clean before each of the two `*.py` commits.

## Findings

### Pre-PR verification sub-agent (Step 6) — `general-purpose`, read-only

The sub-agent read the plan, the full diff, report-01.md, `audit.py`, the test diff, the three edited docs, and swept the whole tree for stale statements. It confirmed all four deliverables implemented and test-covered, D1/D2 visibly separate, and no out-of-scope collateral (no `workflow-integration-github` / `tools-integration-ci` code touched). It independently re-confirmed D0 (store git-tracked via `.gitignore` exception; 0 self-minted hints). It surfaced 3 stale-claim gaps and 2 correctness observations:

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | `audit-archived-plan-retrospectives/SKILL.md` Step 4c | Still listed routing target `architecture enrich insight --module default` for cross-cutting rows — false after D2 | **FIXED** — updated Step 4c to state surfaced rows are authorship+attribution gated and route only to concrete modules |
| 2 | `finalize-step-preference-emitter.md` Step 4 | Still named `--module default` for cross-cutting patterns — self-contradictory with the just-edited Step 3 | **FIXED** — routing target reworded; Step 3 already drops default-bucket tuples |
| 3 | `audit.py` `_preference_module` docstring | Still said cross-cutting `default` bucket routes via `--module default` — false after D2 | **FIXED** — docstring rewritten to the counted-but-never-promoted semantics |
| 4 | `_preference_admissible` (D1) | Also suppresses genuine external-human reviewer pr-comments (no `bot_kind`), broader than the plan's literal "keep external humans" wording | **ACCEPTED (deliberate)** — there is no self-login signal on a finding to tell an external human from the pipeline-self (both `bot_kind`-absent, both author-bearing); admitting author-bearing comments would re-open the exact hole. Recorded as a fail-closed divergence in D1, and now pinned by an explicit characterization test `test_human_reviewer_pr_comment_without_bot_kind_is_excluded` so the behavior is a tested invariant, not silent |
| 5 | `default` sentinel overloading | `default` is both the unattributed-fallback sentinel AND the alias for the real project-root module, so D2 would also suppress a recurrence genuinely attributed to `module: "default"` | **ACCEPTED / RESIDUE** — a pre-existing system-wide convention (the fallback sentinel, the retired routing target, and the enriched store's cross-cutting bucket ALL use the literal `default`); the plan explicitly frames `default` as the unattributed sink, and D0 confirms the store's `default/` holds cross-cutting project-wide hints, so suppressing them is D2's intended behavior. Re-architecting the sentinel is a system-wide change beyond this plan; see Residue |

All three stale-claim fixes shipped in a follow-up commit; the D3 negative controls (bot-attributed pr-comment, module-attributed tool finding) genuinely still promote, so the filter does not suppress both halves.

**Re-verification (Step 6, second pass) — CLEAN.** The sub-agent re-checked the two fix commits: all three stale sites corrected with no residual `--module default` routing instruction and no new stale claim; the reworded D2 rationale comments accurate; the characterization test genuine (non-vacuous); all four docs (shared contract §§ (b)(d)(e), emitter doc Steps 1/3/4, auditor SKILL.md Step 4c, check doc) mutually consistent; and the D1/D2 executable logic byte-identical to the first-pass approval (the fix commits are doc/comment/test-only). It also confirmed the two remaining `--module default` hits (`phase-6-finalize/workflow/lessons-capture.md:142`, `standards/lessons-integration.md:94`) belong to the lessons-capture knowledge-routing subsystem — a deliberate LLM cross-cutting classification, correctly out of D2's scope.

### PR review (CodeRabbit) — 3 actionable inline comments, all accepted

CodeRabbit posted a full review; `cuioss-review-bot` reported no concerns; `sourcery-ai` was rate-limited. The three CodeRabbit findings — all valid, all improving the change:

| # | Source | Finding | Disposition |
|---|---|---|---|
| CR-1 | `audit.py:2204` (Minor, Data Integrity) | `_preference_admissible` accepted any non-empty `bot_kind` string; the auditor reads archived JSONL directly (no write-time `add_finding` validation), so a legacy / de-registered / hand-edited record with an unrecognized `bot_kind` (e.g. `sonarcloud`) would pass and seed a preference | **FIXED** — added `_recognized_bot_kinds()` (loads the live `automatic-review` registry via the established marketplace-import pattern) and now validate `bot_kind ∈ registry`; degrades to presence-only if the registry can't be loaded; added negative-control test `test_unrecognized_bot_kind_pr_comment_is_excluded`. Contract § (e) updated to say "recognized reviewer identity, validated against the registry" |
| CR-2 | `report-01.md:21` (Minor, Maintainability) | Published population count was wrong: `default/` + 10 modules = **11** files, not 12 | **FIXED** — corrected to 11 files / 10 modules. An off-by-one in a published population is precisely this epic's namesake defect, so the correction matters |
| CR-3 | `report-01.md:29` (Major, Data Integrity) | Reporting `0` as a provenance count overstates what a text scan can establish — the store retains no finding→hint linkage, so a text scan can only show no hint TEXT matches the artifact, not that no hint was self-minted | **FIXED** — reframed D0: the precise provenance count is explicitly labelled *not recoverable* (a could-not-look for that question); the text-scan proxy found 0 matches; and the "filter alone" decision now rests on three independent grounds (proxy + untargetable-repair + lane-forbids-`.plan`-mutation/self-limiting), not a false-precise zero |

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
