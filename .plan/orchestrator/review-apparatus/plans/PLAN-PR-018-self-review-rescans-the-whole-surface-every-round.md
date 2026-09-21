> ⛔⛔ **RETIRED 2026-08-08 — CONCEDED to `code-intelligence-substrate` PLAN-CIS-031, which is ALREADY
> RUNNING this subject** (`self-review-resweeps-full-surface-every-round`, at `2-refine`, launched
> 20:33). Discovered while analysing the PLAN-PR-007 landing: the plan appeared in `manage-status list`
> and its `request.md` `source_id` names their spec. **They are in flight; we were staged.**
> Everything this spec absorbed — the C18 lesson corpus, the scope-of-sweep ≠ scope-of-claim trap, the
> `#1087` cost-and-yield datum, and the fresh `#1118` yield curve — was handed to them as
> `code-intelligence-substrate/inbox/review-apparatus-006.md`. ⚠ **Routing note for the record:** their
> spec routes it out of this epic ("no PR/review-participation surface"); our row came in routed the
> opposite way ("pre-submission self-review IS review apparatus"). **Both readings are defensible — the
> three-way rule does not cleanly assign *self*-review, and that gap produced a genuine duplicate that
> lived in two ledgers until an unrelated status listing exposed it.** ⛔ **Do not re-open this row.**
> Kept on disk as the audit record of what was handed over.

# PLAN-PR-018: Self-review re-scans the whole surface every round, and the cost compounds

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — lever **L5** of the cross-epic token-reduction roadmap

Staged 2026-08-03 from `truthful-signals-015` (roadmap REV 2). ⭐ **Token reduction is operator-confirmed
Priority 1** — confirmed first-party by `code-intelligence-substrate` with the operator, not merely
reported. **L5 is this epic's wave-1 item** and the only roadmap lever we own outright.

⚠ **The roadmap is a proposal, not a directive.** We accepted L5 in reply `review-apparatus-016`, with the
success-test correction below, which REV 2 adopted.

## Why this lever is worth taking

⭐⭐ **99% of billing-weighted cost is CONTEXT, not generation** (n=47 archived plans; `cache_read` 76.1%,
`cache_creation` 22.8%, **`output` 1.1%**; billing formula reconstructed exactly to the token). An explored
byte is paid ~once at 1.25× and then **once per remaining turn** at 0.1×. ⇒ **The cost of a byte is a
function of WHEN it enters context, not just its size.**

Self-review runs late and re-enumerates a growing surface each round. Observed candidate growth across one
plan's rounds: **86 → 106 → 123**.

⛔⛔ **THE PER-PHASE FIGURES ARE NOT SETTLED — do not use them to justify this plan's size.** We ourselves
found, first-party on #1078, that a closed phase row is never re-opened on loop-back: `[5-execute]` closed
at 162,906 while the plan looped back three more times for a further **758,059 tokens that no phase row
absorbed**. ⇒ Every looping plan is under-counted. ⭐ **"99% of cost is context" is the durable conclusion;
the per-phase ranking is the fragile one.** This plan rests only on the former.

## ⛔⛔ The success test is TWO-SIDED. This is the whole plan.

**Our correction to REV 1, which REV 2 adopted, and it is the load-bearing constraint:**

> The test is **NOT** *"did round 2 avoid re-enumerating?"* — that is trivially satisfiable by doing less
> work. It is **"does the delta-scoped pass still find the defects the full-surface pass found?"**

⛔ **The candidate growth 86 → 106 → 123 is NOT redundancy.** The surface genuinely got bigger, because
**each round's fix changed the tree.** A plan that reads the growth as waste will scope this as
deduplication and ship a regression.

**Replayable corpus, first-party, already gathered:**

- **#1077** — four blocking defects across three rounds, **all found by self-review and NONE by any bot.**
- **#1078** — passes 1, 2 and 3 **each** found a genuine defect. Zero failures; three real catches.

