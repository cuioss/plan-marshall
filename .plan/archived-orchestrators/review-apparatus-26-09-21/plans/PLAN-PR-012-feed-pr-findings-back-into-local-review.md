# PLAN-PR-012: Could we have found it ourselves? — back-feed accepted PR findings into the local review

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

For each PR finding we **accepted**, ask one question:

> **Could we have found it ourselves?**

Where the answer is yes, add the small detector to the plan-local review that would have surfaced it.
That is the whole plan.

## The precondition — the POSTED ANSWER is the signal

The automatic-review workflow is instructed to **always post an answer** to a finding: `post_responses`
transmits the triage disposition and its rationale back to the PR as a thread reply (then resolves the
thread), or as one batched PR-level comment for genuinely threadless kinds. **That posted answer is the
signal, and it says whether we accepted the finding.**

⛔ **Do NOT key the corpus off the findings ledger's internal resolutions** (`fixed` / `accepted` /
`taken_into_account` / `rejected` / `suppressed` / `pending`). Those are our own claim about ourselves.
The posted reply is the observable — read it via `ci pr comments --pr-number {N}`, the same evidence
standard this epic applies everywhere else.

⭐ **A MISSING answer is itself a finding — never a silent exclusion.** A finding with no posted answer
is a defect in the response path and is REPORTED as one, not dropped from the corpus. Two known
producers: a thread-bearing finding whose thread is missing is reported **`untransmitted`** (never
batched, by design), and **`skipped`** is specified to fire "only when there is genuinely nothing to
say" — so an unjustified `skipped` is the same defect wearing a success label. ⚠ **Treating an
unanswered finding as noise would hide exactly the failure this epic exists to catch.**

## ⚠ The third answer: "yes — but it was not running"

The local review also includes the **security audit** (`default:finalize-step-security-audit`), which is
**conditionally active**: on plan-marshall it is a tier-`full` lane element, so lane `auto` **drops** it
and it runs only at lane `full`. (On API-Sheriff it is active in most cases — relevant because the same
accepted finding can answer differently per project.)

So a security finding may be a **yes-but-it-was-not-running** — an **activation question, not a detector
gap**. ⛔ **Do not add a detector to compensate for a check that was simply switched off.** That gives
the local review a second, weaker copy of something it already has, which is worse than either.

**Verify against the archived plan; do not infer the lane.** The archived plan's execution manifest
carries the answer, and there are **two independent drop paths — check BOTH**:

1. `execution_profile` / `lane_dropped` — the lane tier dropped it (`auto` drops tier-`full`);
2. `security_class_omitted` — the **ceremony pre-filter** dropped it, as `{step, reason}` records. This
   path is separate from the lane, so checking only the lane would miss it and misreport an inactive
   check as a detector gap.

## Deliverables

1. **D1 — GATE (mutates nothing): ask the question over the answered-finding corpus.** Read the posted
   answers off the PR, and for each finding we accepted, answer yes or no — for a yes, name the detector
   that would have caught it. **Report separately any finding with NO posted answer**: that is a
   response-path defect, and it is a finding of this exercise rather than an omission from it.
   ⛔ **Answer "no" for anything that needed reading the code and reasoning about intent** — that is the
   bot's job and re-implementing it locally would be slower and worse. A finding the local pass already
   raised is a trivial yes-we-did, and yields nothing. ⚠ **A security finding takes the third answer
   below — resolve it there, not here.**
