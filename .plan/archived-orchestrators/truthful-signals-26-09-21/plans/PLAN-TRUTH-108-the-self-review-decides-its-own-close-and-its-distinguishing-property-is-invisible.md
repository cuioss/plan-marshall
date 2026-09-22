# PLAN-TRUTH-108: The self-review decides its own close, and its distinguishing property is invisible in the summary

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-24 from a parallel audit of the cloud-plan runs, whose input was `doc/concepts`
(top-level files only). It concluded:

> *"its bounded adversarial verification loop is a cloud-lane invention plan-marshall doesn't have in
> the same form, and the reports call it the highest-yield step in the whole method. So is the
> non-converging signal."*

⛔⛔ **THAT CONCLUSION IS MOSTLY WRONG, AND THE WAY IT IS WRONG IS THIS EPIC'S OWN ARCHETYPE.** It is an
absence claim drawn against an input scope it did not state. **Do not implement it as written.** The
first-party comparison below is what this plan is scoped from.

## Objective

Close the one genuine gap: plan-marshall's self-review is self-assessed rather than adversarial. That
means no verifier independence, and the stop question is decided author-side instead of being asked of
the verifier. The request narrative is § "What is genuinely missing" below. § "What plan-marshall already
has" is explicitly out of scope. *(Section added at the 2026-09-11 `cleanup` as a pointer.)*

## What plan-marshall already has — verified, and NOT in scope

`phase-6-finalize/workflow/pre-submission-self-review.md` carries the bounded loop **in more detail than
the lane's**:

| Property | plan-marshall |
|---|---|
| Bounded multi-round loop | ✅ `head_dependent: true`, re-fires every loop-back, delta anchor via `--since-ref` |
| Only a full-surface clean pass may close | ✅ Step 4 Branch A precondition |
| **The non-converging signal** | ✅ **explicit and named** — *"**Converged** vs **out of budget** — these are two DIFFERENT closes and a later reader MUST NOT collapse them"* |
| Scope honesty | ✅ `scope_statement`, `structural_limit`, `counts.by_family` |
| Self-seeding rounds | ✅ named, with *resolve by deletion* |

⭐⭐ **And on one axis plan-marshall is AHEAD of the lane.** The lane *diagnoses* the repeat-defect
pattern — *"a fix applied at n−1 of n sites is why a corrected claim keeps reappearing round after
round"*, with a per-round table. plan-marshall **encodes the remedy**: the cohort sweep requires that
when a check fires with `defect_class` D, every other surfaced candidate is re-scanned for D and every
member is filed **in the same round**.

⛔ **None of the above is in scope. Do not re-derive, re-specify, or "improve" it.** The audit's claim
that these are missing is refuted, and re-adding them would duplicate shipped machinery.

## What is genuinely missing — two properties, and they are the same property twice

**The lane's verification is ADVERSARIAL; plan-marshall's is SELF-ASSESSED.** That is the whole
residue, and "adversarial" is the word doing real work in the audit's sentence.

**1. No verifier independence.** The lane dispatches a sub-agent that *"has **not** seen this plan or
the diff"*. plan-marshall's step is a deterministic surfacer plus, in its own words, *"an LLM cognitive
review applied"* — **in the finalize envelope, by the same context that wrote the code.**

**2. The stop question is not asked of the verifier.** The lane asks it directly — *"does anything you
found remain that condition A or B forbids leaving open?"* — with A and B quoted to the verifier and
every survivor from earlier rounds listed, and states explicitly that it *"is asked of the verifier
here rather than decided by the author afterwards."* plan-marshall closes on a **mechanical
precondition evaluated author-side**: findings list empty, `surface_scope: full`.

⇒ **The entity that wants to ship is the entity that decides nothing remains.**

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: settle whether independence is achievable here at all, and at what cost.** The lane runs
one plan per session in a standalone lane; plan-marshall dispatches `pre-submission-self-review` inside
a finalize envelope that already holds the plan. ⛔ **Do not assume the lane's shape transplants.**
Establish: can a blind verifier be dispatched through `execution-context-{level}` with the diff and the
contract but **not** the plan; what does it cost against the step's already-large budget (one observed
run: **8 firings, 115 candidates, 20 findings**); and does the existing surfacer/check split already
supply part of the independence (the surfacer IS deterministic and plan-blind — **only the cognitive
review is not**).

⭐ **A partial answer may be the right answer.** If full independence is unaffordable, an
independent verifier asked ONLY the stop question — over the findings the existing rounds produced — is
cheaper than a blind re-review and captures most of D2's value. **Price both.**

**D1 — verifier independence, per D0.** ⚠ Whatever is built must preserve what already works: the
delta/full scoping, the cohort sweep, `structural_limit`, and the converged-vs-out-of-budget
distinction are **not** to be touched.

