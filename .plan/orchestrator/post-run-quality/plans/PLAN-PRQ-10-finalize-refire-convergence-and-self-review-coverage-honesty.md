# PLAN-PRQ-10: The finalize loop re-fires converged steps, and the self-review cannot tell a swept class from an unswept one

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-19 from three `candidate-lesson` messages filed first-party by `PLAN-PRQ-06`'s own
retrospective (PR #1541, `a1dd4901f`) and delivered to this epic's inbox by hand after `emit-landing`
failed open: `prq-06-a-lane-override-that-cannot-take-effect-is-003.md`, `-018.md`, `-019.md`. The three
name one phenomenon and three of its drivers, and two of them cross-reference each other in their own
text. Drafted by a dispatched `execution-context-level-5` leaf and adjudicated by the orchestrator.

⚠ `-019`'s payload was also filed to the global corpus as lesson `2026-09-19-12-001` during the run. That
lesson is superseded by this spec — see the epic's Decisions for the pointer.

## Objective

**Finalize cost more than the work it was finalizing, and the loop that drove the cost cannot tell when
it has converged.** On `PLAN-PRQ-06`, 6-finalize consumed 4,232,432 of 8,444,415 tokens (50%) against an
anchor that errors at 1.6M — 5.3× the error column — across 47 step firings over 9 steps where 9 would
suffice. The re-firing is not one expensive step: `finalize-step-simplify` fired 12 times reporting `0
edits`, `lessons-housekeeping` 8 times reporting `0 rm, 0 promo, 0 adapt`, `plugin-doctor` 7 times
reporting `clean`. Each re-fire paid a fresh envelope to re-confirm a settled answer, because no step is
gated on a convergence probe.

Two mechanisms inside the loop manufacture iterations rather than measuring them. The self-review's
`further_round_owed` predicate files a **loop-control fact as a Q-Gate finding**: four such findings on
one plan, every one resolved not by fixing anything but by recording that a later round superseded it, two
resolution texts byte-identical across pairs. And a swept file's actual shape (AsciiDoc) is covered by
**no detector at all**, so it returned zero candidates — and in the verdict, zero candidates is
indistinguishable from swept-and-clean. ⛔ **CORRECTED 2026-09-21 (cleanup, `checked_at: e8a71650`)**: the
`CONTENT_CLASSES` registry declares **six** classes (`python`, `skill_doc`, `standards_doc`,
`markdown_other`, `structured_config`, `other`), not five, and "AsciiDoc bullet-list prose" is not one of
them — a `.adoc` file lands in the unnamed catch-all `other`, which also absorbs every other unclassified
file shape. The substance survives and is if anything sharper: zero detectors reach AsciiDoc specifically,
confirmed by a direct sweep of all three implementor modules. Re-firing that step could never change that
signal; the defect in that file was found only because an operator opened it by hand, twice.

⭐ This is the epic's own instrument applied to the loop that gates every plan's push: after this lands, a
reader must be able to tell *"this step has converged"* from *"this step keeps being asked"*, and *"this
class was examined and is clean"* from *"no instrument looked at this class"*.

## Deliverables

Six deliverables. D0 is a gate.

**D0 — GATE: derive the re-firing population and the detector→content-class reach map, and publish both
with their sizes.**
(a) Over the archived-plan corpus, per finalize step: firing count, distribution of last-reported
outcomes, and how many firings reported no work performed. ⛔ One plan's 47 firings is an instance; the
corpus figure decides whether D1 is a convergence probe or a threshold tweak. `manage-status`
`metadata.phase_steps` and `manage-execution-manifest refire-report` are the two available readers — ⛔
note `refire-report` reads ONLY `execution_log` (`manage-execution-manifest.py:2918`, helper
`:2801-2849`), which `PLAN-PRQ-08` D2 records as under-counting exactly the steps that re-fire most. Read
both ledgers and publish the disagreement rather than picking one.
(b) For every entry in the `ext-self-review-plan-marshall` `CANDIDATE_LISTS` registry, state which
`CONTENT_CLASSES` members it can produce a candidate for. Publish the matrix and the count of (class,
detector) pairs, and the classes with zero covering detectors. ⛔⛔ **CORRECTED 2026-09-21 (cleanup,
`checked_at: e8a71650`): `CANDIDATE_LISTS` is NOT in `_self_review_detectors.py`** (which declares only
`CONTENT_CLASSES`) — it is defined at `_self_review_patterns.py:488-541` (22 `CandidateList` entries) and
consumed by `self_review.py`. Neither file was in this spec's Expected Surface; both are added below.
⭐ Each `CandidateList` carries a `family` (`structural` / `prose_contract`), **not** a content class — so
this reach map is derivable only by analysing each detector's body against `CONTENT_CLASSES`, which is
precisely the cost both `:222` and the `_self_review_detectors.py:2327-2330` comment assert is
prohibitive. D0(b) must size this work explicitly before D3 commits to amending either site. ⛔ This
derivation is the whole load-bearing question of D3 — see its Claim Label.

**D1 — A finalize step does not re-fire once it has converged, and "converged" is a published fact.**
Gate re-firing on a cheap idempotence probe rather than re-dispatching the whole ordered prefix at full
envelope cost on every loop-back. ⛔⛔ **NARROWED 2026-09-21 (cleanup, `checked_at: e8a71650`): shape (ii)
is REFUTED, D1 is scoped to shapes (i) and (iii) only.** `ext-point-finalize-step.md:120-124` states
`work_performed` is deliberately NOT a per-step template — it is exactly one fact with a fixed key,
declared only CONDITIONALLY (when a `done` branch is reachable without characteristic work), and every
declaring step must record it at every terminal call site. Generalising it to all steps is a per-step
contract change at every call site, not a free derivation — the standard refuses the template shape (ii)
assumed. The declarer population is also corrected: **four** steps declare it today
(`finalize-step-sync-baseline`, `branch-cleanup`, `sonar-roundtrip`, `emit-landing`), not two, and the
archived `PLAN-PRQ-06` already shows `pre-submission-self-review` recording it as well.
(i) **HEAD-bound skip** — several steps already stamp `head_at_completion`; when it equals current HEAD
and the last outcome was `done` with a no-work facts block, record `outcome: done, basis: unchanged-head`
without dispatching.
(iii) **Cap the prefix** — on loop-back iteration N, re-fire only the steps whose inputs the loop-back
actually invalidated.
⛔ Whichever is chosen, a skipped firing MUST be recorded as skipped-with-basis, never as a firing that
ran and found nothing: the two are different facts and collapsing them re-creates the epic's own
archetype inside its fix.

**D2 — A loop-control fact is not a Q-Gate finding.**
`further_round_owed` fires once per non-clean round and its only resolution is "a later round superseded
it" — four such rows on one plan, put through the triage surface and into every downstream finding count.
That a round which found things did not also close is already implied by the loop continuing. Either stop
filing it as a finding and record it as loop state, or restrict the filing to the load-bearing case. ⭐
The load-bearing case is identified and MUST survive: `5e9ee0`'s shape — a delta-scoped round verified
clean but `may_close=no` **because it was a delta round**, owing a full-surface confirmation — is what
prevents a delta pass from closing on a partial surface, and is already contractual
(`ext-point-self-review-surfacing.md:56`, "A delta-scoped round cannot close the step"). Keep that; retire
the bookkeeping rows.

**D3 — A per-class candidate count states which kind of zero it is.**
⛔⛔ **This deliverable contradicts a sentence in the governing standard, deliberately, and must discharge
it rather than ignore it.** `ext-point-self-review-surfacing.md:222` currently states that separating
"covered class, nothing found" from "no detector covers this class" *"would need a per-detector reach map
no implementor can derive, and publishing one would be a stronger claim than the evidence carries."* D0(b)
is the test of that claim. ⛔⛔ **CORRECTED 2026-09-21 (cleanup, `checked_at: e8a71650`): a SECOND site
makes the identical assertion — `_self_review_detectors.py:2327-2330`'s comment directly above the
`CONTENT_CLASSES` registry ("a claim about detector reach that nothing here can verify… the same fail-open
this fact exists to close"). D3's amendment must discharge BOTH sites or it ships the same contradiction
it forbids.** If D0(b) derives the map from the registry, this deliverable adds per-class detector
coverage beside `delta_coverage.by_class[]` (so a class with `files > 0`, `files_with_candidates: 0` and
`detectors: 0` is visibly a GAP, not a pass) **and amends both sentences in the same act**, stating what
changed and why. If D0(b) shows the map is genuinely underivable, this deliverable ships the refutation
and the reason at both sites, and D4 covers the class instead. ⛔ Either outcome is a result. What is
forbidden is adding the field while leaving either sentence saying it cannot be derived.

**D4 — AsciiDoc content gets a detector, or its absence is declared at the registry.** ⛔ **CORRECTED
2026-09-21: there is no "the uncovered class" — `CONTENT_CLASSES` has six members and AsciiDoc is not one
of them; `.adoc` files fall into the unnamed catch-all `other`, which also absorbs every other
unclassified shape.** `doc/user/configuration.adoc` — the measured instance — is where the operator found
a stale floor enumeration by hand, in a user-facing document no detector reaches. Either (a) introduce a
distinct AsciiDoc class in the registry and add a detector reaching it, or (b) record explicitly that
`other` bundles AsciiDoc with everything else and that D3's coverage field over `other` therefore answers
nothing about AsciiDoc specifically — a registry change D0(b)/D3 must scope, not assume. ⛔ The fix set is
whatever D0(b) returns — this one member was found by an operator reading a file, which is the
under-derived-population archetype.

**D5 — Controls.**
(i) A step whose inputs DID change still re-fires — the matched negative for D1, pinned by a case where
HEAD moved. (ii) A delta round still cannot close the step — the matched positive for D2's preserved
case. (iii) A class with a live detector and a real candidate still reports it, and a class with a live
detector and nothing to find still reports a clean zero — the matched pair for D3, so the new field
cannot report every zero as a gap. (iv) Per the epic's standing rule every guard here is
population-derived and publishes the population it scored; a probe that can report "0 unconverged steps"
from an empty firing set is the vacuous-guard archetype this epic has recorded at n≥6.

## Claim Labels

- OBSERVED: 6-finalize consumed 4,232,432 of 8,444,415 tokens (50%) across 47 firings over 9 steps and 6
  loop-back iterations on `PLAN-PRQ-06`; `finalize-step-simplify` 12 firings / "0 edits",
  `pre-submission-self-review` 9 firings with 7 of 8 prior returning `loop_back`, `lessons-housekeeping`
  8 / "0 rm, 0 promo, 0 adapt", `plugin-doctor` 7 / "clean". First-party from that plan's
  `status.metadata.phase_steps` and its `plan_efficiency` aspect. ⛔ The plan directory is archived —
  re-derive from the archived corpus at outline, do not re-read this restatement (verify-at-outline).
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: All figures exact, re-derived from archived status.json + fragment-plan-efficiency.toon. One nuance: the 47-firing total sums only the 9 steps with firing_count>1, excluding 13 single-firing steps out of 22 total steps / 60 total firings -- D0(a) must state which denominator it publishes. Also confirms execution.toon's execution_log carries only 30 of 6-finalize's rows -- live first-party evidence of PRQ-08 D2's under-count, measurable before D0 runs.
- OBSERVED: `may_close` and `further_round_owed` are defined and consumed in
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` and
  nowhere else outside tests — content sweep, 37 hits in that file, 6 across 5 test files, 0 elsewhere;
  3080 files scanned, 0 unreadable, no truncation, no elision (2026-09-19).
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: may_close: 34 hits in pre-submission-self-review.md + 4 across 3 test files. further_round_owed: 3 hits same file + 2 across 2 test files. Totals 37/6/0 reproduce exactly. files_scanned 3089 (grew from 3080, not drift), 0 unreadable.
- OBSERVED: `ext-point-self-review-surfacing.md:222` declines the per-detector reach map on the stated
  ground that "no implementor can derive" it, while `:219` states the class vocabulary is declared in the
  implementor's own `CONTENT_CLASSES` registry, and that registry exists at
  `pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`. The two
  sentences sit in one document. Read directly, 2026-09-19.
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: :222 and :219 verbatim as claimed; registry confirmed at _self_review_detectors.py:2331. FLAG for D3: a SECOND site makes the same underivability assertion -- _self_review_detectors.py:2327-2330's comment directly above the registry. D3's amendment must discharge BOTH sites or it ships the same contradiction it forbids.
- OBSERVED: `5e9ee0` is the load-bearing `may_close=no` case (delta round clean, full-surface confirmation
  owed) and is contractual at `ext-point-self-review-surfacing.md:56`. D2 must not retire it.
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: :56 verbatim: 'A delta-scoped round cannot close the step...' The contract D2 must preserve is live and unambiguous. Finding id 5e9ee0 lives in the archived findings store, not re-opened this pass; the contractual claim does not depend on it.
- ⚠ HYPOTHESIS: the four steps named above are not the whole re-firing population — D0(a) owns the
  derivation and may return a larger or smaller set (verify-at-outline).
  - verdict: corroborated | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Derived from archived status.json phase_steps: nine steps re-fired (simplify 12, self-review 9, lessons-housekeeping 8, plugin-doctor 7, pre-push-quality-gate 3, push 2, ci-verify 2, automatic-review 2, branch-cleanup 2), 13 of 22 fired once. Hypothesis confirmed on one plan before D0 starts; D0(a) inherits a floor of 9, not 4.
- ⚠ HYPOTHESIS: AsciiDoc bullet-list prose is the only content class with zero covering detectors. ⛔
  Asserted by nobody; it was found by an operator opening one file. D0(b) owns it (verify-at-outline).
  - verdict: contradicted | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: yes | evidence: CONTENT_CLASSES (_self_review_detectors.py:2331-2338) has SIX members: python, skill_doc, standards_doc, markdown_other, structured_config, other. 'AsciiDoc bullet-list prose' is not a declared class -- .adoc lands in the unnamed catch-all 'other' per _classify_content (:2344-2368). Objective's 'one of five classes' is a count error, same archetype as PRQ-02/09's 16-vs-17. Substance survives: 0 hits for adoc across all three implementor modules -- no detector reaches AsciiDoc at all. D4 must name 'other' explicitly or scope an AsciiDoc class -- neither is currently stated.
- ⚠ HYPOTHESIS: a `work_performed`-style convergence flag is derivable for every finalize step without a
  per-step change — confirm/refute at `finalize-step-sync-baseline` and `branch-cleanup`, which already
  publish it, and at the `ext-point-finalize-step` facts contract (verify-at-outline). If refuted, D1
  narrows to shape (i) or (iii).
  - verdict: contradicted | checked_at: e8a71650 | by: post-run-quality/cleanup | rescoped: yes | evidence: ext-point-finalize-step.md:120-124: work_performed is exactly one fact with a fixed key, deliberately NOT a per-step template; declaring it is CONDITIONAL (only when a done branch is reachable without characteristic work), binding every declaring step at every terminal call site. Generalising to all steps is a per-step change, not a free derivation -- the contract refuses the template the hypothesis assumes. D1 narrows to shape (i) or (iii) per the spec's own fallback. Also: declarer population is FOUR not two -- :144 sync-baseline, :145 branch-cleanup, :146 sonar-roundtrip, :149 emit-landing; archived PRQ-06 status.json also shows pre-submission-self-review recording facts.work_performed.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — D2 (`may_close` / `further_round_owed`)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — D1 (the step loop and its re-fire path)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — D3 (the coverage field AND the `:222` sentence it amends)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — D0(b), D3, D4 (the `CONTENT_CLASSES` registry and its own `:2327-2330` underivability comment)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — D0(b) (added 2026-09-21 — the ACTUAL `CANDIDATE_LISTS` registry, `:488-541`)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py` — D0(b) (added 2026-09-21 — `CANDIDATE_LISTS`' consumer)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — D0(b), D4 (§ Detection Rules, the authoritative enumeration)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — D1, only if the convergence fact rides the step facts contract (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — D0(a), only if `refire-report` must be read or extended (verify-at-outline)
- OBSERVED: `doc/user/configuration.adoc` — D4's measured instance (read for the class, not necessarily edited)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — D5 (i), (ii)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/` — D5 (iii), (iv)

## Dependencies and Sequencing

- Depends on: none.
- ⛔⛔ **CROSS-EPIC, INVISIBLE TO BOTH GATES — FOUR staged plans across THREE ledgers, not one
  (corrected 2026-09-21, cleanup, `checked_at: e8a71650`).** This spec originally named only
  `PLAN-CIS-052`; three more are confirmed staged and contending for the identical 3-5 files:
  - `code-intelligence-substrate` **`PLAN-CIS-052`** (staged, 10 deliverables) declares
    `phase-6-finalize/workflow/pre-submission-self-review.md` for D1b and all of D5, and extends it with
    folds **N3** (a round that suppresses findings it identified still reports `clean`), **N4**
    (`cohort_size` is round-scoped), **N5** (clause-deletion fixes re-flag the same line round after
    round; `repeat_site: true`). N3 and N5 sit in the same document and the same neighbourhood as this
    spec's D2 and D3.
  - `truthful-signals` **`PLAN-TRUTH-173`** (staged) — *"the in-run self-review instrument, detector
    reach, a bounded terminus and six vacuity modes"*. Its Expected Surface names
    `_self_review_detectors.py`, `_self_review_patterns.py`, `pre-submission-self-review.md`,
    `ext-point-self-review-surfacing.md` and the test dir — **every one a surface this spec also
    declares**. Its D0 ("derive the detector-class population") and D2 ("a bounded terminus for the
    review chain") are this spec's D0(b) and D1/D2 by another name, in another ledger. That epic's own
    Deps already record "Never pair with `PLAN-TRUTH-167`".
  - `truthful-signals` **`PLAN-TRUTH-167`** (staged) — *"self-review on a diff no resolvable surfacer
    applies to loops to the ceiling instead of reporting not-covered"*. Its Expected Surface includes
    `pre-submission-self-review.md`, `ext-point-self-review-surfacing.md`, `self_review.py`, and both
    test dirs.
  - `review-apparatus` **`PLAN-PR-074`** (staged) — per `PLAN-TRUTH-173`'s own Deps: *"`PLAN-PR-074` D6
    edits `_self_review_detectors.py` and `_self_review_patterns.py` and sweeps them for the six vacuity
    modes BEFORE editing."*
  ⛔ Never run this spec concurrently with ANY of the three; whichever lands first moves the contested
  files under the others, and every survivor must be re-grounded before its own emit. Check all three
  epics' queues via `manage-status list` before launching — not only `code-intelligence-substrate`'s.
- ⚠ Shares `phase-6-finalize/**` with `PLAN-PRQ-04` and (conditionally) `PLAN-PRQ-07` — at
  `parallelization_scope: 1` that is automatic, but recorded so a raised knob does not pair them.
- D0(a)'s ledger-disagreement read is `PLAN-PRQ-08` D2's subject. ⛔ **Report the disagreement; do not fix
  `refire-report` here.** If PRQ-08 lands first, D0(a) consumes its corrected reader.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-10-finalize-refire-convergence-and-self-review-coverage-honesty.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