⛔ **The unsafe class, stated precisely**: a defect in round N's fix is *inside* the delta and a
delta-scoped pass still catches it. **The danger is a defect in UNTOUCHED code made reachable or wrong BY
the fix** — and that is exactly the class that produced #1077's round-1 finding, where the plan's own fix
reintroduced the fail-open shape the plan existed to remove. ⭐ **A naive "diff the candidate set" cannot
see it.**

## ⛔⛔ ABSORBED 2026-08-03 — the best-evidenced instance yet, AND the trap that would sink a naive delta scope

From PLAN-PR-009 / PR #1087's own finalize and its candidate-lesson `-002`.

### The cost datum, with its yield attached

**7.2M tokens against a `single_module` + `bug_fix` anchor of ~1.3M — 5.5×.
`pre-submission-self-review` alone was 1.19M across 5 iterations.**

⛔ **Do NOT cite the 1.19M without the yield**: the 5 iterations produced **15 findings, all real, all
fixed** (curve 6, 4, 3, 1, 1 — converging), and **5 of CodeRabbit's 10 suggestions targeted this plan's
own guard code.** ⭐ This is the corpus entry that makes D1's "report cost and yield together" concrete —
and it points *against* a naive cut, not for one.

### ⛔⛔ The trap — `scope-of-sweep ≠ scope-of-claim`, and it shipped a live defect

⭐⭐ **This is the single most important input to D2, because it is this plan's failure mode observed in
advance.** Self-review round 4 asserted a residual literal appeared in *"zero test and source files."*
**Three survivors were live in merged main** (`test_ci_base.py:548,561,569`).

**Why**: the sweep was scoped to `marketplace/**` — its own resolution text says *"The single remaining
**marketplace** occurrence"* — while the **claim** asserted *"test and source"*. ⛔ **The searched
population and the asserted population silently differed.**

⚠ **And the recurrence migrated granularity under fixing** — each iteration's miss was finer than the last:

| Round | Miss |
|---|---|
| 2 | swept 3 of 4 docs — **a whole FILE missed** |
| 3 | patched the named location while **the survivor sat inside the very line the fix edited** |
| 4 | fixed 2 named sites, asserted a corpus-wide zero, **3 siblings in the same file survived** |

⇒ ⛔⛔ **A delta-scoped pass is a SCOPE RESTRICTION, and this is exactly how scope restrictions fail: not
by missing the delta, but by making a claim wider than the scope searched.** ⭐ **D2 and D3 must therefore
require every residual/absence claim to publish `scope_searched` and `files_scanned` alongside its
count** — otherwise this plan ships a faster pass whose claims are quietly narrower than its wording, and
that is strictly worse than the slow pass it replaces.

⭐ **Adopt the positive shape the same plan demonstrated**: finding `a494d3` **searched the claim rather
than the string** — enumerate the doc-quoted literals and match each against the live source symbol — and
**closed its class exhaustively.** ⇒ *Search the claim, not the phrasing.*

⚠ **A tooling constraint that caused part of this and belongs in the outline**: `architecture search
--content` is **case-sensitive with no `--ignore-case`**, and `--literal` (the flag an author reaches for
when the pattern contains regex metacharacters like `--pr-number`) `re.escape`s the pattern, so an inline
`(?i)` becomes impossible. **Verbatim matching and case-insensitivity are mutually exclusive by
construction.** Its top-level `count` also double-counts multi-module files. ⛔ **Routed to
`code-intelligence-substrate`, who own the content-search seam — do not fix it here**, but do not build a
sweep that assumes it is case-insensitive either.

## Deliverables

1. **D1 — GATE (mutates nothing): establish what the re-scan actually costs and what it actually finds.**
   Per round, per plan across the #1077/#1078 corpus: candidates enumerated, candidates newly appearing,
   and **which round each real defect was found in.** ⛔ **Report cost and yield together.** A round that
   is expensive and productive is not a target; this plan exists only where cost and yield diverge.
