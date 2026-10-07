# PLAN-PR-011: Review bots catch what in-house gates structurally cannot, and nothing quantifies the residual

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — the REVIEW half of `truthful-signals` PLAN-60, split on operator decision

`truthful-signals` PLAN-60 (`in-house-gate-ci-parity`) was released to this epic on 2026-07-30 (row
`transferred` there). **The operator decided to split it**: only the review-apparatus half is staged
here. Its build-gate half — D2 (ruff `RUF` family in local `select=`, `mypy test` test-compile parity)
and D3 (gate footprint scoping: zero-scoped-modules branch, `marketplace/targets/**` root footprint) —
is **returned to `truthful-signals`** by inbox, because those are pure build-gate concerns with no
review-apparatus content. PLAN-60 also exceeded the split guard at 5 deliverables plus 10 carried
lessons, so the split serves both purposes.

⚠ **This spec does NOT carry PLAN-60's ten bound lessons.** The lessons split with the deliverables:
the two review-relevant ones are named below; the build-gate lessons return with D2/D3 and stay bound
there. **Do not carry a lesson this spec does not name.**

## Objective

A full green in-house sweep is not evidence of correctness, and today **nothing quantifies the
residual**. Close the two review-side coverage gaps where a local gate structurally cannot see what a
review bot does, and make the review-versus-gate delta a measured, recurring signal rather than an
anecdote — with the one confound that would invert the measurement handled explicitly.

## Deliverables

1. **D1 — GATE (mutates nothing): state what each gate structurally cannot evaluate.** For the gates in
   scope, name the analysis each performs and therefore what each cannot see. ⛔ **A gate whose green is
   scope-limited must say so in its verdict** — the defect is not that a gate is narrow, it is that a
   narrow gate's green reads as whole-tree assurance.
2. ⛔⛔ **D2 — PRESUMPTIVELY SHIPPED BY `#1118`. RE-VERIFY AND RE-SCOPE OR DROP BEFORE DESIGNING IT.**
   The original text follows so the re-scope can see what was intended — **do not implement it as
   written.**

   > **D2 — the automatic-review completeness guard distinguishes a structurally-absent bot from an
   > in-progress one** via a checks-status presence probe **before** `loop_back`. (Carries lesson
   > `2026-07-21-10-002`.) ⚠ **Coordinate with PLAN-PR-007**: that plan adds a `stale` taxonomy member on
   > the same classifier.

   **What changed (orchestrator-verified in merged main, 2026-08-08).** PLAN-PR-007 landed as **`#1118`**
   (`fddc4ec8b`), and it did more than add `stale`:

   - The taxonomy is now **seven closed members**, including `absent`, `in_progress`, **`not_triggered`**
     and **`participated_stale`** — and `bot-participation-contract.md` states each one's *distinct
     remedy*, which is the substance of "distinguish".
   - `#1118` added `workflow-integration-github/scripts/_github_checks.py` (+120 lines) carrying
     `_classify_check_buckets`, `_is_pull_request_event_run`, `_has_pull_request_event_run` and
     `_pull_request_event_runs_for_pr` — **an observable-keyed workflow-run presence probe**, which is
     the mechanism D2 proposed.
   - `review_completeness.py` (+131) now accounts for the widened member set.

   ⇒ **The absent/in-progress distinction D2 asked for is at minimum substantially built, and possibly
   complete.** ⛔ **Re-verify by reading `_github_checks.py` and the `loop_back` decision path against
   the seven-member contract BEFORE scoping.** If it is complete, **drop D2 and say so** — this epic's
   named failure mode is staging a plan for an already-landed fix. If a gap remains, scope only the gap
   and state precisely what `#1118` left open.

   ⚠ **The three-way coordination note is now HISTORY, not a constraint**: *absent* / *in-progress* /
   *stale* landed as one coherent set in `#1118`, exactly as the note asked. Do not re-open it.
3. **D3 — a same-run reconciliation contract between an automatic-review-committed line and
   `finalize-step-simplify` dead-code removal.** Honour the in-run reviewer commitment rather than
   ad-hoc judgement: if the review process committed to a line within a run, a later step in the same
   run must not silently remove it. (Carries lesson `2026-07-17-09-001`.)
