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

**Second operator decision (after the verify-first findings on D2 were surfaced):** the three D2
blockers (fail-closed sensitivity, documented "triage-CI-first" reversal, unmeasured benefit blocked
behind an unreachable D0) were reported back to the operator. **The operator directed: "descope it,
document at the report and continue."** D2's dispatcher change is therefore **descoped for this run**
by explicit operator decision — recorded here as the only durable trace of that conversation event.
The run proceeds with: D1 verdict (committed), D0/D2/D3/D4 findings (this report), and the finalize
cycle (PR + review + merge).

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

**Recorded durably** in `phase-6-finalize/standards/source-edit-pushability.md` (§ "Its post-PR CI run
is intrinsic, not a defect to relocate") — an anti-speculation note so a future plan does not
re-litigate the era-stamp's extra run by relocating its commit. Commit: see Deliverables/commits below.

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

### D2 — one loop-back barrier across all finding producers (DESCOPED by operator decision; verify-first verdict below)

**Mechanical feasibility (agent-mapped, re-grounded against current code):** `automatic-review`(30) +
`sonar-roundtrip`(40) already share one unified triage barrier (dispatcher item 7c,
`producer=finalize-feedback`, `SKILL.md:1379-1421`). `ci-verify`(22) is the lone outlier. The
`finalize-feedback` union query is already type-agnostic (`manage-findings list --resolution pending
--include-qgate`, `verification-feedback.md:162`) and `triage` ∈ `FINDING_TYPES`
(`constants.py:123`), so the union query would already surface ci-verify's findings. CI-completion is
already the common precondition for all three (`requires: [ci-complete]`, resolved once at order 22 and
cached by HEAD SHA), so deferring ci-verify's *triage* to the 7c juncture never advances CI-completion —
the plan's verify-first "no CI-completion reorder" is satisfied.

**But the plan's D5(c) "fail-closed must hold" and its own epistemic discipline block shipping the fold
this run.** Three findings, from verify-first:

1. **Fail-closed rests on a mechanism a naive fold breaks.** ci-verify files `type: triage` findings,
   and `triage` is **NOT** in `_ACTIONABLE_FINDING_TYPES` (`_invariants.py:1049-1056` =
   `build-error, test-failure, lint-issue, sonar-issue, qgate, pr-comment`). So ci-verify's findings do
   **not** block the phase boundary. ci-verify's entire fail-closed comes from the step **returning
   `step_marked_done: False` and never calling mark-done on red CI** (`ci_verify.py:691,733`; locked by
   `test_ci_verify.py:489-490, 535-536`). A fold that makes ci-verify mark done after filing (the way
   `sonar-roundtrip`/`automatic-review` legitimately do — *their* findings ARE actionable) opens a
   fail-closed hole: red CI could merge on non-blocking `triage` findings. Preserving fail-closed
   requires either (a) keeping ci-verify un-`done` and adding a dispatcher done-record-on-resolve
   coupling (to avoid a phase-transition **deadlock** when 7c resolves ci-verify findings as
   accept/suppress with no loop-back), or (b) making ci-verify findings a blocking type — which breaks
   their deliberate operator-decides-between-runs `triage` design. Both are real redesigns.
2. **The fold reverses a documented design rationale.** `ci-verify.md:128-136` explicitly argues
   ci-verify must triage CI **first** so `architecture-refresh`/`automated-review`/`sonar-roundtrip`
   benefit and the loop-back signal is not delayed, and that placing it later "would be wrong." D2
   defers ci-verify's triage to *after* sonar(40) — a direct reversal, trading a faster loop-back
   signal for fewer CI runs. That trade-off is a design judgment, not a mechanical fold.
3. **The benefit is unmeasured and unmeasurable here.** The plan labels "Consolidating loop-backs
   yields a material token saving" a HYPOTHESIS blocked behind **D0** ("a plausible mechanism is not
   evidence"), and D0's corpus is unreachable from this clone. Implementing a design reversal (finding
   2) to chase an unmeasured benefit (finding 3) on a fail-closed-sensitive surface (finding 1) is the
   exact untruthful-signal move this plan exists to eliminate.

