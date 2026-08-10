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

# The post-run band contract cannot express the steps that need it

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

A previous change introduced the `post_run_review` band — every step declaring the fact runs after
the merge gate — and **mandated `mutates_source: false` for membership**. That closed the
downward-facing half of the finalize-ordering defect and left three things open, all live in merged
`main`:

1. A step that needs post-merge evidence **and** mutates source **cannot be in the band at all.**
2. The metrics recorder still runs **after** the retrospective, so the retrospective reads an
   accumulator that has not closed.
3. The change footprint is still **derived at read time from a mutable substrate** rather than
   captured while it was true.

⭐ **These are one plan, not three, because they share a single root**: a step's `order:` determines
what it can *see*, and **nothing declares the producer→consumer edges** that ordering is supposed to
satisfy. The remedy is to make the dependency explicit rather than continuing to hand-tune integers.

### R1 — `mutates_source: true` and post-run-review are mutually exclusive, and one real step needs both

The lessons-housekeeping step runs very early and declares `mutates_source: true`. It **consumes** a
quality-verification report produced by the retrospective hundreds of orders later. Its own log
records the consequence: the report was unavailable, a references field was absent, and it proceeded
on the request document plus the branch diff.

⛔ **It cannot simply move.** Band membership requires `mutates_source: false`; this step declares
`true`. Relocating it past the merge gate would land a declared mutator with **no push path** — the
exact defect the post-run source guard was added to detect.

⭐ **The one candidate that survives the constraint** (converged on independently by two epics):
**split the step** — a main-anchored *classify* pass early, and a pushable *apply* pass in the settle
band. ⚠ That is the leading candidate, **not a decision**; D2 settles it.

### R2 — the retrospective still reads an unclosed accumulator

The retrospective is ordered before the metrics recorder, so the largest phase of a run is read as
zero at exactly the moment the retrospective samples it.

⭐ **The partiality machinery works correctly** — the row is marked unrecorded and the total stamped
partial — so this produces an **honest floor**, not a falsehood. That is why it is a defect and not
an emergency, and why the fix is the **ordering**, not the partiality reporting. ⛔ **Do not "fix" the
labelling; it is the only component currently telling the truth.**

A downstream consequence worth carrying: three producers have reported three materially different
totals for one run, because they sample at three points in a sequence nobody declared. The
*labelling* half of that belongs to another epic; **the sampling-point half is this plan's.**

### R3 — capture, don't derive

A previous change correctly removed a `base..HEAD` range from the footprint fallback chain (it
over-counted several-fold, because sibling PRs land in between). The shipped chain is live worktree
diff → a legacy references key → an explicit unresolved sentinel, and it never silently returns an
empty set.

⛔ **But the recommended tier — the plan's own merge commit — was not implemented**, and the shipped
legacy key is scoped by its own docstring to plans created before the ledger was removed. ⇒ **For
every new plan the archived path resolves to UNRESOLVED permanently.**

⭐ **Honest-but-unmeasurable is a strict improvement over confidently-wrong and is not the same as
measured.** The remedy: have the branch-cleanup or push step persist the realized footprint as a
deterministic side effect, and make the resolver prefer it. **Capture it while it is still true.**

⛔⛔ **This is a correctness gap, not a reporting statistic.** On one landing the under-declaration
was several paths wide, and **two of the undeclared files were the subject of three review
findings** — so the under-declaration **under-scoped a remediation sweep** and an external reviewer
caught what the sweep missed. Every finalize step that scopes itself from the declared file set
inherits that miss. D4 must state that consequence, so the fix is understood as restoring a **scoping
input** rather than improving a retrospective number.

## Goal

Finalize ordering is derived from declared producer→consumer edges rather than hand-tuned integers;
a step that needs post-merge evidence and mutates source has a stated, sanctioned answer (an
exception with a push path, a split, or an explicit "unrepresentable"); the retrospective reads a
closed accumulator; and the realized footprint is captured while true instead of re-derived from a
substrate that has since changed.

## Deliverables