2. **D2 — a delta-scoped pass whose scope is the CHANGE PLUS ITS REACHABILITY CLOSURE**, not the changed
   files. The closure is the deliverable; the diff is the easy half. ⛔ If D1 shows the closure is not
   computable at acceptable cost, **say so and stop** — shipping a diff-only scope is worse than shipping
   nothing, because it converts a slow-but-sound pass into a fast unsound one.
3. **D3 — the replay harness.** Both corpora re-run under the delta scope, asserting **every** defect the
   full-surface pass found is still found. ⛔ **Population derived and non-empty-asserted FIRST** — this
   epic has been bitten repeatedly by set-guards that pass on an empty population; copy
   `test/_shared/_dispatch_roster.py`.
4. **D4 — a saving that is stated honestly or not at all.** ⛔ **No token-delta claim may be made until the
   measurement defect is fixed** (`truthful-signals` PLAN-TRUTH-035 / the loop-back phase-row under-count).
   ⭐ **That does not block this plan** — D3's correctness test is binary and needs no token measurement.
   **Ship the structural change; leave the number to L3.**

## ⛔ Prohibited remedies — from the roadmap's anti-goals, and one is aimed straight at this plan

- ⛔⛔ **Do NOT reach for the `minimal` posture.** It would have dropped `pre-submission-self-review` —
  **the one arm that caught #1077 reintroducing the exact shape that plan existed to remove.** Cheaper,
  and it ships the defect. ⭐ **The lever is review that SCALES WITH THE DELTA, never less review.**
- **Do NOT optimise candidate counts, step counts, or dispatch counts.** All are proxies for the **1%**.
- **Do NOT rewrite plan specs plainer to trip fewer sensors.** The ⛔/⚠ markup carries the anti-rework
  record that stops plans re-deriving settled constraints.

## Claim Labels

- OBSERVED (first-party, ours): the #1077 and #1078 round-by-round defect counts; the 86 → 106 → 123
  candidate growth; the #1078 phase-row under-count.
- OBSERVED (filer, `truthful-signals`, reconstructed to the token): the billing composition figures.
- ⚠ **HYPOTHESIS**: that exploration bytes are the dominant *cause* of `cache_read`. Strongly suggested
  (79.6% of tool-result bytes) but **not established** — L3 is what would establish it. ⛔ **Do not cite it
  as fact in this plan's justification.**
- ⚠ **UNKNOWN**: whether the reachability closure is computable at a cost below the re-scan it replaces.
  **D1 answers this, and a null result is a valid publishable outcome.**

## Dependencies and Sequencing

- ⭐ **No dependency on L2/L3.** The two-sided success test is binary and needs no token measurement — this
  is precisely why the roadmap places it in wave 1.
- ⚠ Adjacent to `code-intelligence-substrate`'s content-search seam (L4a): if a sanctioned content-query
  verb lands, the closure computation may become far cheaper. **Do not block on it**; re-check at outline.
- Overlaps with no staged plan in this epic on file surface — verify at outline.

## ⛔⛔ ABSORBED 2026-08-08 — nine corpus instances of self-review failing to close the class it opened

