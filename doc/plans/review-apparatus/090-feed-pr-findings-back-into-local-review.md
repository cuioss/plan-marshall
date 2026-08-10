> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Could we have found it ourselves? — back-feed accepted PR findings into the local review

**Epic:** review-apparatus
**Branch prefix:** feature

## Problem

For each PR finding we **accepted**, one question goes unasked:

> **Could we have found it ourselves?**

Where the answer is yes, the local review is missing a small detector that would have surfaced it
before a reviewer had to. That is the whole plan — a narrow, high-yield exercise, not a redesign.

**The precondition: the POSTED ANSWER is the signal.** The review workflow always posts an answer to a
finding — a thread reply carrying the triage disposition and its rationale (then resolving the thread),
or one batched PR-level comment for genuinely threadless kinds. **That posted answer says whether we
accepted the finding.**

⛔ **Do NOT key the corpus off the findings ledger's internal resolutions** (`fixed` / `accepted` /
`taken_into_account` / `rejected` / `suppressed` / `pending`). Those are **our own claim about
ourselves**. The posted reply is the observable — read it from the PR, the same evidence standard this
epic applies everywhere else.

⭐ **A MISSING answer is itself a finding — never a silent exclusion.** A finding with no posted answer
is a defect in the response path and is **reported as one**, not dropped from the corpus. Two known
producers: a thread-bearing finding whose thread is missing is reported `untransmitted` (never batched,
by design), and `skipped` is specified to fire *"only when there is genuinely nothing to say"* — so an
unjustified `skipped` is the same defect wearing a success label. ⚠ **Treating an unanswered finding as
noise would hide exactly the failure this epic exists to catch.**

## Goal

The local review gains the small number of detectors that would have caught real, accepted PR findings —
and the exercise's by-products (unanswered findings, an over-narrow existing detector, an
evidence-standard asymmetry in triage) are recorded rather than absorbed.

## Deliverables

Three. ⚠ **Expect a small yield — plausibly two or three detectors.** A large yield means the question
was answered too generously at D0, not that a goldmine was found.

1. **D0 — GATE, mutates nothing: ask the question over the answered-finding corpus.** Read the posted
   answers off the PRs, and for each accepted finding answer yes or no. For a **yes**, name the detector
   that would have caught it. **Report separately every finding with NO posted answer** — that is a
   response-path defect and a *finding of this exercise*, not an omission from it.
   ⛔ **Answer "no" for anything that needed reading the code and reasoning about intent.** That is the
   reviewer's job, and re-implementing it locally would be slower and worse. A finding the local pass
   already raised is a trivial yes-we-did and yields nothing.
   ⛔ **This deliverable HALTS the plan** if the posted answers cannot be read from the PRs in this run's
   environment. Do **not** substitute the internal resolutions for them — that is the exact substitution
   the precondition forbids, and a corpus built on it would be our claim about ourselves.
   *Done when:* every accepted finding has a yes/no with a named detector for each yes, and the
   unanswered set is reported with its size.

2. **D1 — the third answer: "yes, but it was not running."** The local review includes a **security
   audit** that is **conditionally active** — in this repository it is a tier-`full` lane element, so the
   `auto` lane **drops** it and it runs only at lane `full`.
   ⇒ A security finding may be an **activation question, not a detector gap.** ⛔ **Do not add a detector
   to compensate for a check that was simply switched off.** That gives the local review a second,
   weaker copy of something it already has, which is worse than either.
   ⚠ **There are two independent drop paths and both must be checked**: the **lane tier** drop
   (`execution_profile` / `lane_dropped`), and the **ceremony pre-filter** drop
   (`security_class_omitted`, recorded as `{step, reason}`). Checking only the lane would miss the second
   and misreport an inactive check as a detector gap.
   ⛔ **Scope note for this lane:** determining what a *past* run's lane actually resolved to requires
   that run's execution manifest, which lives in a machine-local, git-ignored directory and is **not in
   your clone.** So D1 answers the *current-configuration* question — is the check active in this
   repository's resolved lane, and via which of the two paths could it be dropped — from the composer
   source, which **is** in your clone. **Record explicitly that the per-past-run lane verification was
   not available**, rather than inferring the lane.
   *Done when:* each security-shaped candidate is classified activation-question or detector-gap, with
   both drop paths named, and the unavailable per-run verification stated.