1. **D1 — GATE: derive the producer→consumer edges, do not enumerate them. Mutates nothing.**
   For every finalize step, determine which artifacts it reads and which it writes, and report the
   pairs whose `order:` values violate the implied dependency.
   ⛔ **The three residues above are a SAMPLE** — they surfaced because someone happened to read a
   log. **Report the derived cardinality.**
   ⚠ A population derived from step markers is a **FLOOR, not a count** — only some steps carry
   them. Settle the enumeration mechanism before asserting coverage.
   *Done when:* the edge set is derived from step definitions, the cardinality is published, and the
   enumeration mechanism's coverage is stated.
2. **D2 — settle the band contract for a step that needs post-merge evidence AND mutates source.**
   Either the `mutates_source: false` requirement gains a sanctioned exception with a push path, or
   such a step must be split, or the case is declared unrepresentable and the source guard says so
   explicitly.
   ⛔ **All three are acceptable outcomes; silently leaving it unrepresentable is not.**
   *Done when:* one of the three is implemented and the reasoning is recorded in the contract
   document, not only in the run report.
3. **D3 — the retrospective reads a closed accumulator.** Fix the ordering.
   ⛔ **Close the accumulator, not merely re-order the reader** — a reader moved after an accumulator
   that never closes still reads a short number.
   ⛔ **Leave the partiality labelling intact** so a future omission still surfaces.
   *Done when:* the retrospective's reading of the largest phase is non-zero on a run where that
   phase did work, and the partiality machinery still marks a genuinely-absent row.
4. **D4 — capture the footprint while it is true.** Persist the realized footprint as a deterministic
   side effect of branch-cleanup or push, and make the resolver prefer it.
   ⛔ **Never reintroduce `base..HEAD`** — sibling landings contaminate any such range.
   ⭐ **Evaluate the merge-commit fallback as a resolution tier.** It is **not** `base..HEAD` and the
   prohibition does not reach it: a merge commit names its own two parents, so the range is exact and
   carries no sibling contamination. ⚠ It only resolves *post*-merge, so it cannot serve a consumer
   running before the merge — which is why the deterministic capture stays the primary mechanism and
   the merge commit is a fallback tier.
   ⚠ **Design the SHA-recovery seam rather than assuming the squash case**: which step record carries
   the landing SHA, and what happens on a non-squash merge.
   ⚠ **Feed the same resolved list to the routing-decisions check** so both consumers recover
   together — one footprint resolution, two consumers.
   *Done when:* a post-merge retrospective resolves the footprint and reports a measurable recall
   instead of `inconclusive`.
5. **D5 — this change is NOT self-exercising; say so and name the observation point.**
   The plan modifies finalize ordering, so its own manifest — frozen earlier in the run — executes
   the OLD order, and its script-backed steps resolve from a cache synced later in the same run.
   ⛔ **Its own green finalize is NOT evidence the fix works.**
   *Done when:* a derivation-level test exists that is observable from inside the run, and the run
   report states plainly which evidence its own execution could and could not provide.

Five deliverables — under the split guard, and **proceeding unsplit is deliberate**: D2/D3/D4 are
three instances of the single root D1 derives, and splitting them would produce three plans that each
re-derive the same edge set and race each other on the same `order:` frontmatter. D5 is a
documentation obligation, not an independent workstream.

## Out of scope

- **The partiality labelling.** Excluded because it is currently the only component telling the
  truth; changing it would remove the signal that makes a future omission visible.
- **The corpus-resolution half** — decoupling a store handle from the working directory so a step's
  order stops determining what it can see. Excluded because another epic owns it under an explicit
  cross-epic agreement; ⛔ **what must not happen is both epics editing the band contract.**