**D2 — the stop question is asked of the verifier, not evaluated by the author.** Port the lane's
shape: quote the forbid/permit conditions to the verifier, list every survivor still open from earlier
rounds, and let its answer be an input to the close. ⛔ **This does NOT replace Branch A's
full-surface precondition** — that precondition is a scope guarantee and remains necessary. The stop
question is an **additional** gate, not a substitute: today a full-surface clean pass closes the step
with nobody asked whether the survivors it is leaving are acceptable.

⚠ **plan-marshall has no documented A/B condition taxonomy.** The lane quotes conditions A and B to its
verifier; this repo's equivalent would have to be derived. **D0 establishes whether one exists under
another name** (the findings-severity vocabulary, the Q-Gate disposition set) **or must be authored** —
and authoring one is a materially larger change that should be split out rather than absorbed.

**D3 — the concept summary characterises the step, in ONE clause.** ⛔ **THIS IS DELIBERATELY TINY AND
MUST NOT GROW.** `doc/concepts/README.adoc` states these pages are *"short navigational summaries over
the canonical specifications co-located with the code"*, so **specifying the loop there would violate
both that contract and the repo's no-duplication standard.** The link already exists
(`automatic-reviews.adoc:42` → `pre-submission-self-review.md`).

⇒ The defect is narrower: `automatic-reviews.adoc:14` names *"structural self-review"* in a list of
seven surfaces and conveys **nothing about its most distinctive property**, so a reader summarising
*from the concepts* under-represents it — which is exactly what the audit did. **Fix: one clause naming
that it is a bounded multi-round loop closing only on a full-surface clean pass, and that a
budget-exhausted close is reported as such and never as converged.** ⛔ No new page, no expanded
section, no restatement of the mechanics.

⚠ **Record honestly that this is a shared failure.** The audit had a link it did not follow, or was
scoped not to. **The doc change reduces the chance of the next false negative; it does not make the
method sound.** Do not write D3 up as the fix for the audit's error.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` *(expected READ-ONLY — the surfacer contract is consumed, not changed; record the reason if that proves false)*
- `doc/concepts/automatic-reviews.adoc`
- `test/plan-marshall/phase-6-finalize/`

- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — the per-instance vs per-class candidate emission granularity, added 2026-09-03 by the drain fold of `dual-homed-hook-install-renders-identically-001` (verify-at-outline)

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.**

- ⛔⛔ **`PLAN-TRUTH-097` — SERIALIZE, hard.** `pre-submission-self-review.md` is in its Expected Surface
  (added 2026-08-23 for **DC**), and **DC is thematically adjacent to this plan's core**: DC governs
  *"a self-review round may FILE only on checked evidence but may DISMISS on any premise it likes"* —
  **the evidence standard for dismissal**; this plan governs **who decides the loop may stop**. Both are
  *the self-review judging itself*. ⛔ **They must not be answered independently**, and `-097` is
  already above the split guard, so this was staged separately rather than folded.
- ⚠ **`PLAN-TRUTH-106` / `PLAN-TRUTH-107`** also touch `phase-6-finalize`. `-107` D5's *honest stop*
  and this plan's stop question are different subjects — one is a runner yielding control, the other a
  verifier answering whether work remains — but **confirm at emit time that D2's vocabulary does not
  collide with `-107` D1's named-yield set.**
- **Depends on:** nothing hard.

## Claim Labels

- OBSERVED: `pre-submission-self-review.md` names the converged-vs-out-of-budget distinction explicitly and forbids collapsing them — read at that file § the termination-criterion block, so the audit's "missing non-converging signal" claim is refuted.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:504-521 keeps converged, out-of-budget and not-run explicitly distinct; MUST NOT collapse language present
- OBSERVED: the same file's cohort-sweep obligation requires filing every member of a `defect_class` in the same round — read at § "the obligation", which is the remedy for the lane's n−1-of-n diagnosis.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:252,367,431 cohort_size plus class-closure obligation requires filing every same-class member in the same round
- OBSERVED: the step is *"a deterministic helper that surfaces concrete candidates … with an LLM cognitive review applied"* in the finalize envelope — read at that file `:32`; no independence or blindness property appears anywhere in it.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:32-33 deterministic helper plus LLM cognitive review runs inside the same plan finalize envelope; no independence property stated
- OBSERVED: Step 4 Branch A closes on an empty findings list plus a full-surface precondition — an author-side mechanical evaluation, with no question put to a verifier.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-submission-self-review.md:387,250 Branch A closes on empty findings plus the full-surface precondition, author-side mechanical, no verifier question
- OBSERVED: the lane asks the stop question *"of the verifier here rather than decided by the author afterwards"*, with conditions A and B quoted and prior survivors listed — read at `.claude/skills/cloud-plan-lane/SKILL.md` § Step 6.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: cloud-plan-lane/SKILL.md:663 asked of the verifier here rather than decided by the -- verbatim
- OBSERVED: `doc/concepts/README.adoc` declares these pages *"short navigational summaries over the canonical specifications co-located with the code"* — which is why D3 is one clause and not a page.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: doc/concepts/README.adoc:11 short navigational summaries over the canonical specifications -- verbatim
- OBSERVED: `automatic-reviews.adoc` names structural self-review at `:14` and links the workflow at `:42`; `verification.adoc` does not mention it at all.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: automatic-reviews.adoc:14,42 name and link structural self-review; verification.adoc has zero self-review mentions
- HYPOTHESIS: a blind verifier is affordable within the step's existing budget — confirm/refute at D0 against a real run's figures (verify-at-outline). ⛔ **The one observed run cost 8 firings / 115 candidates / 20 findings; a blind re-review multiplies that.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Deferred to D0 against a real run firing and cost figures; not performed this pass
- HYPOTHESIS: plan-marshall has no A/B-equivalent forbid/permit taxonomy and one would have to be authored — confirm/refute at D0 against the findings-severity vocabulary and the Q-Gate disposition set (verify-at-outline). **If it must be authored, split it out.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Exhaustiveness claim (no A/B taxonomy exists) deferred to D0 sweep; not swept this pass
- Verify-first clause: D1/D2 must leave the delta/full scoping, the cohort sweep, `structural_limit` and the converged-vs-out-of-budget distinction untouched — they are shipped, correct, and this plan's whole premise is that only the CLOSE is self-assessed.