3. **D2 — add the detectors for the yes answers**, each one function in the existing
   `_detect_*(added, …) -> list[dict[str, Any]]` shape.
   ⭐ **D2 has a SECOND arm that is easy to miss: WIDENING an existing detector rather than adding one.**
   The first real back-feed case resolved to none of the three obvious answers — the detector **exists,
   ran, and its predicate was simply too narrow.** ⛔ **Do not answer such a case by writing a second
   detector beside the first**; that is how the local review acquires two overlapping copies of one
   check. **Widen the existing one and say so.**
   **The motivating case, verified against source:** the count-prose detector scans **only `SKILL.md`**
   files, and only within the skill directory of a modified file — so count prose in a `standards/*.md`,
   an ADR, or a concepts doc is invisible to it. Its predicate runs over a **closed five-noun set**
   (`operations` / `fields` / `steps` / `rules` / `commands`), so a count against any other noun does not
   match.
   ⭐⭐ **And its own docstring is wrong, in this exact archetype**: it claims *"`twelve fields`,
   `5 rules`, `nine checks` are matched"* — but `checks` **is not in the noun set**, so `nine checks` is
   NOT matched. **The count-prose detector's documentation is itself an unverified count claim
   contradicted by its own code.** ⇒ Fix this as part of D2; it is the cheapest possible demonstration of
   why the check exists.
   ⚠ **Widening must be DERIVED, not guessed.** Do not widen to "any noun" — that trades a narrow
   predicate for a noisy one and trips the stop rule below. **Derive the noun set from the counts that
   actually appear in the corpus, and state whether the resulting set is closed.**
   *Done when:* each yes has either a new detector or a justified widening, and the docstring
   contradiction is fixed.

4. **D3 — tests, each verified to FAIL pre-fix.** Per new or widened detector: one **positive** case
   drawn from the real accepted finding that motivated it, plus one **negative** case proving it does not
   fire on the adjacent shape it would most plausibly over-match.
   *Done when:* both cases exist per detector and each is proven discriminating by mutation.

## Out of scope — and the stop rule is structural, not a judgement call

Every existing detector is a scan over the diff's added lines plus at most a bounded, already-available
context read. **A candidate that does not fit that shape is out of scope.** Concretely, reject any
candidate needing:

- cross-run or cross-plan state, or history beyond the current diff;
- a new configuration knob;
- semantic judgement about whether prose or logic is *correct* (as opposed to *structurally
  inconsistent*);
- a new bundle, skill, standard, or extension point.

⭐ **Reaching for a complex rule is the signal that the candidate does not belong here at all — not a
signal to write it carefully.** When a candidate needs any of the above, **record it as a finding in the
run report and move on.**

Also out of scope:

- **`plugin-doctor`**, the other deterministic local gate. A finding better served by a plugin-doctor
  rule is **recorded as such and left for a separate plan**, not bolted onto self-review because that is
  the file already open.
- **The quality-only simplify step.** It does not hunt defects and is not expected to be edited. If D0
  concludes otherwise, **say so explicitly** rather than quietly widening.
- **Re-implementing the reviewer.** See the "no" rule in D0.

## Expected surface

- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
  — the detector registry and the primary (likely only) production surface.
- `.../ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — if a candidate is
  pattern-shaped rather than logic-shaped.
- `.../ext-self-review-plan-marshall/SKILL.md` — the advertised candidate-class list, if adding a
  detector changes it.
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` — **read-only**, for D1's
  two-drop-path question.
