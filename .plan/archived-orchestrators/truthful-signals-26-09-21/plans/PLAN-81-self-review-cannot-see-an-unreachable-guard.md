# PLAN-81: In-House Structural Review Reports Clean On A Guard That Cannot Fire

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-27 from PR #1013's landing (PLAN-69). Lesson `2026-07-27-08-001`.
> **The sharpest instance of this epic's archetype recorded so far: a plan whose entire purpose was to
> make a false-green structurally impossible introduced a fresh false-green inside its own guard, and
> the in-house structural review reported CLEAN on it.**

## Objective

`pre-submission-self-review` (via `pm-plugin-development:ext-self-review-plan-marshall`) exists to
surface deterministic structural defects before a diff reaches review. On #1013 it ran **13 checks
over 50 candidates and reported clean** — and `finalize-step-simplify` reported **0 findings** — on a
newly-added guard whose predicate could not fire. **Two independent bots caught it.** Give the
in-house review a check for the defect class this epic tracks most: a predicate that cannot reach a
true positive.

## ⚠ Mechanism — OBSERVED, verified first-party at HEAD

The defect (now fixed in #1013 itself; it is the *detector gap* that remains open):

- OBSERVED — `generate_executor.py:706-730`, `_split_bundle_version`. The shipped version anchors on
  the cache root and its docstring names what the original did wrong: scanning for *"the first
  version-shaped segment anywhere in the path"* mis-splits on **two real inputs** — a version-shaped
  **ancestor directory** above the cache root (`/srv/1.0-workspace/cache/{bundle}/{version}/…`) and
  **a bundle whose own name starts with `N.N`** (`1.0-my-bundle`). It records the consequence
  verbatim: *"Either returns the wrong key and silently defeats the provenance guard."*
- **The second trigger is not hypothetical: `1.0-my-bundle` is a naming convention this repo
  DOCUMENTS and PINS IN A TEST.** The vacuous-guard trigger was already sitting in the repo's own
  fixtures — which is exactly the kind of thing a deterministic in-house check is well-placed to find
  and a human reviewer is not.
- OBSERVED (operator-reported) — `pre-submission-self-review`: 13 checks, 50 candidates, **clean**.
  `finalize-step-simplify`: **0 edits, 0 findings**. Both green on this diff.
- OBSERVED — the two bots that caught it did so from the diff alone, so the information needed was
  present in the change; the in-house pass had no *informational* disadvantage, only a missing check.

**Why this is not simply "add another check":** `ext-self-review-plan-marshall` already surfaces
symmetric-pair functions, flag-guard pairs, producer-consumer pairs, and lone-unguarded-boundary calls
— it is *built* for exactly this family. The gap is that every existing candidate class is a **shape**
(two things that should match), while "this predicate cannot reach a true positive" is a
**reachability** property. D1 must decide whether that is expressible deterministically at all.

## ⛔ TWO NEW INSTANCES FROM #1022 — the CLEAN verdict is now a PATTERN, not an anecdote

Folded 2026-07-27 from the PLAN-62 landing (inbox messages `-002` and `-003`, read first-party).
On PR #1022, `pre-submission-self-review` reported **"clean: 75 candidates examined"** over TWO real
defects that review bots caught immediately:

- OBSERVED — **a production defect (CodeRabbit, 🟠 Major).** `ci_complete_precondition.py::resolve`
  rebound `timeout_seconds` at a clamp settle point, and the ratchet then used that same rebound name
  as its comparison base, so the learned value drifted DOWNWARD on every deadline-exceeded finalize.
  The module docstring simultaneously claimed the value "stays honest / is free to exceed the clamp"
  — code and prose disagreed **inside the change written to make them agree.**
- OBSERVED — **a test defect (CodeRabbit, same review).** The shipped test seeded a persisted ceiling
  of 5000s and asserted only that ~571s was recorded, with **no assertion connecting input to
  output** — codifying the drift as the contract and pre-defending it against any correct fix.
- OBSERVED — **a third defect the self-review also missed (PR-Agent, independently).**
  `_clamp_wait_ceiling` had no lower bound, so `--timeout 0` or a corrupt negative persisted value
  reaches `subprocess.run` and raises an uncaught `ValueError` (only `TimeoutExpired` is handled).
- **⇒ This is the SECOND identically-shaped occurrence** (cf. `_split_bundle_version`, #1013: a
  vacuous guard introduced BY a vacuous-guard fix, self-review CLEAN, two bots caught it). **The
  recurring signal is not the defect class — the defects differ. It is that the self-review returns
  CLEAN on the specific class "a fix for archetype X introduces a fresh instance of X".**

**⇒ D1 gains a mandatory question, and it is a fork the gate must resolve rather than assume:**
**was the candidate surfaced and mis-judged, or never surfaced at all?** Those demand opposite fixes —
a judgement problem needs better criteria, a coverage problem needs a new detector — and D1 MUST
settle it by inspecting the actual candidate set from a reproduction, not by reasoning about what the
detector *ought* to emit. ⚠ Both instances examined a large candidate count (75 here, similar there)
and returned CLEAN, so **candidate VOLUME is not evidence of coverage** — the same false-confidence
shape PLAN-78 records for `extract-chat-signal`.

**Two durable rules the fixes yielded** (D2/D3 should encode whichever are detectable):

1. **A variable rebound at a settle point must not remain the comparison base for a downstream
   invariant.** When a value is clamped/normalised/defaulted in place, every later read of that name
   silently switches meaning from "what was requested" to "what was consumed". Keep the pre-settle
   value in a distinctly-named local whenever a later predicate is about the *request*.
2. **An observation-derived test tell:** a fixture with a dramatic input and an assertion on an
   unrelated small output, with nothing relating them — the gap is where the invariant should be.
   Prefer relational assertions (`not [d for d in recorded if d < requested]`) over
   equality-to-observed whenever the property is a bound or a direction rather than an exact value.

⚠ **Counterweight, do not drop it:** inbox message `-003` from the PLAN-55 era recorded the SAME
self-review CATCHING a description-body drift before push. **D1 must read both** — the gate is not
uniformly blind, and a fix that assumes total blindness would be scoped wrong.

## ⛔ THREE MORE INSTANCES FROM #1027 — and one of them names the missing mechanism

1. **A property the code ADVERTISED was falsified by an external reviewer, not by six rounds of
   self-review.** `cmd_inbox_archive`'s docstring and D5 both promised *"idempotent on repeat"* and
   *"safe to resume"*; CodeRabbit found a **TOCTOU race**. **Six self-review rounds validated the
   prose.** ⇒ **The gap is not judgement, it is execution: no in-house gate runs the interleaving**, so
   a concurrency claim is unfalsifiable in-house by construction. D1 must decide whether such claims are
   (a) out of scope for a structural reviewer — and therefore must be *labelled unverified* rather than
   silently cleared — or (b) in scope, requiring a real check.
2. **A candidate was EXAMINED and CLEARED, and the clearing was wrong.** Self-review inspected
   `_section()`, reasoned correctly about the `####` nesting case, and **never checked the `##`
   boundary**. CodeRabbit found it four rounds later. ⇒ **This settles D1's central fork for at least
   one instance: the candidate WAS surfaced and MIS-JUDGED.** Partial-coverage-of-an-examined-candidate
   is a distinct failure from never-surfacing, and it needs a different fix — the detector must record
   *which cases it checked*, not merely that it looked.
3. ⭐ **The countermeasure that worked is known, and nothing requires it.** **Five defects were
   introduced by the fix for a prior defect**, two re-introducing the vacuous-guard archetype *through
   its own remedy*. What broke the chain — twice — was an **explicit adversarial re-read of the fix's
   own diff**, which happened only because the executor asked for it in the dispatch prompt.
   Lesson `2026-07-28-08-001`. ⇒ **Strong candidate for D2/D3: make the fix-diff re-read mandatory**,
   since a fix is the highest-risk moment and is currently the least-reviewed one.

⚠ **Counter-evidence to weigh, not to discard:** this same run's self-review DID find 5 real defects
including 2 vacuous guards. **The gate is productive, not broken** — D1 must scope a *sharpening*, not
a replacement. Combined with the earlier CLEAN-over-real-defects instances, the CLEAN verdict is now
**n=4**.

## Deliverables

### D1 — GATE: decide whether unreachability is deterministically detectable here (mutates nothing)

**Do not assume it is.** Establish, against the real #1013 diff as the worked example, whether a
deterministic candidate-surfacer could have flagged `_split_bundle_version`. Candidate framings to
evaluate, cheapest first:

- **New-guard-without-a-failing-test** — a diff adds a refusal/guard path but no test asserts the
  refusal fires. Cheap, shape-based, and would have caught this one.
- **Predicate-over-parsed-structure** — a new predicate derives a key by *scanning* rather than by
  *anchoring* (first-match over an unbounded sequence). Narrow, but it is the literal shape here.
- **Fixture-contradiction** — a new predicate's assumption is contradicted by an existing pinned test
  fixture (the `1.0-my-bundle` convention). Powerful, and the repo already has the fixtures.

**If none is deterministic enough to run without false-positive noise, say so and choose the honest
fallback** — e.g. surfacing new guards as *candidates for human attention* rather than asserting
cleanliness. ⚠ **A check that cannot fire would be this plan committing its own subject-matter
defect**; D1 must state how the chosen check is verified to reach a true positive.

### D2 — implement the D1-chosen check in `ext-self-review-plan-marshall`

Scoped to surfacing candidates, consistent with the extension point's existing contract. No blocking.

### D3 — the clean verdict stops over-claiming

`pre-submission-self-review` reporting *"clean: 50 candidates examined"* reads as *"no structural
defects"* when it means *"none of my 13 checks matched"*. Make the verdict state its own scope — the
same distinction PLAN-51 shipped (`sections_omitted` / `sections_dropped`) and PLAN-76's D1 requires
(`unmeasured` ≠ `0`). **This is the durable half**: even where a check is missing, the report should
not read as coverage it does not have.

### D4 — tests

(a) The #1013 pre-fix `_split_bundle_version` (scanning form) is surfaced by the new check —
**verified to FAIL against the current checker**. (b) The fixed anchored form is NOT surfaced (no
false positive). (c) The D3 verdict distinguishes "no checks matched" from "nothing to check".

Four deliverables (D1 a gate) — under the split guard.

## Expected Surface

- OBSERVED: `pm-plugin-development` — `ext-self-review-plan-marshall` (the candidate surfacers) and
  the `pre-submission-self-review` verdict/reporting path. **Exact files verify-at-outline** — the
  bundle is named in the skill listing; its script layout was not read by the orchestrator.
- HYPOTHESIS: `finalize-step-simplify` — it also reported 0 findings; D1 should decide whether it
  shares the gap or is legitimately out of scope for guard reachability (verify-at-outline).
- OBSERVED (worked example, read-only): `tools-script-executor/scripts/generate_executor.py:706-730`
  and its Guard 4 consumer at `:952`.
- OBSERVED: lesson `2026-07-27-08-001`, retired at finalize.
- HYPOTHESIS: tests under `test/pm-plugin-development/**` — confirm the module exists before assuming.

**Disjointness:** confined to `pm-plugin-development`. Disjoint from every staged plan — PLAN-79
(`platform-runtime`/`manage-status`), PLAN-80 (`workflow-integration-github`), PLAN-57
(`manage-status`), PLAN-75 (`manage-execution-manifest`), PLAN-62, PLAN-76 (project-local auditor),
PLAN-78 (`plan-retrospective`). **Good parallel candidate.**

## Dependencies and Sequencing

- Independent; no gate.
- **Conceptual sibling of PLAN-76's D5** (surface a detector with zero corpus positives as suspect).
  Different surface — that is the archived-plan auditor, this is pre-submission self-review — but the
  same idea applied one layer earlier. **If both land, their class-guard vocabulary should agree**;
  whichever is second should reuse the first's phrasing rather than inventing a parallel one.

## Notes

- **The bots outperformed the in-house pass on the exact class the in-house pass owns.** That is worth
  stating plainly: it is an argument for the check, and simultaneously a caution against the reflex of
  treating automated review as redundant once in-house checks are green.
- Recurrence data: the vacuous-guard archetype now includes `scope_creep_check`, saturated markers,
  `search-markers`, roster-count, PLAN-76's three auditor detectors — **and now one introduced by a
  fix for the archetype itself.** The class is not converging; a detector for it is overdue.

## ⚠ COUNTER-EVIDENCE 2026-07-28 (#1038) — self-review caught a defect the plan itself introduced

This plan's premise is that `pre-submission-self-review` returns CLEAN over real defects. **#1038 is a
counter-instance and must be scoped in, not ignored:** self-review caught the plan **reproducing its
own target defect** — `phase-4-plan` Step 8 parsed only `total_failed`/`ambiguous`, silently dropping
a rejected persist at a call site the plan itself had just created. It found 4 defects, they were
fixed, and re-review came back clean.

⛔ **Do not let this be read as refuting the plan, and do not let the plan ignore it.** Both are true:
self-review has returned CLEAN over real defects (the 250- and 75-candidate instances), **and** it has
caught a subtle self-inflicted one. **The deliverable is therefore not "make self-review work" but
"characterise when it sees and when it cannot"** — the unreachable-guard case this plan names is a
*specific blindness*, not a general failure.

⚠ **D1 must state the discriminator.** If it cannot say why #1038's defect was visible and the
250-candidate defects were not, the fix will be aimed at the wrong property — and a volume-based
remedy would not have helped here, since this was caught at 38 candidates.

## Verify a BEHAVIOUR at its execution surface

A change claimed a behaviour in doc text **and** in an expectation list while **no artifact
implemented it**. Both review bots passed it; only an operator's manual review caught it.

⛔ **The tautology is the point:** two artifacts that both merely *describe* a behaviour agreeing
with each other is not evidence — it is a restatement. *"The docs and the expectation list agree"*
must never be accepted as verification.

**The check this plan should add to pre-submission self-review** — for every behavioural claim a
change introduces (doc text, expectation list, task description, PR body):

1. Identify the single artifact that would have to change for the claim to be true — the POM goal,
   the workflow step, the conditional in code.
2. Open it and confirm the change is present. ⚠ **An artifact carrying NO diff hunk is a red flag,
   not reassurance.**
3. Name the implementing artifact in the review output, so the absence of one is visible rather
   than assumed.

⭐ **This is the same defect as PLAN-61's citations-vs-assertions finding, seen at the review seam
rather than the premise seam** — there, a claim passed because its citations were valid; here, a
claim passed because its *descriptions* agreed. **Co-design with PLAN-61**; the two should not
invent separate remedies for one shape.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