4. **D4 — the review-versus-gate delta becomes a measured signal.** ⛔ **CONSUME PLAN-PR-006's D1
   counting rule; do NOT re-derive it** — see that spec § *D1 OWNS THE COUNTING RULE FOR THE WHOLE
   EPIC*. Three plans need per-reviewer finding counts and the epic keeps exactly one rule. "What did review catch that the
   gates did not" is the only direct read on parity we get, and **it arrives free on every PR.**
   ⛔ **The confound is load-bearing and must be handled in the measurement, not noted beside it:** the
   bots are frequently refusing (observed across at least four PRs), so an absence of review findings is
   often an absence of *review*, not of defects. **A parity metric that does not exclude PRs where the
   reviewer refused will report improving parity as coverage collapses.** That inversion is this epic's
   named failure mode, so a metric that can produce it must not ship.
5. **D5 — tests, each verified to FAIL pre-fix**, plus retirement of the two lessons this spec carries.

## ⭐⭐ ABSORBED 2026-08-08 (inbox drain) — a clean natural experiment: same diff, same day, six findings vs eight, ESSENTIALLY DISJOINT

Source: inbox `absent-names-two-states-with-opposite-remedies-006`. **First-party, PR #1118.** This is
the strongest evidence this plan has for its own thesis, and it arrived as a controlled comparison
rather than an impression.

**Self-review** ran three passes and produced six findings (`6fc38c`, `d26dd0`, `b0f7dc`, `d4ebf1`,
`64165f`, `92dd7c` — all `fixed`). **Every one is a documentation-consistency finding:** a
strictly-narrowing claim that was too broad, a sentence contradicting an instruction 29 lines above
it, three consumer docs asserting a retired five-member count, two sites calling the blocking subset
seven when it is six, one hard-coded guard population.

**CodeRabbit's FIRST review of the same diff** produced 8 actionable comments, four of them Major
(`212b88`, `dadd8a`, `a582b1`, `2690b3`, `b7e497`, `d66c05`, `308d72`, `7b5c4c`, `53a438`) — of a
different kind entirely:

- a binary read of a fallible observable coercing UNKNOWN into a positive (Major)
- a documented remedy with **no reachable invocation** — no verb, no outcome recording, no timeout
  branch (Major)
- an observable scoped to the head branch when its meaning is per-PR, so a reused branch suppresses
  the remedy (Major)
- a malformed-envelope path collapsing "never read" into "read empty", contradicting the function's
  own docstring
- a drift pivot shared by both sides of a count comparison, so the comparison stays green over a set
  missing a member (Major)

### The generalisable shape — this is the plan's thesis, stated precisely

**Self-review found internal inconsistencies between statements IN the diff. It did not find
behaviours of the code under inputs the diff does not contain.** Those are different search problems,
and this run separates them cleanly.

Two consequences this plan must carry:

1. ⛔⛔ **Self-review passing is not evidence the diff is sound.** Three green-ish passes preceded four
   Major findings. A run that reads self-review as a proxy for review quality will merge on that proxy
   **exactly when a bot is unavailable** — which is what then happened on this same run (see the
   empty-quorum absorption in PLAN-PR-008).
2. ⚠ **Self-review's own recurring hit is the hard-coded population**, and it caught one (pass 3) while
   missing two more CodeRabbit then found, plus one more found at 6-finalize. Five instances of one
   archetype in one PR, discovered by three different mechanisms.

**Candidate remedy (not applied):** do not let self-review passes converge on the class of finding the
previous pass produced. Passes 2 and 3 produced more of pass 1's class (count prose, then a guard
population) rather than reaching for the behavioural class. ⚠ **Whether that is a detector-coverage
gap or an attention-anchoring effect is worth deciding BEFORE adding detectors** — adding detectors
for the wrong one entrenches the anchoring.

## ✅ D2 IS SHIPPED — DROP IT. Verified 2026-08-09.

Orchestrator ground-truth pass, first-party against merged main. D2's proposed mechanism — a
checks-status presence probe distinguishing a structurally-absent bot from an in-progress one — exists
in full at `workflow-integration-github/scripts/_github_checks.py`:

| Function | Line |
|---|---|
| `_classify_check_buckets` | 121 |
| `_is_pull_request_event_run` | 155 |
| `_has_pull_request_event_run` | 178 |
| `_pull_request_event_runs_for_pr` | 244 |

⇒ **D2 is DROPPED, not re-scoped.** The spec's own instruction was *"if it is complete, drop D2 and
say so — this epic's named failure mode is staging a plan for an already-landed fix."* It is complete;
this is the saying-so.

## ⭐⭐ ABSORBED 2026-08-09 — the complement of this plan's natural experiment, realised