2. **D2 — add the detectors for the yes answers**, each one function in the existing
   `_detect_*(added, …) -> list[dict[str, Any]]` shape in `ext-self-review-plan-marshall`.

   ⭐ **D2 has a SECOND arm, discovered 2026-07-30 and not anticipated when this spec was written:
   WIDENING an existing detector, rather than adding one.** The first real back-feed case resolved to
   neither "yes, add a detector" nor "no, semantic" nor "the check was switched off" — the detector
   **exists, ran, and its predicate was simply too narrow**. ⛔ **Do not answer such a case by writing a
   second detector beside the first**; that is how the local review acquires two overlapping copies of
   one check. Widen the existing one and say so.

   **The motivating case, orchestrator-verified against source** (`#1067` finding `835226`, *"one of
   those nine"* against a list of eleven):
   - `_detect_count_prose` exists in `_self_review_detectors.py:1019`.
   - ⛔ It scans **only `SKILL.md`** files, and only within the skill directory of a modified file — so
     count-prose in a `standards/*.md`, an ADR, or a concepts doc is invisible to it.
   - ⛔ Its predicate is `_COUNT_PROSE` over a **closed five-noun set**:
     `_CARDINALITY_NOUNS = 'operations?|fields?|steps?|rules?|commands?'`. A count against any other
     noun does not match.
   - ⭐ **Its own docstring comment is WRONG, and wrong in this exact archetype**: it claims
     *"``twelve fields``, ``5 rules``, ``nine checks`` are matched"* — but `checks` is **not** in
     `_CARDINALITY_NOUNS`, so `nine checks` is NOT matched. **The count-prose detector's documentation
     is itself an unverified count claim contradicted by its own code.** Fix this as part of D2; it is
     the cheapest possible demonstration of why the check exists.
   ⚠ **Widening must be DERIVED, not guessed.** Do not widen to "any noun" — that trades a narrow
   predicate for a noisy one and trips the stop rule below. Derive the noun set from the counts that
   actually appear in the corpus, and state whether the resulting set is closed.
3. **D3 — tests, each verified to FAIL pre-fix**: per new detector, one positive case drawn from the
   real accepted finding that motivated it, plus one negative case proving it does not fire on the
   adjacent shape it would most plausibly over-match.

Three deliverables. ⚠ **Expect a small yield — plausibly two or three detectors.** A large yield means
the question was answered too generously at D1, not that a goldmine was found.

## ⛔ The stop rule — structural, not a judgement call

Every existing detector is a scan over the diff's added lines plus at most a bounded already-available
context read. **A candidate that does not fit that shape is out of scope.** Concretely, reject any
candidate needing:

- cross-run or cross-plan state, or history beyond the current diff;
- a new configuration knob;
- semantic judgement about whether prose or logic is *correct* (as opposed to *structurally
  inconsistent*);
- a new bundle, skill, standard, or extension point.

⭐ **Reaching for a complex rule is the signal that the candidate does not belong here at all — not a
signal to write it carefully.** When a candidate needs any of the above, record it as a finding for the
epic and move on.

## Claim Labels

- OBSERVED: `post_responses` transmits an already-decided disposition plus its rationale
  (`resolution_detail`) back to the PR, via a three-way transmit keyed on the finding's `kind` —
  thread-reply-then-resolve for a thread-bearing finding, ONE batched PR-level comment for the
  genuinely threadless kinds (`review_body`, `issue_comment`), and `skipped` "only when there is
  genuinely nothing to say". A thread-bearing finding whose thread is missing is reported
  **`untransmitted`, never batched.** Read at
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`. **These two states
  are the named producers of a missing answer.**
- ⚠ OBSERVED (a trap for the corpus read): `fetch_findings` deliberately drops any comment whose body
  **starts with** the batched-response heading, counting it as `count_skipped_self_response`, so our
  own posted answers do not re-enter as findings. **When reading the posted answers for D1, that same
  batched comment IS the artifact being read** — do not mistake the self-response filter for evidence
  that no answer was posted. The match is start-anchored, so a human comment quoting the heading is
  still a real finding.
- OBSERVED: `ext-self-review-plan-marshall/scripts/_self_review_detectors.py` implements ~18 detectors
  as `_detect_*` functions over the diff's added lines (`_detect_regexes`, `_detect_user_facing_strings`,
  `_detect_markdown_sections`, `_detect_contract_sources`, `_detect_keep_markers`,
  `_detect_symmetric_pairs`, `_detect_flag_guard_pairs`, `_detect_producer_consumer`,
  `_detect_source_of_truth`, `_detect_same_document_consistency`, `_detect_description_vs_body`,
  `_detect_unguarded_boundaries`, `_detect_count_prose`, `_detect_ordinal_references`,
  `_detect_touched_claims`, `_detect_advertised_form_help_strings`, `_detect_scan_derived_keys`, …).
  **This registry is the unit of change.**
- OBSERVED (a likely first candidate pair): on `#1039` every local gate passed and CodeRabbit still
  found two real defects — a negative `--max-per-component` producing a spuriously truncated result,
  and a duplicated disposition table. Both look mechanically recognisable. ⚠ **Confirm they were
  ACCEPTED before using them** — this spec asserts they were real, not that the ledger recorded them as
  accepted.
- OBSERVED: `security-audit` is a tier-`full` lane element and lane `auto` drops it; the composer
  reports drops through `execution_profile` / `lane_dropped` (lane path) and `security_class_omitted`
  as `{step, reason}` records (ceremony pre-filter path) — read at
  `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` § lane resolution.
  **Two producers, two drop paths.**
- HYPOTHESIS (asserted absence, per candidate): no existing detector already covers the shape —
  confirm/refute against the registry above (verify-at-outline). **Verify each one**: duplicating an
  existing detector under a new name is the cheapest way for this plan to do harm.
- Verify-first clause: re-read the registry at HEAD before scoping. The detector list is actively
  grown, and a shape this plan means to add may already have landed.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
  — the detector registry, and the primary (likely only) production surface.
- HYPOTHESIS: `.../ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — if a candidate is
  pattern-shaped rather than logic-shaped (verify-at-outline).
- HYPOTHESIS: `.../ext-self-review-plan-marshall/SKILL.md` — the advertised candidate-class list, if
  adding a detector changes it (verify-at-outline).
- OBSERVED: the `ext-self-review-plan-marshall` tests.
- OBSERVED (absence): `finalize-step-simplify` is NOT expected to be edited — it is quality-only and
  does not hunt defects. If D1 concludes otherwise, say so explicitly rather than quietly widening.

## Dependencies and Sequencing

- Depends on: none. The accepted-finding corpus already exists.
- Overlaps with: ⚠ **PLAN-PR-011** — its D4 makes the review-versus-gate delta a *measured* signal;
  this plan *acts* on it. ⛔ Complementary, and neither absorbs the other.
- Overlaps with: nothing else. This surface (`pm-plugin-development` self-review) is disjoint from the
  participation classifier (WS-01), `branch-cleanup.md` (WS-04), and both config repos.
- Adjacent to: `plugin-doctor`, the *other* deterministic local gate. ⛔ **Out of scope** — a finding
  better served by a plugin-doctor rule is recorded as such and left for a separate plan, not bolted
  onto self-review because that is the file already open.

## ⛔⛔ ABSORBED 2026-08-08 — a REJECTED review clause is held to a LOWER evidence standard than an accepted one

Sources: `truthful-signals-020` item 29; C05 lesson `2026-08-03-14-007`. ⛔ **LEADS, NOT FACTS.**

**Item 29 — the asymmetry.** The disposition flow requires a *rationale* for rejecting a reviewer's
clause, but not a *source*. So "disagree, here is my reasoning" is a COMPLETE disposition, while the
reviewer's own citation is discarded unread. ⇒ **the cheapest path through the flow is the one that
never reads the evidence** — and rejection is exactly where reading it matters most, because a rejected
finding leaves no other trace. Observed cost: two wrong rejections of the same reviewer on the same
false premise, and one of them is still the public record on that PR.

⭐ **Why this belongs to THIS plan rather than to the response-transmission plans.** The feedback path
this plan builds carries review findings back into local review. **A finding rejected on an unsourced
rationale is a finding this plan will feed back as noise, or drop entirely** — the back-feed inherits
whatever the disposition flow decided, so an asymmetric evidence bar upstream silently degrades the
corpus downstream. The remedy shape is the epic's standing one: a disposition that *rejects* must cite
the artifact that settles it, at the same standard the epic already requires of an absence claim. This
is the verify-first contract's symmetry clause — an asserted absence of merit is verified exactly as an
asserted presence — arriving at the triage boundary.

**C05 lesson `2026-08-03-14-007`** — the triage leaf **writes tests it structurally cannot run**, with
CI as the only covering gate. ⚠ Folded here with an explicit caveat from its own routing note: this is
about the triage leaf's **executability**, not about the feedback path. It is adjacent, not central. If
outline finds it wants a different owner (the leaf's tool envelope rather than the back-feed), say so
and route it out rather than absorbing it because this is the file already open — the same discipline
this spec's own Sequencing section applies to plugin-doctor findings.

- HYPOTHESIS (verify-at-outline): that OUR disposition flow requires no source on a rejection.
  Confirm/refute artifact: the rejection/dismissal disposition path in `manage-findings` and the
  `ext-triage-{domain}` contract — read what the disposition record REQUIRES, not what the triage
  guidance recommends.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-012-feed-pr-findings-back-into-local-review.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