---
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause constraining D1/D2 untouched-surface scope

## Machine-derived collision map (2026-08-24, `corpus cross-check` — 156 specs)

⛔⛔ **`code-intelligence-substrate/PLAN-CIS-043` — CHECKED AT STAGING. Not a duplicate, but it
WEAKENS a claim this spec makes and D2 must be corrected for it.**

CIS-043 is *"The Self-Review Surface Over-Reports Its Own Coverage Three Ways"* — the **surfacing**
layer; this plan is **who decides the loop may stop**. Different subjects. ⭐ **But its arm A is
directly load-bearing against D2:**

> `_detect_count_prose` opens **only** `{skill_dir}/SKILL.md`, while its sibling
> `_collect_skill_contract_sources` in the same file returns *"SKILL.md plus every `standards/*.md`"*.
> ⇒ **The closing full-surface pass is not the backstop a reader assumes: "full surface" means the
> full FILE surface, not the full DETECTOR surface.**

⛔ **D2 above states that Branch A's full-surface precondition *"is a scope guarantee and remains
necessary."* That is TOO STRONG and must be softened at outline.** It remains necessary, but it is a
**file**-scope guarantee only — CIS-043 establishes that a candidate list can be blind to a whole
document class inside a "full" surface. ⇒ **D2's stop question is more load-bearing than this spec
first implied**, because the precondition it supplements is narrower than its name. ⚠ Do NOT fix
CIS-043's arms here; **serialize and consume its outcome.**

**Other machine-derived hits:** `PLAN-TRUTH-097` (1 file — the hard serialization already recorded) ·
`code-intelligence-substrate/PLAN-CIS-052` · `review-apparatus/PLAN-PR-030`. ⛔ Re-derive at emit time.

⭐ **A defect of this same family was drained from PLAN-TRUTH-095 and FORWARDED to CIS as
corroboration of arm A** (*the surfacer emits only `context: docstring` prose, so two copies of a
four-site over-claim were structurally invisible, and a delta over uncovered prose yields a
byte-identical candidate set*). **That is CIS's, not this plan's** — this plan neither fixes nor
re-derives it.

## Folded from the PLAN-TRUTH-088 drain (2026-08-24) — the loop's first YIELD measurement

⭐⭐ **This spec finally has a cost-and-yield number, and it cuts in the loop's favour.**
`pre-submission-self-review` fired **eight times** on `-088` (seven `failed`, one `done`), cost
**~1.4M tokens across 7 rounds**, and raised **9 real defects with ZERO false positives**. ⛔ **Do not
let D2's "the self-review decides its own close" framing slide into "the loop is too expensive"** —
these are different questions, and the only measurement we have says the yield is real. The open
question this spec owns is whether the loop's *own close decision* is trustworthy, not whether it
earns its cost.

**Inbox `-012` — the convergent remedy for an over-claiming sentence is DELETION, not correction.**
Of the nine findings, eight were `contract_drift` and one `same_document_contradiction`; in every
case the offending text was a sentence stating a count, a condition or a guarantee that the code no
longer supports. ⭐ The generalisation: a sentence that restates a fact the code already carries has
**no correct version** — corrected today, it drifts again on the next change. The remedy that
converges is removing the restatement and leaving one authority. ⇒ Feed this to the surfacer as a
**suggested disposition**, so the loop stops proposing rewrites of sentences that should not exist.

