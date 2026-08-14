# Run report — 410-the-pipeline-talks-to-itself-and-learns-from-the-echo (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/pipeline-self-communication-e33yu6` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `plan-marshall:ref-code-quality` (via bundle path)
- `pm-plugin-development:plugin-script-architecture` (via bundle path)
- `plan-marshall:persona-implementer` (via bundle path)
- `pm-dev-python:python-core` (via bundle path)
- `pm-dev-python:pytest-testing` (via bundle path)

## Deliverables

### D0 — GATE: population before the filter (mutates nothing)

**Question:** How many promoted hints in the existing corpus were minted from self-authored (pipeline-authored) comments?

**The corpus IS reachable here** — a correction to the plan's framing. Most of `.plan/` is git-ignored and absent from this clone, but `.gitignore` (lines 46-48) carries explicit exceptions: `!.plan/marshal.json` and `!.plan/project-architecture/`. The architecture-hint store (`.plan/project-architecture/{module}/enriched.json`) is therefore **tracked and present**. This is a genuine *looked-and-found*, not a *could-not-look*.

**Population scanned:** all 12 tracked `enriched.json` files — `default/` plus 11 modules (`plan-marshall`, `pm-dev-frontend`, `pm-dev-frontend-cui`, `pm-dev-java`, `pm-dev-java-cui`, `pm-dev-oci`, `pm-dev-python`, `pm-documents`, `pm-plugin-development`, `pm-requirements`). Every `best_practices[]` / `insights[]` / `tips[]` entry read; the full set grep-swept for the comment-provenance signature (`pr-comment`, `taken_into_account`, `acknowledg*`, `unattributed`, `self-author*`, `triage-summary`, `review-trigger`, `review-bot`).

**Count of self-authored-minted hints: 0.**

Every comment-related preference hint present attributes to an **external review bot** (`default/` insights lines 13,15,16,17; `plan-marshall/` best-practice line 5; `pm-plugin-development/` line 3 — all about CodeRabbit / pr-agent / Sourcery meta traffic) or to **genuine operator / q-gate / user-review dispositions** (`default/` insights lines 8-9). None encodes the plan's predicted false preference — *"unattributed / pipeline-self PR comments are routinely taken into account"*. The observed `(default, pr-comment, taken_into_account)` self-minted hint is **absent from the store**.

**Provenance caveat (stated for honesty):** by privacy invariant (c) in `disposition-to-hint-routing.md`, the store persists only the generalized hint *string* — never the author / finding-class / raw disposition. So D0 is answered by reading every hint's TEXT and assessing whether any encodes the self-reinforcing artifact (none does), not by a provenance query the store cannot answer. The scan covered the complete reachable population; the negative is *looked-and-found-nothing*.

**Decision this gates:** **filter alone, no corpus repair.** Zero self-minted hints exist to repair; and any hypothetical repair would be a `.plan/` mutation this lane forbids and could not target anyway (no retained provenance).

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

_pending_

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
