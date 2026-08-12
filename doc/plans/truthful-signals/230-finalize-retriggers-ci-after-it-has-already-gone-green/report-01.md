# Run report — 230-finalize-retriggers-ci-after-it-has-already-gone-green (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/finalize-retriggers-ci-green-agofze` (harness-assigned; kept as-is per lane)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, governing contract).
- `plan-marshall:ref-code-quality` — read from bundle path (plugin route not required).
- `pm-plugin-development:plugin-script-architecture` — read from bundle path.
- Conditional, by surface: finalize dispatcher + self-review workflow + tests are the surface. Domain
  skills consulted as the work reaches them (see Deliverables).

GitHub access path: **GitHub MCP server** (cloud session; `gh` CLI absent).

## Reachability finding (shapes D0)

`.plan/` is present in this clone but contains **only** `marshal.json` and the crawled
`project-architecture/` inventory — **no generated executor (`.plan/execute-script.py`), no archived
plan corpus, no CI manifests, no metrics**. Verified:

- `test -d .plan` → exists; `test -f .plan/execute-script.py` → **absent**.
- `ls .plan` → `marshal.json`, `project-architecture/` only.

Consequence: the archived CI-manifest corpus that D0's quantitative attribution depends on is **not
reachable from this clone**, exactly as the plan anticipated (Claim-labels: "Not reachable from this
clone — the corpus is under `.plan/`"). D0 therefore degrades from a per-plan quantitative split to a
**mechanism-level attribution** from the reachable code, with the quantitative split explicitly
recorded as "could not look" rather than fabricated. Full detail under Deliverables → D0.

## Directly-verified plan claims (reachable from this clone)

- ✅ **push.md names the "finalize-internal re-stale (known-safe)" class** and lists the two
  finalize-internal `mutates_source: true` steps that commit during finalize: `era-stamp-fill` and
  `lessons-capture` — `phase-6-finalize/standards/push.md:54-59`.
- ✅ **A post-PR re-push fast path is documented** — `push.md:115` ("explicit post-PR re-invocation
  after a `mutates_source` step commits (item 5f § 'Post-PR re-push') as the fast path").
- ✅ **Self-review findings are WRITTEN at phase `6-finalize`, source `qgate`** —
  `phase-6-finalize/workflow/pre-submission-self-review.md:334-338` (Step 4 Branch B
  `manage-findings qgate add --phase 6-finalize --source qgate`). The QUERY side (D3 premise) is under
  investigation.
- ✅ **era-stamp-fill currently makes its OWN commit + push** at order 21 (after `create-pr` order 20,
  before `ci-verify` order 22) — `.claude/skills/finalize-step-era-stamp-fill/SKILL.md:123-144`,
  ordering at `:66-77`. It resolves `PR-PENDING` → `#{pr_number}` in `audit.py` + `test_audit.py`.

## Scope decision (reachable-operator escalation)

The investigation refuted the plan's central self-review premise (D3) and confirmed D0's quantitative
corpus is unreachable from this cloud clone. Per the lane's reachable-operator rule and the plan's own
split-guard authorization ("if D3–D4 prove separable, ship the CI half first"), the scope was
escalated via `AskUserQuestion`.

**Question:** Given D3's phase-mismatch premise is refuted and D0's corpus is unreachable, what scope
should this run deliver?
**Answer:** **"CI-half + findings"** — implement D2 (fold ci-verify into the existing unified triage
barrier), record the D1 era-stamp verdict, add D5(b)+D5(c) tests (each seen red first), and report
D0/D3/D4 honestly. Defer the self-review half and the risky-beyond-D2 work.

## Deliverables

### D0 — attribution (mechanism-level; quantitative split "could not look")

`.plan/` in this clone contains only `marshal.json` + `project-architecture/` — **no archived
CI-manifest corpus, no metrics, no executor** (verified). The per-plan quantitative split and the
709k token figure are therefore **not re-derivable here**; they remain the plan's stated
OBSERVED/HYPOTHESIS motivation. Mechanism attribution from the reachable code:

- **Post-PR source-mutating steps = exactly three**: `era-stamp-fill`(21), `automatic-review`(30),
  `sonar-roundtrip`(40). Only era-stamp makes a guaranteed own commit+push; review/sonar mutate only
  via loop-back fixes.
- **Loop-back producers**: `ci-verify`(22) runs its **own** triage+loop-back (item 7b);
  `automatic-review`(30)+`sonar-roundtrip`(40) **already share one** unified triage barrier (item 7c).
  So the multi-round CI waste attributable to loop-backs is dominated by `ci-verify` looping
  **separately** from the already-unified review+sonar barrier — which is exactly what D2 fixes.
- **The split between (a) post-green era-stamp push and (b) loop-back rounds is UNMEASURABLE from this
  clone.** Reported as "could not look", not fabricated. Both mechanisms are confirmed present.

### D1 — era-stamp post-PR push verdict (recorded)

Per-step verdict for the three post-PR source-mutating steps (detail + evidence below in a committed
doc note):

- **`era-stamp-fill`(21)**: (a) compute pre-PR — **IMPOSSIBLE** (needs the real PR number, which only
  exists after `create-pr`/20). Ride an existing post-PR commit — **no reliable carrier** in the
  era-stamp-only case (`create-pr` makes no commit; a loop-back commit is not guaranteed). Defer to
  *after* merge — **REFUSED**, it resurrects the unpushable-on-`main`/guessed-number defect the
  sentinel exists to prevent. **Verdict: must remain its own pre-merge commit; its one extra CI run in
  the era-stamp-only case is intrinsic to the PR-number dependency.** The only lever that removes it
  (verify-workflow concurrency cancellation) lives in `.github/workflows/`, outside this plan's
  declared surface. When a co-occurring loop-back commit exists, its correction should ride that
  commit rather than a separate push (D2 consolidation reduces the co-occurring case).
- **`automatic-review`(30)/`sonar-roundtrip`(40)**: post-PR by nature (react to PR-side
  review/analysis). Not internally computable earlier. **Verdict: consolidate via D2** — already the
  target of the unified barrier.

### D3 — self-review phase mismatch: PREMISE REFUTED (nothing to implement)

Verified at all four load-bearing sites (each independently re-read): writer files at `6-finalize`
(`pre-submission-self-review.md:334`); the phase-transition blocking gate loops **all** `QGATE_PHASES`
including 6-finalize (`_invariants.py:1103-1164`, "phase-agnostic" by docstring); the lessons signal
gate loops all five phases (`SKILL.md:741-760`); the unified triage loops `QGATE_PHASES`
(`_findings_core.py:396-408`); the retrospective globs **all** `qgate-*.jsonl`
(`audit.py:3248`), with `no_qgate6` firing on genuine `self_total == 0` (`:3322-3324`) — the "6" is a
label, not a phase filter. **No execute-phase query reads self-review findings**, so there is no
mismatch to fix. The "examined-nothing vs found-nothing" distinguishability the plan wants **already
exists** as two disjoint clean verdicts (`:296-302`). The real self-review concern (detector
blindness) is owned by the out-of-scope sibling `100-self-review-surfacing-integrity`. Reporting the
refutation is the truthful-signals-correct outcome; fabricating a phase-repoint would be a fix for a
non-existent defect.

### D4 — scope self-review: undermined by D3's refutation

D4 is framed "Given D3, decide what the step should examine." With D3 refuted, the premise is gone,
and the absolute token figure D4 must be measured against (709k) is under `.plan/` and unreachable.
No self-review scoping change is made this run (operator chose CI-half + findings).

### D2 — one loop-back barrier across all finding producers (IN PROGRESS)

Feasibility confirmed (agent-mapped, re-grounded against current code): fold `ci-verify` into the
existing item-7c unified triage barrier so all three producers share one loop-back round, without
advancing the CI-completion precondition (verify-first satisfied — deferring ci-verify's triage from
order 22 to the 7c juncture never forces CI earlier). Five fail-closed sites to preserve. Implementation
detail and tests recorded below as the work proceeds.

### D5 — tests

- (b) two producers → one loop-back round — planned in `test/plan-marshall/phase-6-finalize/`.
- (c) fail-closed under the batched barrier — planned in
  `test/plan-marshall/workflow-integration-github/` (closest analog: `test_pre_merge_barrier.py`).
- (a) era-stamp-only → one CI run: the D1 verdict shows the extra run is intrinsic; the ordering
  invariant (era-stamp 21 < ci-verify 22) already holds. Recorded as a verdict, not a new mechanism.
- (d) self-review finds a known defect: **already covered** by
  `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_defect_regression.py`
  (positive-fires / negative-silent / cross-class matched controls). No phase-mismatch test is added
  (D3 refuted).

## Build gate

_pending_

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