**Inbox `-013` — a defect class closed by INSTANCE COUNT left a third copy at the render site.**
The plan widened `_sequence_build_minimality_plan` from a denominator-only condition to
`has_ledger and wall_clock_seconds > 0`; the pre-change wording was restated in two places that were
found and fixed, and a **third copy survived at the render site**. ⛔ **This is the epic's
`a-reviewer's-list-of-call-sites-is-a-SAMPLE` rule reproduced inside a fix for exactly that class.**
The close criterion must be a **derived population** (every site that renders or restates the
condition), never "the instances the finding listed". ⇒ D-scope: the loop's close decision must name
the population it enumerated, which is the same obligation D2 already argues for — this is its
sharpest worked example.

## Folded from the PLAN-TRUTH-094 drain (2026-08-25) — inbox `-004`, the self-review half

⚠ **Scope note: only HALF of candidate-lesson `-004` folds here.** Its bot-split half (the manifest
marks the zero-yield bot REQUIRED and the twice-productive one OPTIONAL) is `review-apparatus`'s and
is already held there as `5bdbb9` in its own `plugin-doctor-detector-coverage-residue-001.md`. Do NOT
re-derive that half here; the routing rule gives PR/review reliability to that epic outright.

**The half that IS ours is the strongest available evidence for this spec's thesis.** PR #1343's
merge candidate had passed:

- a whole-tree quality gate — 37 rules, 0 issues
- 21,957 module tests
- a clean whole-tree plugin-doctor run
- **seventeen rounds of dispatched self-review, converging to two consecutive clean results**

An independent reader found a **correctness defect in shipped code** at that exact HEAD —
`_analyze_argument_naming.py` counting an undecided site as decided, introduced by the plan's own
commit `4ca2481a9`.

⛔⛔ **Seventeen rounds of the same reviewer architecture converged clean on a defect a DIFFERENT
reader found immediately.** That is the distinguishing-property-is-invisible claim demonstrated end to
end: the self-review's close carries no signal about whether an independent reader would agree, and
the run had no way to know the difference between "converged because it is clean" and "converged
because it is the same reader".

⭐ **The transferable consequence for this spec's deliverables:** convergence is not evidence of
correctness, so a `settle converged` row MUST NOT be renderable as a completeness claim. The count of
rounds is not the property that matters — reader INDEPENDENCE is — and nothing in the current output
distinguishes them.

⚠ **And the round count itself was reported in a way that hides the shape.** The finalize row reads
`settle converged: round 27 clean, 0 findings`, which is true. The series was
1, 8, 7, 4, 6, 9, 4, 1, 1, 1, 0, 2, 4, 3, **11**, 1, 0 — an 11-finding round at position 15, after a
zero at position 11. A single terminal-round figure cannot express that, and the dominant defect class
throughout was **a fix's own replacement text being the next round's defect**.

## ⭐ FOLDED 2026-08-27 (landing #1359) — re-run the class surfacer over the FIX's own diff

From the `PLAN-TRUTH-098` landing drain (message `-004`).

**Directive: re-run the class surfacer over a fix's own diff before closing a self-review round.**

⭐⭐ **The evidence from that run is decisive and is this plan's strongest argument:** **four separate
fixes each introduced a defect of the class they were fixing.** Five pre-submission self-review rounds
found **8 real defects** — while **three plugin-doctor passes and the whole-tree gate found 0**. ⛔ The
structural gates did not see this class at all, so "the gates are green" carried no information about
it.

⇒ A round that closes without re-surfacing its own edits is closing on the *previous* state of the
diff. This is the mechanical form of the corpus's standing observation that **a warning is not a
guard** — the round already knew the class; what it lacked was a re-check against what it had just
written.

## ⭐⭐ FOLDED 2026-08-27 (landing #1361) — a plan whose subject IS a defect class reproduced it FIVE times inside its own fixes

From the `PLAN-TRUTH-114` landing drain (candidate-lesson `-006`).

**The plan reproduced its own defect class five times, inside fixes for it — and each was caught by a
DIFFERENT mechanism:** pre-submission self-review, an operator-facing premise error, an external
reviewer (CodeRabbit), the plan's own fix agent, and CI.

⭐⭐ **The mechanism-diversity is the finding, and it is the sharpest argument this plan has.** Five
instances, five different catchers, **no single mechanism caught more than one** ⇒ **no one gate would
have found them**, and a self-review round that closes on its own verdict is closing over a class its
own arm demonstrably catches only a fifth of. ⚠ The lesson states this as **a floor over eight cited
records, not a partition** — do not read "five mechanisms" as an enumeration of the catch surface.

⇒ Reinforces this plan's existing fold (*re-run the class surfacer over the fix's own diff*): four of
the five were introduced **by a fix**, so the diff that needs re-surfacing is the remedy's, not the
original's.