Source: inbox `generic-charter-language-specific-defect-008`, first-party on PR #1130.

This plan's evidence has been a run where self-review and CodeRabbit found essentially disjoint defect
sets. #1130 is **the case this plan warns about, actually happening**: no external reviewer produced
content at all (pr-agent `participated_but_empty`, coderabbit `refused_awaitable` with await switched
off, sourcery `refused_hard`), and the merge proceeded on in-house evidence alone — CI green,
quality-gate, 18,135 tests, plugin-doctor clean, self-review clean after 4 findings fixed.

⭐⭐ **The proxy is weakest exactly when it is being leaned on hardest.** That is the sentence this
plan exists to make measurable, and it now has a first-party instance rather than an inference.

⚠ **And the same run supplies the counter-weight, which must not be dropped**
(`generic-charter-language-specific-defect-009`): self-review caught **four** stale-set instances on
that run, including one in a repo-root instruction file that had just been made load-bearing as the
reviewer's own context source. So the honest finding is **not** "self-review is weak" — it is that
self-review and bot review have **different and complementary reach**, and D1's *state what each gate
structurally cannot evaluate* is the deliverable that captures it. ⛔ Do not let this absorption
re-frame the plan as an argument against self-review.

## Claim Labels

- OBSERVED (`#1039`): every in-house gate went green — `pre-push-quality-gate` (bundle + whole-tree,
  test-compile and module-tests), `plugin-doctor` (3 skills, 30 rules, 0 issues),
  `pre-submission-self-review` (125 candidates, 1 finding), `finalize-step-simplify` (0 findings) — and
  **CodeRabbit still found two real defects**: a negative `--max-per-component` producing a
  spuriously-truncated result, and a duplicated disposition table. ⚠ Note "125 candidates" is a VOLUME,
  not a coverage number.
- OBSERVED (the confound, across four-plus PRs): the review bots are frequently refusing, and refusals
  are often stated only in comment bodies.
- OBSERVED (lessons carried, both **OPEN**): `2026-07-21-10-002` — the completeness guard conflates an
  absent bot with an in-progress one; `2026-07-17-09-001` — no simplify ↔ automatic-review same-run
  reconciliation contract.
- HYPOTHESIS (message-supplied, un-re-verified): the `#1039` gate-green / bot-finding pairing is
  representative rather than a single instance — confirm/refute at D1 by sampling further PRs
  (verify-at-outline). **D4's whole value depends on this being a recurring signal**; if it is not, D4
  should ship as a measurement without a parity claim attached.
- HYPOTHESIS (asserted absence): no existing metric already captures the review-versus-gate delta —
  confirm/refute against `manage-metrics` and the retrospective checks, several of which measure
  adjacent things (verify-at-outline). **An unverified absence here would duplicate a shipped
  retrospective check.**
- Verify-first clause: **`quality-gate` excludes `test/` was a claim about the build gate, and it left
  with D2/D3 — do NOT scope it here.** If D1 finds the review-side gaps are inseparable from the
  build-side ones, say so and escalate rather than quietly re-absorbing the returned half.

## Expected Surface