- The `ext-self-review-plan-marshall` tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The response path posts an answer per finding via a three-way transmit keyed on the finding's `kind`, with `untransmitted` and `skipped` as the two named producers of a missing answer | OBSERVED | `workflow-integration-github/SKILL.md` — read the transmit description and the two states |
| The count-prose detector is `SKILL.md`-scoped over a closed five-noun set, and its own docstring names a noun the set does not contain | OBSERVED | The detector function and its noun-set constant — read both, and compare against the docstring |
| The detector registry is the unit of change and holds roughly eighteen `_detect_*` functions | OBSERVED — ⚠ **the count is a lead** | Enumerate the registry at HEAD. ⛔ **Re-derive; the list is actively grown and a shape this plan means to add may already have landed** |
| The security audit is a tier-`full` lane element that the `auto` lane drops, with a second independent ceremony pre-filter drop path | OBSERVED | The lane resolution in the execution-manifest skill — **check both paths** |
| Two specific findings on one past PR (a negative `--max-per-component` producing a spuriously truncated result, and a duplicated disposition table) are mechanically recognisable first candidates | HYPOTHESIS | ⚠ **Confirm they were ACCEPTED before using them.** This plan asserts they were *real*, not that the ledger recorded them as accepted |
| No existing detector already covers a given candidate's shape (an asserted **absence**, per candidate) | HYPOTHESIS | The registry above. ⛔ **Verify each one — duplicating an existing detector under a new name is the cheapest way for this plan to do harm** |
| Our disposition flow requires a **rationale** but no **source** when rejecting a reviewer's clause | HYPOTHESIS — **a lead, not re-derived** | The rejection/dismissal disposition path in `manage-findings` and the triage-extension contract. ⛔ **Read what the disposition record REQUIRES, not what the triage guidance recommends** |

⚠ **A trap for the corpus read, worth knowing before D0.** The findings fetch deliberately drops any
comment whose body **starts with** the batched-response heading, counting it as a self-response, so our
own posted answers do not re-enter as findings. **When reading the posted answers for D0, that same
batched comment IS the artifact being read** — ⛔ do not mistake the self-response filter for evidence
that no answer was posted. The match is start-anchored, so a human comment quoting the heading is still
a real finding.

⛔ **Do not go looking for `.plan/`.** The archived plan directories, execution manifests, and inbox
messages referenced above are git-ignored and **absent from your clone** — which is exactly why D1 is
scoped to the current configuration rather than to a past run's lane.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D3 case proven discriminating by mutation.** The negative cases matter most: a detector that
  fires on the adjacent shape will be disabled by the first person it annoys, which costs more than
  never adding it.
- **Publish the corpus size, the yes count, the no count, and the unanswered count** in the run report.
  A back-feed exercise that reports only its yields hides its own selectivity.
- ⭐ **Cold read, aimed at the widened predicate.** D2 widens a detector's noun set. Have the pre-PR
  verification sub-agent read the widened detector's documentation **cold** and answer: *which count
  phrases does this match, and which does it not?* Then compare that answer against the code. If they
  disagree, the docstring defect this plan exists to demonstrate has been **reproduced by its own fix**.

## Notes

- ⛔⛔ **An asymmetry worth carrying, because it silently degrades this plan's own corpus.** The
  disposition flow requires a *rationale* for rejecting a reviewer's clause, but not a *source*. So
  *"disagree, here is my reasoning"* is a complete disposition while the reviewer's own citation is
  discarded unread. ⇒ **The cheapest path through the flow is the one that never reads the evidence** —
  and rejection is exactly where reading it matters most, because a rejected finding leaves no other
  trace. Observed cost: two wrong rejections of the same reviewer on the same false premise, one of
  which is still the public record on that PR.
  ⭐ **Why it belongs here**: the back-feed inherits whatever the disposition flow decided, so an
  asymmetric evidence bar upstream degrades the corpus downstream — a finding rejected on an unsourced
  rationale is one this plan feeds back as noise, or drops entirely. The remedy shape is the epic's
  standing one: **a disposition that rejects must cite the artifact that settles it**, at the same
  standard the epic already requires of an absence claim.
- **An adjacent lesson, deliberately not absorbed.** The triage leaf writes tests it structurally cannot
  run, with CI as the only covering gate. ⚠ That is about the **leaf's executability**, not about the
  feedback path. If the run finds it wants a different owner, **say so and route it out** rather than
  absorbing it because this is the file already open — the same discipline this plan applies to
  plugin-doctor findings.
- **Sequencing.** Nothing blocks it, and the surface is disjoint from the participation classifier, the
  merge path, and the CI abstraction — so this can run alongside most of the epic. ⚠ It **complements**
  another staged plan whose deliverable makes the review-versus-gate delta a *measured* signal; this one
  *acts* on it. ⛔ Neither absorbs the other.
