# PLAN-120: Derive the Partition and the Budget Attribution

epic: test-quality
workstream: WS-06

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> ⛔ **RE-SCOPED ON INGESTION — read this before the objective.** The original plan
> ([`archive/120-derive-the-epics-cross-file-sets.md`](../archive/120-derive-the-epics-cross-file-sets.md),
> preserved verbatim) derived **three** sets from `doc/plans/test-quality/`'s documents and gated a CI
> check on any document disagreeing. Two of the three are now provided **structurally** by this ledger
> and the third is not:
>
> | Original set | Status after ingestion |
> |---|---|
> | The **collision matrix** | **Superseded.** `orchestrator corpus cross-check` derives pairwise surface overlap from each spec's own `## Expected Surface`. Nothing hand-maintains it any more |
> | The **queue / ownership table** | **Superseded.** The Ordered Queue is a GENERATED block rendered from `status.json`; hand-editing it is prohibited by construction |
> | The **partition** — every `test/` entry mapped to the plan claiming it | ⛔ **NOT provided.** Nothing walks `test/`. An entry claimed by **no** plan is invisible to every ledger verb, and it is the defect that halted four consecutive runs |
> | The **per-slice budget attribution** | ⛔ **NOT provided.** Nothing groups the doctor's findings by owning plan |
>
> The CI gate is also gone: the specs are git-ignored, so no build can read them. What remains is a
> **read-only derivation tool**, and this spec is scoped to exactly that.

## Objective

An entry under `test/` that no plan claims looks exactly like a clean run — which is why four
consecutive runs each halted on `test/pm-code-intelligence/`, escalated, and were told to proceed: the
same defect, dispositioned four times, because each disposition was about that run rather than about the
partition. Build the derivation that makes an unclaimed entry a **reported fact** rather than something
each run rediscovers by hand, and group the module-budget findings by owning plan so a campaign run can
be sized without a manual attribution pass.

## Deliverables

1. **D1 — Parse what is declarative, and classify what is not.** ⛔ **Gating.** A script that reads every
   plan spec under `.plan/orchestrator/{epic}/plans/` and extracts, per plan, the `test/` paths its
   `## Expected Surface` claims and its `## Out of Scope` excludes. **Parse, do not hand-list** — a
   hard-coded plan list in this script is the same defect this plan exists to close, one level down.
   ⛔ **Not every Expected Surface is declarative, and the derivation must say so rather than guess.**
   Each plan lands in exactly one of three classes: **declarative** (paths a parser resolves), **derived**
   (its surface is a function of other plans' — PLAN-140's is), or **prose** (neither). The first two are
   usable; the third is reported.
   *Done when:* every spec carries exactly one class with the evidence for it; a spec added afterwards is
   picked up with **no edit to the script**; the tests pin the parse of each entry shape the epic actually
   uses (a directory, a glob, a named file, an exclusion, a conditional, an `OBSERVED:`/`HYPOTHESIS:`
   label prefix); and **a spec whose class cannot be determined halts the run** rather than defaulting.

2. **D2 — Derive the partition and the attribution, and report every disagreement.** From D1's model plus
   the doctor's `test-conventions` sweep, compute:
   * **the partition** — every entry under `test/` mapped to the plan whose Expected Surface claims it,
     with **unclaimed** and **multiply-claimed** entries reported separately;
   * **the per-slice attribution** — `test-module-line-budget` findings grouped by owning plan.

   ⛔ **"Unclaimed" and "claimed by a plan I cannot parse" are different verdicts and must never be
   merged.** A `test/` entry claimed only by a **prose**-class plan is reported as *coverage the
   derivation cannot see*, never as a partition defect — otherwise the check manufactures false
   disagreements out of its own parser's limits. D1's three-class model is what makes that expressible.
   ⛔ **The check must be observed failing.** Add a directory no spec claims, add a path to two specs, and
   confirm it reports each. A checker never observed failing is not a checker.
   ⚠️ **A known-good baseline exists to validate against**: at HEAD `2cd1a19c` the whole-tree
   `test-module-line-budget` count is **267** and the per-slice attribution sums to it **exactly, with no
   residual bucket** — 030:40, 040:57, 050:3, 060:55, 070:62, 080:49, and 1 for PLAN-010's rule-test
   glob. **Re-derive it; do not trust it.** If the derivation reproduces that partition, it is working.
   *Done when:* the check reports both derived sets with their sizes, distinguishes the three verdicts
   (claimed / unclaimed / not-derivable), reports each injected disagreement with a message naming the
   entry, and **states every disagreement it finds against the tree as it stands rather than silencing
   it** — this is the first thing ever to compute the answer, so finding some is the expected outcome.

3. **D3 — Report the derived sets and what the derivation could not see.** The partition, the attribution,
   every unclaimed and multiply-claimed entry per instance, every prose-class spec whose paths the
   derivation cannot resolve, the injected-failure demonstrations for D2, and the collected test count
   before and after.
   ⛔ **The "not-derivable" list is the deliverable's most important half**, not a footnote: it is the
   exact measure of how much of the epic's ownership still rests on prose a tool cannot check.
   *Done when:* the report carries all six, each with the command that produced it.