⚠ **One of the five was an operator-facing premise error the PLAN supplied to the ORCHESTRATOR** — it
asserted the plan dir sits outside `resolve_main_anchored_path`'s six corpora when
`integrate_into_main` already resolved it through them. **The orchestrator's D0 decision was correct on
what it was told and wrong on the facts**, and self-review caught it downstream. ⇒ **A plan's report to
the orchestrator is an input this class can corrupt**, which is a catch surface this spec does not
currently model.

## ⭐ FOLDED 2026-09-03 — inbox drain (2 message(s))

- **`dual-homed-hook-install-renders-identically-001.md`** — *scope a self-review fix to the finding CLASS, not the instance it named.*

  **First-party cost split from PLAN-TRUTH-102’s own run (PR #1384):** `pre-submission-self-review` fired 5 times over 10 rounds and found 13 defects, **all genuine and all introduced by that diff**. Rounds 1-5 cost **896,644** tokens; rounds 6-10 cost **953,588** — *more, for fewer defects.* The step accounts for **1,850,232 tokens — 50.6% of the plan’s whole recorded dispatch spend** — for defects that never reached the PR. The rounds-6-to-10 block alone is 26.1% of the plan.

  ⭐ **Root cause:** a self-review finding names one file because that is where the surfacer matched; the fix is then scoped to the named file rather than to the class of documents sharing the claim. Rounds 6-10 were largely residue of the previous round’s own fixes, concentrated in **two symmetric `marshall-steward` menu docs** (`menu-enforcement-hook.md`, `menu-terminal-title.md`). Each round fixed the file the finding named; the next round found the sibling. Only at round 9 was a whole branch rewritten, and round 10 then showed the sibling still carrying the identical pair.

  ⭐⭐ **The class is already representable — the emission granularity is not.** `ext-self-review-plan-marshall` already surfaces *near-identical-hunk touched claims* and *duplicate-claimable keys*. The ask is: emit a candidate matching in N > 1 files **once**, as an N-member set carrying every member path, instead of N independent candidates; and state in `pre-submission-self-review.md` that a finding carrying more than one member path is fixed and re-checked **across the whole member set in the same round** — a fix that closes one member and leaves siblings open does not close the finding.

  ⚠ **The saving figure is an ESTIMATE, not a measurement**, and the sender labels it so: uniform per-round cost ⇒ closing at round 7 instead of round 10 saves roughly 3 × 190,718 = **572,154 tokens (~15.6% of the plan)**. Do not publish it as measured.

- **`dual-homed-hook-install-renders-identically-002.md`** — *do not close self-review on the round type with a 100% residue-hit rate.*

  The step closed `outcome: done` after round 10 found one defect, which was fixed. **No round 11 ran, so no clean round confirmed the closure.** ⭐ The deviation was recorded honestly in the step’s own `display_detail` — *“13 fixed over 10 rounds; final sibling deletion not re-reviewed”* — a deliberate, visible departure from Branch A’s clean-round precondition rather than a silent one.

  ⛔ **What makes it a defect is WHERE the closure was taken.** Every round from 6 to 10 had found residue of the previous round’s fix: **a 5-of-5 residue-hit rate.** The step stopped at exactly the point where the observed probability of further residue was at its maximum, on the strength of a fix that had never been re-examined.

  ⚠ **It did not in fact leak** — a post-merge check of the two menu docs at HEAD found no residual defect on the surface inspected. **That is a spot check of two files, not a proof, and it does not retire the rule.**

  **Root cause:** the clean-round precondition is a step-level rule, but the decision to close is taken with the round-level history in view and **no rule that reads it**. A run whose recent rounds all found residue and one whose recent rounds were all clean face the same precondition and the same override cost. The ask: make the closure rule **history-sensitive** — when the previous K rounds each found at least one defect the precondition is not waivable; when recent rounds were already clean the existing waiver is unchanged — and **record the residue-hit rate alongside the round count in `display_detail`**, so the closure’s risk is legible in the status record instead of only in prose.

## ⭐ FOLDED 2026-09-04 — inbox drain (2 message(s))

- **`documented-invocations-...-007`** — *finalize outspent every other phase combined on a bug-fix plan, and the largest term is this step.* `6-finalize` at **3,011,257** tokens exceeds all five other phases combined (2,833,784); `max_phase_token_share` 0.52; the plan crossed its 2.0M `multi_module + bug_fix` ERROR anchor by **2.9×**. ⛔⛔ **`pre-submission-self-review` fired FIVE times** (`prior_firings: [failed, failed, failed, done]`, current `done`); **the three failures account for `error_total_tokens: 737,877` — 12.6% of the plan’s ENTIRE spend — with `retryable_total_tokens: 0`, so NONE of it is infrastructure a re-run would have recovered.** ⭐ **The ask is a bounded failure budget with a distinguishable terminal state, so the third identical failure ESCALATES instead of re-firing** — *“a step that can fail three times before succeeding is spending most of its budget on rounds that return nothing.”* ⚠ Two independent contributors ride alongside and must not be conflated with it: the loop-back re-fired the whole settle band (five steps at `firing_count >= 2`), and **75,518 stale temp files / 714 MB of pytest residue inflated a `module-tests` run 1,519s → 740s after the sweep.**

- **`documented-invocations-...-014`** — *the defect class a plan exists to close recurred inside that plan’s own change — three times, and one instance was authored by the FIX for an earlier one.* **(1)** Q-Gate `b76f9f`: after the `toon_parser` delegation the outer-quote guard stopped firing, so input reached the intent-marker validator and was rejected **for the wrong reason** — the finding’s own words: *“the rejection is real but names the wrong cause, sending a caller to add an intent marker when the actual problem is the outer quoting.”* **(2)** CodeRabbit `74cb2d` (Major): the finalize step’s parse table named three TOON fields `generate.py` never emits — **and the pre-existing contract test restated the same wrong claim rather than catching it.** **(3)** Q-Gate `861e68`, verbatim: *“This prose was authored by THIS ROUND’s fix for `f5dbc5`, so it is a self-seeded doc claim.”* Round 1 widened prose to state both guard conjuncts; round 2 found it over-claimed (it ranged over `steps`, `skills` and `verification.commands` while `_build_task_record` makes exactly **two** guard calls — `skills` is never guarded).

  ⭐⭐ **Two rules, and the second is the sharper one.** *A fix for a contract-drift finding is itself a contract claim* and must be re-derived against the code it describes, not against the finding’s narrative — **`861e68` was caught ONLY because a second self-review round ran; a plan whose settle band fires once would have shipped it.** And: **when a plan’s subject IS a defect class, that class is the highest-prior candidate for its own diff.** All three were caught — by module tests, by CodeRabbit, by round-2 self-review — **but none by a check that knew what the plan was about.** A pre-submission pass that reads the plan’s own defect class and sweeps the diff for it would have been aimed correctly by construction.

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

**Theme 3's family-scope findings fold here — the review unit is the family, not the diff.**

⛔⛔ **§3.1 is the theme's thesis and it is measured: THREE OF SIX post-implementation findings were places the plan did NOT change but should have** — the one `resolve*` method not receiving a new argument while every sibling did; the one parser not validating bracket contents while its sibling always had; the user guide not updated alongside the Javadoc enumerating the same fields. ⭐ **Two security audits and a self-review passed all three — each CORRECT that what changed was correct.**

> **When a change makes one member of a family stricter, the review unit is the whole family.** Enumerate the family — siblings by name prefix, siblings by shared parser, the doc surface enumerating the same field set — and for each member **not** in the diff, state why it does not need the same treatment. **An unexplained absent member is a finding, not a non-event.**

⭐ **This is the same shape as this spec's existing `dual-homed-...-001` fold** (a fix scoped to the instance a finding named rather than the class), reached from the opposite direction: there the class was rediscovered round after round; here it was never looked for at all. **One remedy serves both — emit the family, not the member.**

- **§3.3 — a landed fix is a search key, not a closed ticket.** Two cache-eviction gaps **four lines apart, in adjacent branches of the same `if`**, found a review round apart; fixing the first did not trigger a search for the second. ⛔⛔ **The deeper half is a shared blind spot: neither was visible to the tests, both times for the same reason** — a converter that *never* returns `Optional.empty()`, so **no test built on it can exercise the conversion-failure path at all.** ⇒ *"The remediation INHERITED the fixture blind spot that caused the original defect."* ⭐ **A fixture that cannot represent a failure mode makes every defect in that mode invisible, INCLUDING defects in the code written to fix that mode** — so the fixture gap must be closed **first, as part of the remediation.** (The fixture half also reinforces `PLAN-TRUTH-116`.)

- **§3.4 — a justification's scope must match the annotation's scope.** A **class-level** `@SuppressWarnings` was removed on the grounds that a **public accessor's** type change made the rule inapplicable. The private helpers the same annotation covered still had the triggering shape; **8 Sonar issues surfaced and needed a loop-back.** ⇒ **a class-level suppression needs a class-wide justification — enumerate every site the suppression covered, not only the site that motivated the removal.**

- **§3.5 — a change that distinguishes two states must enumerate every way the code COLLAPSES them.** A deliverable existed to close a fail-open when two header families disagree. The implementation failed closed on disagreement **and reopened the same fail-open inside itself**: the parser mapped *"header present but rejected"* onto the same empty value as *"header absent"*, so the distinguishing logic downstream could not see it. ⛔ **The data has THREE states — absent, present-and-valid, present-and-invalid — and a return type expressing only two silently re-introduces the fail-open.** ⚠ **A security audit reviewing the distinguishing logic PASSES, because that logic is correct; the defect is in what it is HANDED.**

## ⭐⭐⭐ FOLDED 2026-09-05 — lessons-handling drain (1 message), and it is CORROBORATED BY THIS EPIC'S OWN SHIPPED RECORD

- **`lessons-handling-26-09-04-01-010`** — *self-review should treat "the same refactor applied to N−1 of
  N sibling sites" as a FIRST-CLASS candidate class, including for control-flow edits.*

  ⭐⭐⭐ **The n−1-of-n pattern is this epic's single most-recurrent defect archetype and it does not need
  arguing — it is measured.** `PLAN-TRUTH-075`'s own n−1-of-n guard **reproduced n−1-of-n four times
  inside itself** across five rounds, each a level deeper (glob pinned at 2 of 4 sites ▸ population check
  was mere non-emptiness ▸ skip row bound positionally while the docstring claimed semantic ▸ the REPORT
  surface still bound positionally). `PLAN-TRUTH-055` did the same. ⇒ **This is not a proposed heuristic;
  it is the class most likely to survive a clean self-review.**

  ⛔⛔ **The "including control-flow edits" qualifier is the load-bearing half, and it is where the
  candidate surfacer is weakest.** A textual sibling sweep finds a renamed symbol at N−1 sites; a
  control-flow edit (a narrowed guard, a moved early return, a changed catch scope) has no textual twin
  to match on, so the class the qualifier names is precisely the class the current surfacer cannot see.
  ⚠ **Recorded already at a different seam**: when a delta's whole content is uncovered prose, the
  candidate set is byte-identical to the previous round's and a clean verdict certifies nothing. **Same
  failure — a candidate list blind to a whole content class inside a surface called "full."**

  ⭐ **This plan's own subject is the reason it lands here**: an N−1-of-N gap is invisible in a
  self-review that decides its own close, because the closing verdict reports what it examined and not
  what it could not see. ⇒ **The candidate class and the close criterion must ship together**; adding the
  class to a self-review that still grades itself just moves the blind spot one step later.

## ⭐⭐⭐ FOLDED 2026-09-05 — PLAN-TRUTH-093 drain (1 message)

- **`preference-admissibility-...-006`** — *the two review instruments split one defect family by WHICH
  SIDE is wrong, so a clean self-review is not evidence the code is.*

  ⛔⛔ **This is the sharpest statement yet of why a self-decided close cannot be trusted, and it is
  structural rather than motivational.** The partition is not by severity or by area — it is by *which
  side of a doc↔code divergence is at fault*. One instrument owns "the code is wrong"; the other owns
  "the doc is wrong". **Neither owns "they disagree."** ⇒ A clean verdict from either says only *"nothing
  in MY half"*, and the union is never taken, so **a divergence can pass both instruments while every
  individual verdict is honest.**

  ⭐⭐ **It strengthens this spec's D-line directly**: the close criterion cannot be "my checks found
  nothing", because the defect class most likely to survive is the one **no instrument is scoped to
  own**. A self-review that reports its own scope alongside its verdict makes that gap visible; one that
  reports only the verdict cannot. ⇒ **The scope declaration IS the deliverable**, not a nicety attached
  to it.

  ⚠ **Pairs with the fold above** (`lessons-handling-...-010`, the N−1-of-N candidate class): that one is
  a class the surfacer cannot SEE; this one is a class no instrument OWNS. **Different causes, same
  invisible residue, and a fix for either leaves the other.** ⚠ Expected Surface unchanged: adds no file
  surface.

## ⛔⛔⛔ FOLDED 2026-09-05 (c) — PLAN-TRUTH-089 drain (1 message). THE SPEC'S TITLE, MEASURED AT THE CEILING.

- **`planning-lane-...-002`** — *a round loop closed at its iteration ceiling records the same `done` as a
  converged one.*

  **This is the spec's subject with the numbers attached.** `pre-submission-self-review` fired **19
  times**; fifteen returned `loop_back`, and `status.metadata.loop_back_iteration` reached **17 against
  `max_iterations: 17` — the ceiling FULLY consumed.** ⛔ The last closes were therefore **not
  convergence**, and the step's stored record spells them `outcome: done`, **byte-identical to the record
  a genuinely converged round writes.**

  ⛔⛔ **The final `display_detail` reads *"agent stalled before filing, findings NOT recorded"* — a
  partial round — and it is STILL stored under `done`.** So the conflation is not merely
  converged-vs-exhausted; a round that produced no record at all also lands there.

  **Root cause is a vocabulary gap, not a logic error:** `mark-step-done --outcome` offers
  `done` / `skipped` / `loop_back` / `failed`. **There is no value, and no companion field, for *"the loop
  stopped because it ran out of iterations."*** Every terminal path — converged clean, converged with the
  last findings accepted, and budget-exhausted — lands on `done`.

  ⭐⭐ **The plan's own finding `28e6e8` names the distinction WHILE FIXING A DIFFERENT INSTANCE OF IT**:
  an unresolved `{sha}` in Branch C created *"a wedge only `max_iterations` breaks, closing the step OUT
  OF BUDGET rather than converged, which is the exact distinction the round-loop termination rule exists
  to protect."* ⇒ **The rule exists. The ledger that would carry its outcome does not.** That gap is this
  spec's D-line, and it now has a measured instance rather than an argued one.

  ⚠ **Expected Surface widened in this same act**:
  `marketplace/bundles/plan-marshall/skills/manage-status/**` — the `--outcome` value set and any
  companion field — and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
  — the round-loop termination rule's recorded outcome (HYPOTHESIS, verify-at-outline).

## ⛔⛔⛔ FOLDED 2026-09-07 — PLAN-TRUTH-128 drain. THE HEADLINE INSTANCE, AND A CANDIDATE CAUSE ARRIVING IN THE SAME DRAIN.

### `freshness-gate-...-001` — self-review matched 0 of 75 candidates against shapes IT ALREADY DECLARES

`pre-submission-self-review` fired **8 times** (3 recorded `loop_back`) and closed
`self-review clean: 75 candidates examined, no check matched`. **CodeRabbit then filed 9 actionable
items against the same diff, four of them in classes this gate already declares** — `same-document
normative directives`, `producer-consumer pairs`, `source-of-truth duplicates`, `contract sources`.
**Two of the nine were genuine fail-open contract defects** — precisely the class the gate exists to
catch before a reviewer sees it.

⛔⛔ **This is NOT a vacuous run over an empty population, and that is what makes it this spec's
subject rather than `-104`'s.** 75 candidates were surfaced. The gate examined the right population,
applied the right classes, and **still returned clean while a downstream reviewer found four instances
of those same classes.** ⇒ **A verdict its checks did not earn.**

⭐⭐⭐ **The sender's sharpest observation, and it inverts a discipline this epic promotes:**
*"`75 candidates examined, no check matched` reads as thoroughness and is the reason nobody looked
further: it publishes the population size — the discipline this epic asks for — and then draws the
wrong reassurance from it."* ⇒ **Publishing the population is necessary and NOT sufficient.** A stated
denominator over an unearned verdict is more persuasive than a bare one, not less.

**Its three proposed actions are adopted into this spec's D-line:**
1. **Turn each of the four escaped findings into a FIXTURE for the class it should have matched.**
   ⛔ *A class with no failing fixture is a class with no evidence it can fire.*
2. **Establish, per class, whether the class has EVER fired on any corpus.** ⛔ *A class that has never
   matched in production is indistinguishable from an unimplemented one, and the aggregate
   `no check matched` hides which of the two it is.*
3. **Make the terminal display distinguish *no candidate matched any check* from *k of N checks are
   known-live*.** ⛔ *`75 candidates examined, no check matched` must not be renderable when the
   live-check count is unknown.*

### ⭐⭐⭐ A CANDIDATE CAUSE ARRIVED IN THE SAME DRAIN, FROM A DIFFERENT PLAN — `arm-the-refusal-...-001` item 2

`pre-submission-self-review.md:133-143` invokes the surfacer with **NO `--base-branch`**, in both the
full and the delta form. **Verified first-party**: `self_review.py surface` declares
`--base-branch BASE_BRANCH  Base branch for diff computation (default: main)` — **local `main`.**

⛔ **On any plan rebased onto `origin/main` by `finalize-step-sync-baseline` (order 3), local `main`
lags**, so the diff absorbs upstream the plan never touched. The reporting run measured
**`files_in_scope: 136` against a real diff of 21 — roughly 6×, ~115 absorbed files.**

⚠ **HYPOTHESIS, and it must be tested rather than assumed: the over-scope is a candidate CAUSE of the
0-of-75 result.** A candidate set dominated by absorbed upstream would dilute the genuinely changed
files. ⛔ **The sender of `-001` reasoned the opposite** — *"that is not a run over an empty population,
so the failure is in the matching, not in candidate enumeration."* **Both can be true**, and they have
different fixes. ⇒ **NAMED TEST: re-run the surfacer on PR #1425's branch WITH `--base-branch
origin/main` and compare `files_in_scope` and the candidate mix against the recorded 75.** If the
candidate set collapses toward the 21 real files, enumeration is implicated; if the four escaped classes
still fail to match over the narrowed set, the matching is.

⚠ **Expected Surface widened in this same act**:
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
— the Step 1 surfacer invocation — and
`marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — the class
fixtures and the terminal display (HYPOTHESIS, verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-148-the-finalize-step-contract-declared-surfaces-the-dispatch-seam-and-a-self-review-that-decides-its-own-close.md` (PLAN-TRUTH-148)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