- **A second reader obligation for absent inputs** ("a post-run step whose input is unreadable emits
  `indeterminate`, never a graded value"). Excluded because it is **already discharged** on merged
  main — the reader carries a stated sentinel and yields `inconclusive`, not a graded `fail`. The
  citing instance ran pre-fix code. What survives from that request is R3, not another reader change.
- **The declared-file-set side of the footprint.** Excluded because another epic owns it; this plan
  captures the **realized** side only, and ⛔ **the two keys must not drift toward one name.**

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the band narrative and the
  guard hook. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — the
  band discriminator and the `mutates_source` requirement. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py`.
  **OBSERVED.**
- The `order:` frontmatter of the metrics-recording, retrospective and lessons-housekeeping steps
  (the last under `.claude/skills/`). **OBSERVED.**
- The manifest step-sorting helper and the derivation guard added alongside the band.
  **HYPOTHESIS**, verify at outline.
- The branch-cleanup / push step bodies, for D4's capture side effect. **HYPOTHESIS**, verify at
  outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The `order:` / `mutates_source` / `post_run_review` values that create the R1 conflict | **OBSERVED on merged main** | The step frontmatter named in Expected surface — all git-reachable. ⛔ **Re-read them; they are the premise the whole plan rests on and they move.** |
| The shipped three-tier footprint chain, its unresolved sentinel, and its resolved predicate | **OBSERVED** | The footprint resolver in the clone. |
| The retrospective reads an unclosed accumulator | **OBSERVED** | The two `order:` values plus the recorder's step definition — settle it by reading, not by inference. |
| The magnitude of the understatement, and the several-fold `base..HEAD` over-count | **OBSERVED, but the measurements are NOT reachable from this clone** | They come from machine-local run records under the git-ignored `.plan/` tree. ⛔ **Do not go looking for them.** They motivate the plan; **no deliverable is gated on reproducing them.** |
| Three producers reported three different totals for one run | **HYPOTHESIS (second-hand)** | Corroborate before quoting. Not load-bearing for any deliverable. |
| The merge-commit recipe returns the exact realized path set | **OBSERVED, and verified by hand on a real landing** | `git show --name-only --pretty=format: {merge_sha}` against a squash merge. Re-verify in the clone on any merged commit — this one **is** reproducible here. |
| Every orchestrated finalize runs the retrospective after branch-cleanup, so **every** post-merge retrospective loses both coverage checks | **HYPOTHESIS** | ⛔ **Re-derive from the step order in the clone.** If true it is the standing state rather than one plan's bad luck, which changes D4 from an improvement into a repair. |
| That the reader-grades-absent-inputs defect is still live | **REFUTED — recorded so it is not re-derived** | Already fixed on main; the citing instance ran pre-fix code. Do not re-scope it. |

An asserted **absence** ("the merge-commit tier was not implemented") is verified exactly as an
asserted presence — confirm it in the resolver before building it, because an unverified absence
produces a second implementation beside one that already exists.

## Verification

- **D1's coverage is verified by stating what it could not see.** If the enumeration mechanism only
  covers some steps, the reported cardinality is a floor and must be published as one. A count
  presented without its coverage is the defect this plan exists to fix, reproduced.
- **D3 is verified against a real non-zero phase**, not against a fixture that closes trivially.
- **D4 is verified by a post-merge run resolving a footprint** — recall reported as a number rather
  than `inconclusive`. Assert the negative control too: an unresolvable footprint must still yield
  `inconclusive`, never a graded zero.
- **D2 carries a cold read**: whether the contract now reads as *"this case is representable"* or
  *"this case is explicitly refused"* is exactly what a later reader must not get wrong. Dispatch the
  pre-PR verification sub-agent to read it cold and report which reading it took.
- **D5 is verified by honesty rather than by a green run.** The run report must state which of its
  own claims its execution could not substantiate.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Cross-epic agreement, do not re-litigate.** Ownership was split by agreement: the **band
  contract** (whether a source-mutating step can ever be post-run, what the guard should say, and the
  ordering that follows) is this plan's; the **corpus-resolution half** belongs to another epic and
  is gated on this plan existing. Read their side before scoping D2; the two must agree.
- **Serialization.** This plan sits in the finalize / retrospective surface class — do not run it
  concurrently with another plan touching the same `order:` frontmatter or the retrospective's
  reading path.