**Verdict:** the fold is mechanically feasible but its dispatcher change is **deferred** — it belongs
in a follow-up that (a) re-grounds against the sibling "gate re-firing over the loop-back diff" plan the
plan's Notes say to sequence after, (b) carries D0's measured benefit, and (c) resolves the
"triage-CI-first vs consolidate" trade-off against that measurement, with the fail-closed done-record
coupling designed explicitly. The full design is recorded above so the follow-up starts from it, not
from scratch.

### D5 — tests

- (a) era-stamp-only → one CI run: the D1 verdict shows the extra run is **intrinsic** to the
  PR-number dependency (not a defect to relocate), recorded in `source-edit-pushability.md`. The
  ordering invariant (era-stamp 21 < ci-verify 22) already holds and is derived by
  `test_finalize_edge_ordering.py`. No new mechanism, so no new test.
- (b) two producers → one loop-back round: **coupled to the deferred D2 dispatcher change** — not added
  this run (there is no consolidated barrier to turn it green against).
- (c) fail-closed still holds: the invariant a batched barrier must preserve — ci-verify's red path
  returns `step_marked_done: False` — is **already locked** by `test_ci_verify.py:489-490, 535-536`.
  This is the guard any future D2 fold must keep green; referenced, not duplicated.
- (d) self-review finds a known defect: **already covered** by
  `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_defect_regression.py`
  (positive-fires / negative-silent / cross-class matched controls). No phase-mismatch test is added
  (D3 refuted).

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty**. No buildable footprint, local build
skipped (the gate is `*.py`-only; the merge queue's `merge_group` run verifies the docs/skill change
before it lands). Tree clean (`git status --porcelain` empty) at the gate.

Note: the plan's Verification section expected "Python, documentation, and test changes … the build
gate takes its full path." This run made **no** Python/test changes because the verify-first verdict
deferred D2's dispatcher change (see D2 above), so the full build path did not apply. This is an
honest consequence of the verdict, not a skipped step.

## Findings

_pending_

## Reviewer participation

Expected reviewer population, derived from the registry docs
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` `author_login`
fields (M = 3): `sourcery-ai` (`sourcery.md:25`), `coderabbitai` (`coderabbit.md:27`),
`cuioss-review-bot` (`pr-agent.md:55`). The diff touches `marketplace/bundles/**` (a skill doc), so
the PR keeps bot review (no `skip-bot-review`).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | _pending review cycle_ | — |
| `coderabbitai` | _pending review cycle_ | — |
| `sourcery-ai` | _pending review cycle_ | — |

Coverage and any Step 8 shortfall disclosure recorded after the review cycle, before arming merge.

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness does not expose
  a per-run token figure to the model. Stated plainly rather than estimated.
- **Wall-clock:** single interactive cloud session on 2026-08-12 (UTC); exact start/end not
  instrumented by the agent.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total (that counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  per-task billing boundary, which this interactive session does not share). No comparable figure is
  presented.

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

- **D2 dispatcher change (fold ci-verify into the unified triage barrier)** — deferred to a follow-up
  plan. The full design and the three blocking reasons are recorded under Deliverables → D2. The
  follow-up must: (a) re-ground against the sibling "gate re-firing over the loop-back diff" plan; (b)
  carry D0's measured benefit (needs the archived CI-manifest corpus, unreachable from a cloud clone);
  (c) resolve the "triage-CI-first vs consolidate" trade-off against that measurement; (d) design the
  fail-closed done-record coupling so ci-verify's step-not-done blocking is preserved (guard:
  `test_ci_verify.py:489-490, 535-536`).
- **D5(b) test** (two producers → one loop-back round) — coupled to the deferred D2 change; add it with
  that change.
- **D3/D4 (self-review half)** — no valid implementation target this run (D3 premise refuted). The real
  self-review concern (detector blindness) is owned by the out-of-scope sibling
  `doc/plans/code-intelligence-substrate/100-self-review-surfacing-integrity.md`.
- **D0 quantitative attribution + token sizing** — unreachable from this clone (`.plan/` corpus
  absent). Re-derivable only where the archived CI manifests and metrics are present.