## Claim Labels

- OBSERVED: nothing walks `test/` to find entries no plan claims — read at
  `.plan/orchestrator/test-quality/` (`corpus enumerate` reconciles queue↔specs; `corpus
  cross-check` derives pairwise overlap; neither reads the test tree)
- OBSERVED: a defect of this class appeared in **every one of nine** verification rounds, and three
  structural remedies failed — the last two by contradicting themselves **inside their own commit** —
  read at `.plan/orchestrator/test-quality/archive/report-authoring-02.md` § Findings and § "The stop record"
- OBSERVED: four consecutive runs each halted on `test/pm-code-intelligence/` before it was assigned to
  PLAN-080 — read at `.plan/orchestrator/test-quality/archive/README.md` § "The partition, and how a run re-derives it"
- OBSERVED — **verified during ingestion, and it is D2's validation target**: the whole-tree budget count
  is 267 at HEAD and the per-slice attribution sums to it exactly with zero duplicate file attributions
  - verdict: contradicted | checked_at: 00b92fca | by: test-quality/analyze | rescoped: no | evidence: refuted at HEAD 00b92fca. The claim asserted the whole-tree budget count is 267 and that the per-slice attribution sums to it exactly with zero duplicate attributions. Both halves are now false: the population is 279 (three independent methods agree exactly), and the attribution does not sum per slice at all - it returns a single multiply-claimed bucket holding all 279 findings. rescoped: no - PLAN-120 is SHIPPED and a shipped spec is history, never re-scoped. The claim was PLAN-120's own D2 validation target and the plan duly re-derived it and reported the disagreement, which is exactly what the spec instructed. The live successor is PLAN-170
- HYPOTHESIS — **gating for D1; re-derive the classification, the count is a lead**: **not** every spec's
  `## Expected Surface` is parseable into a set of `test/` paths — confirm/refute by reading every spec's
  Expected Surface and classifying each entry's shape (verify-at-outline). PLAN-140's is derived from
  other plans'; PLAN-105's names a location by convention; several carry `HYPOTHESIS:` label prefixes and
  `⛔`/`⚠️` markers the parser must tolerate
- OBSERVED — **an asserted absence, verify it**: no CI gate can read the specs, because
  `.plan/` is git-ignored and absent from a fresh clone. This is why D3 reports rather than gates

## Expected Surface

- HYPOTHESIS: a new script under the repository's own tooling, placed per
  `pm-plugin-development:plugin-script-architecture` — read that skill for where a script of this kind
  belongs and follow it rather than choosing a location here (verify-at-outline).
  ⛔ **If the standard places it under `marketplace/bundles/**` it enters WS-03's exclusive tree** —
  check the sequencing below before writing, and say in the report which location the standard gave
- OBSERVED: `test/pm-plugin-development/` — the most likely home for this checker's tests, since the
  script-architecture standard places skill scripts under `marketplace/bundles/{b}/skills/{s}/scripts/` and
  **B10** mirrors that path within `test/`. ⚠️ **A lead, not a decision** — D1 settles it, and the row below
  is the rule the settlement must satisfy
- OBSERVED: that script's tests, under `test/` — `pyproject.toml` sets `testpaths = ["test"]` and
  `python_files = ["test_*.py"]`, so a module outside that tree is never collected
  ⛔ **The test location must land inside a directory an existing spec already claims, or this plan
  creates the very defect it exists to detect.** Check the partition first; prefer a claimed directory.
  If the script-architecture standard forces a **new** entry, this spec's own Expected Surface is
  amended by the orchestrator to claim it — file an inbox message rather than editing any other spec
- OBSERVED: this plan **modifies no existing test module and no other plan's spec**

## Dependencies and Sequencing

- Depends on: nothing. ⛔ **Land it earliest of what remains** — it checks the ownership every other plan
  is executed from, and nine verification rounds established that nothing else does.
- Overlaps with: **PLAN-145 / PLAN-160 / PLAN-105** — conditionally, and only if the script-architecture
  standard places the checker under `marketplace/bundles/**`. If it admits a non-bundle location this
  overlap is **inert** and the report says so.
- Adjacent to: the whole `test/` tree, which this plan **reads and never writes**.

## Out of Scope

- **Editing any spec to resolve a disagreement this check finds.** A run that writes the checker and
  edits what it checks can make the check pass by moving either side, and no independent verdict is left.
  **Report the disagreements and let the orchestrator resolve them.** This is the single most available
  wrong move in this plan.
- **Deriving the collision matrix.** Superseded by `orchestrator corpus cross-check`. Building a second
  implementation is the outcome this epic's own cleanup contract forbids.
- **Gating a build on the result.** Impossible — the specs are git-ignored.
- **Generalising the checker beyond this epic.** Other epics have different section conventions.
- **Any `test/` refactoring**, and **changing the doctor's rules or output format** (WS-03's — a shape
  that makes the derivation impossible is **recorded** for it).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-120-derive-the-partition-and-the-budget-attribution.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