Source: `lessons-handling-26-08-08-01-003` (cluster C18). Verbatim snapshots at
`.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.

This spec already carries the sharpest single instance of the shape — scope-of-sweep ≠ scope-of-claim,
where a delta-scoped pass made a claim wider than the scope searched and the recurrence **migrated
granularity under fixing** (round 2 missed a whole file; round 3 missed a clause inside the very line
the fix edited; round 4 asserted a corpus-wide zero while three siblings survived in the same file).
The cluster supplies eight further first-party instances, which turns that from an anecdote into a
population D2/D3's scope-publication requirement can be sized against.

| Lesson | The shape |
|---|---|
| `2026-08-03-17-001` | **the abstract form**: an aggregation states its predicate precisely and leaves the set it ranges over implicit |
| `2026-07-27-08-001` | guard-relational variant: enumerate every relational case a new guard's own condition implies, not only the motivating case |
| `2026-07-29-18-006` | symmetric-peer variant: audit a classifier's peers for the defect's SHAPE, not its text |
| `2026-07-18-05-002` | contract prose mirrored across N locations — sweep all occurrences in one pass, not one-at-a-time |
| `2026-06-30-20-001` | a helper mirroring a canonical must mirror its full sibling-invariant surface |
| `2026-08-02-15-005` | a test name and docstring are a coverage claim — do not promise universal and assert existential |
| `2026-08-02-15-004` | the reflexive case: apply the rule you are enforcing to the artifacts your own change creates |
| `2026-07-28-08-001` | a fix is the highest-risk moment in the pipeline — mandate a named adversarial self-re-read of every fix's own diff |
| `2026-07-18-14-001` | ⚠ **NOT the same shape** — normative worked examples being *semantically wrong*, which structural self-review misses entirely |

⭐ **`2026-08-03-17-001` is the general statement of this plan's whole thesis** and should anchor D2/D3's
wording: *the predicate is stated precisely, the set it ranges over is left implicit.* Every scope
restriction that failed here failed that way — never by missing its own delta, but by making a claim
wider than the scope it searched. ⇒ **D2/D3's requirement that every residual/absence claim publish
`scope_searched` + `files_scanned` is exactly the remedy for the abstract form**, not merely for the
one incident that motivated it.

⚠ **`2026-07-18-14-001` does not belong to this class and must not be folded into the same
deliverable.** A worked example that is structurally well-formed and semantically wrong is invisible to
any sweep-scope discipline. Either scope it out explicitly or give it its own deliverable — silently
absorbing it would reproduce the exact defect this plan exists to fix, at the level of this spec's own
claim.

⭐ **`2026-08-02-15-004` is the reflexive obligation and it binds this plan against itself**: this plan
authors a scope-publication rule, so its own residual claims — in its PR body, its self-review rounds,
and its report — must publish `scope_searched` + `files_scanned` from the first round. A rule applied to
a sibling's work and not to one's own is not yet a rule.

- HYPOTHESIS (verify-at-outline, message-supplied): that each of the nine gaps is still open.
  Confirm/refute artifact: the candidate-surfacer set in `ext-self-review-plan-marshall`, checked per
  member for whether that case is already surfaced. ⛔ Several surfacers were added since these lessons
  were filed — check per member; do not assume the set is unchanged.

## Expected Surface

⛔ **Added 2026-08-08 — this spec was staged WITHOUT one, so the `next` verb's disjointness admission
test had nothing to read.** Re-verify against HEAD at outline.

- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/` — the
  candidate-surfacer set and its enumeration entry point.
- **HYPOTHESIS** (verify-at-outline): the enumeration's caller in the pre-submission-self-review step
  body, wherever the per-round scope is decided. The delta-scoping decision may live in the step rather
  than in the surfacer.
- **OBSERVED**: tests under `test/pm-plugin-development/**` covering the surfacer set.

## Dependencies and Sequencing — ⛔ CORRECTED 2026-08-08

The previous claim, *"Overlaps with no staged plan in this epic on file surface — verify at outline"*,
is **WRONG**. ⛔ **PLAN-PR-012 targets `ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
— the same skill.** That plan ADDS a detector; this plan changes WHAT THE ENUMERATION SCANS. The two are
complementary in intent and collide in file surface.

- ⛔ **Sequence with PLAN-PR-012, never pair.** ⭐ **Prefer PR-018 FIRST**: a new detector added by PR-012
  inherits whatever scope discipline this plan establishes, whereas the reverse order means PR-012's
  detector is authored against a scope rule that then changes underneath it.
- ⚠ **The reflexive trap applies to the pairing itself**: if PR-012 lands first and PR-018 then
  delta-scopes the enumeration, PR-012's detector may silently fall outside the scanned delta — the
  scope-of-sweep ≠ scope-of-claim failure, reproduced by the sequencing decision rather than by the code.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-018-self-review-rescans-the-whole-surface-every-round.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