- OBSERVED: the `automatic-review` completeness guard (the `loop_back` decision path).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/finalize-step-simplify` and its reconciliation
  point with the automatic-review record.
- HYPOTHESIS: a governing coverage-parity standard — candidate home
  `phase-6-finalize/standards/pre-push-quality-gate.md` (verify-at-outline). ⚠ If the natural home turns
  out to be the build-gate standard that left with D2/D3, that is a signal the split needs revisiting —
  escalate rather than editing the returned surface.
- HYPOTHESIS: `manage-metrics` or a retrospective check, for D4's measurement (verify-at-outline).
- OBSERVED (absence): `pyproject.toml` `select=` and the gate footprint logic are **NOT** in this plan's
  surface — they went back with D2/D3.

## Dependencies and Sequencing

- Depends on: **PLAN-PR-007** must land first. D2 edits the same participation classifier that plan adds
  a taxonomy member to; landing this first would fork the taxonomy.
- Overlaps with: ⚠ **PLAN-PR-006** (canned no-op marker) is a third distinction on the same classifier.
  ⛔ **D2, PLAN-PR-006, and PLAN-PR-007 must land as one coherent taxonomy, sequenced — never paired.**
- Overlaps with: ⚠ **PLAN-PR-010** touches `phase-6-finalize`. Sequence.
- ⚠ **Cross-epic**: the returned D2/D3 half **is now staged** as `truthful-signals`
  **`PLAN-TRUTH-019`** (`build-gate-coverage-parity`) — confirmed on their side 2026-07-30, carrying the
  returned D2/D3 verbatim plus the eight lessons this spec did not keep. If it lands first and moves the
  gate standards, re-verify this plan's candidate home at outline. **Name its PR when retiring any
  deferral on it** (see the epic's named-PR deferral convention) rather than relying on memory.
- ⛔ **LATENT COLLISION with `PLAN-TRUTH-019`, and it is DEEPER than the shared file** — flagged
  unprompted by that epic (inbox `truthful-signals-002.md`, drained 2026-07-30). Two distinct couplings:
  1. **The file**: this plan's candidate home for a coverage-parity standard is
     `phase-6-finalize/standards/pre-push-quality-gate.md`, and their D2/D4 may move the same file. They
     will name their PR.
  2. ⭐ **The SEMANTICS, which is the part that would actually cost a double fix**: the returned D3 half
     (a zero-scoped-modules / docs-only branch resolving to a clean pass) is **the same conflation** as a
     defect they folded into `PLAN-TRUTH-010` — `resolve-test-scope` returning `recommended_target: null`
     for Python source it cannot resolve. ⛔ ***"No module matched"* and *"no tests needed"* are one
     signal in both places.** They have recorded TRUTH-010 and TRUTH-019 as a **serialization pair** on
     their side so it is not fixed twice in two shapes.
  ⚠ **Nothing is owed from us** — but if this plan's D2 reaches that same branch, say so rather than
  fixing it a third time. This is the vacuous-guard / one-signal-two-meanings archetype, and it is now
  known to live in at least three places.
- Adjacent to: PLAN-PR-004 (charter effect). Both concern review *quality*; that one measures the model's
  output, this one measures the gate/review delta. Different surfaces.

## Absorbed — inbox drain (message `lessons-handling-26-08-08-01-002`, cluster C06)

**D4 gains its empirical population.** Fourteen active corpus lessons, each ending in
*"every in-house gate passed, only the PR bot caught it"* — the measured denominator D4 needs
instead of the single `#1039` anecdote. Ids: `2026-06-22-11-001`, `2026-06-22-12-001`,
`2026-06-22-13-001`, `2026-06-25-02-001`, `2026-06-25-10-001`, `2026-06-30-15-001`,
`2026-07-08-09-001`, `2026-07-12-18-001`, `2026-07-14-16-002`, `2026-07-14-17-001`,
`2026-07-21-01-001`, `2026-07-21-12-001`, `2026-07-22-10-001`, `2026-06-24-14-003`.
Verbatim snapshots at `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.

Two constraints ride with the corpus, and both are binding on D4:

- ⛔ **It is a SAMPLE, not an enumeration** — fourteen lessons somebody chose to file, not every
  occurrence. Any rate derived from it MUST publish the population and its provenance. This is the
  epic's own volume-read-as-coverage archetype pointed at our own measurement.
- ⛔ **The class is MIXED and must be partitioned before any rate is computed.** At least three
  members are *addable in-house gates* (`2026-06-22-13-001` ruff `select` omits RUF;
  `2026-06-30-15-001` unsorted traversal; `2026-07-08-09-001` symlink-through copy) — for those the
  bot caught what a gate *could* have caught, which is a gate-configuration finding, not evidence of
  a structural bot-only class. Others (doc-prose semantics, report-claim consistency) may be
  genuinely bot-only. **Partition by "could an in-house gate have caught this" first.** This is the
  same partition-before-rate discipline PLAN-PR-006's D1 owes for the absence corpus; if the two
  partitions are the same shape, say so once rather than deriving it twice.

⚠ **Overlap to settle at outline, not to discover late**: `truthful-signals` PLAN-TRUTH-019
(build-gate-coverage-parity). If that plan and this D4 are the same population viewed from the build
side and the review side, say so and split the surface explicitly rather than shipping both.

- HYPOTHESIS (verify-at-outline, message-supplied, re-derived by nobody here): that each of the
  fourteen gaps is still open against current main. Confirm/refute artifact: each named gate's own
  scan scope — e.g. the `select` list in the pyprojectx ruff config for `2026-06-22-13-001`.
- OBSERVED (orchestrator, first-party at drain): C06's cover note offered lesson `2026-07-17-09-001`
  as homeless. It is NOT — this spec's **D3** already carries it. No new spec is owed for it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-011-review-bots-catch-what-in-house-gates-cannot.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
