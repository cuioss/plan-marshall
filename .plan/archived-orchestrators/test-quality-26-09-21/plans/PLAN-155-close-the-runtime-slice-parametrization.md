# PLAN-155: Close the Runtime Slice's Parametrization

epic: test-quality
workstream: WS-02

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator during epic ingestion.** PLAN-060's D4 parametrization half is the largest
> item in the epic with **no owner anywhere** — it appears in neither the scoping brief's "now owned
> elsewhere" column nor its collision matrix.

## Objective

**B5** — *parametrize the table, not the prose* — is the epic's single largest available reduction and the
corpus's least-used tool. PLAN-060 ran three times and converted **one** family of roughly 224, leaving
~223 at ≥80% skeleton similarity across ~4,554 lines. It did not defer this for lack of budget alone: the
similarity set **includes `script-shared`'s deliberate matched positive/negative control pairs**, which look
exactly like a tabular family and must **not** collapse — so every candidate needs a read, and a run that
treats the similarity list as a work queue will destroy controls. That read is what this plan is for. Its
**required cold read was also never performed**, across all three runs.

## Deliverables

1. **D1 — Re-derive the family set and classify every member.** ⛔ **Gating and halting.** Cluster the
   slice's test functions by skeleton similarity and classify each cluster into exactly one of:
   * **tabular family** — the members differ only in input and expected output; **collapse it**;
   * **matched control pair** — a positive and a negative case deliberately written apart so a reader sees
     both; ⛔ **leave it, and name it**;
   * **similar but not equivalent** — the members differ in setup, in what they assert, or in why they
     exist; **leave it, and name why**;
   * **already parametrized** — nothing owed.

   ⚠️ **The similarity metric is the input to this classification, never its output.** A cluster is a
   candidate, not a verdict.
   *Done when:* every cluster carries exactly one class with its evidence; the counts are recorded with the
   command that produced them; and any cluster that cannot be classified has halted the run with it named.

2. **D2 — Collapse the tabular families.** One `@pytest.mark.parametrize` per family.
   ⛔ **The `ids=` list is where the removed prose goes**, carrying what the collapsed docstrings said —
   without it the failure output names a tuple index instead of a case, and the reduction has traded
   readability for line count.
   ⛔ **Parametrizing raises the collected item count; it must never lower it.** That is the guard separating
   simplification from deletion, and it is measured before and after.
   *Done when:* the collected item count is **unchanged or higher**; every collapsed family is named with its
   member count; and no cluster classified as a control pair or as non-equivalent has been touched.

3. **D3 — Perform the cold read PLAN-060 owed three times and never did.** Dispatch a sub-agent with a
   sample of the collapsed families' resulting code and `ids=` lists — **and no other context**: not this
   spec, not the diff, not the original docstrings — and ask, per case, what contract it pins and why that
   contract is load-bearing.
   ⛔ **The `ids=` list is the thing under test.** If the reader cannot say what a case asserts, or cannot
   distinguish two cases, the collapse destroyed information however good the line delta looks. **Fix the
   `ids=`, not the reader.**
   *Done when:* the answers are recorded **verbatim**, every case the reader could not explain is repaired,
   and the repaired cases are re-read.

4. **D4 — Report the measured deltas.** The cluster classification, one row per cluster with its class and
   evidence; the families collapsed and their member counts; the control pairs **left, by name** — this is
   the deliverable's most important row, because it is the evidence the run did not destroy them; the
   collected item count before and after; the line delta, **reported not targeted**; the skipped count; and
   the wall-clock with its population named.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: PLAN-060 converted **one** family (`TestMalformedDeclarations`, −91 lines) and explicitly
  deferred the rest — read at `.plan/orchestrator/test-quality/archive/060-runtime-and-script-substrate-test-reduction/report-01.md` § D4
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: confirmed at archive/060-runtime-and-script-substrate-test-reduction/report-01.md:181, TestMalformedDeclarations eleven tests differing only, consistent with the one-family conversion
- HYPOTHESIS — **re-derive; it sizes the whole plan**: ~223 families remain at ≥80% skeleton similarity
  across ~4,554 lines — confirm/refute by re-running the clustering over the slice's fourteen directories
  (verify-at-outline). ⛔ **The figure is a lead and the *classification* matters more than the count**: an
  unclassified similarity list is not a work queue
  - verdict: unverifiable | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: re-deriving requires running the skeleton-similarity clustering over the slice's fourteen directories; not executed in this read-only pass and no simpler proxy exists for a cluster count
- OBSERVED — ⛔ **and it is why this plan is a read, not a sweep**: the ≥80% similarity set includes
  `script-shared`'s matched positive/negative control pairs, which must not collapse — recorded by PLAN-060
  as its stated reason for deferring
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: confirmed at report-01.md lines 190, 380 and 622 - matched positive/negative control pairs are explicitly excluded from the 80 percent collapse set
- OBSERVED: D4's required cold read was **never performed**, across all three of PLAN-060's runs
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: confirmed at report-01.md lines 429, 544 and 630 - D4's required cold read is listed as never performed across all three runs
- OBSERVED: this deliverable appears in **neither** the epic brief's "now owned elsewhere" column nor its
  collision matrix — read at `.plan/orchestrator/test-quality/archive/README.md` § "What the executed half left open", the `060` row
  - verdict: corroborated | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: n/a | evidence: archive/README.md's 060 row at line 490 routes over-budget modules, latent sys.modules registrations and structurally-unfixable preambles elsewhere, and D4 parametrization is absent from that routing list
- OBSERVED: the slice holds **61** modules over the 400-line budget at `bf1b7ed6` (re-scoped from 55, and
  from 60 at `9fd095718`). ⛔ **The "exactly one class exceeds the budget alone" premise needs
  re-derivation**: `test_claude_runtime.py` has grown to **5,394** lines and `TestInstallTerminalTitleHooks`
  now starts at `:604` (was 663 lines at `:482`), so neither the class's size nor its uniqueness was
  re-confirmed at this HEAD.
  ⛔ **Not this plan's** — WS-04's campaign owns the splits, and parametrizing will change which modules are
  over budget, so this plan **reports** its effect on that count and does not act on it
  - verdict: contradicted | checked_at: bf1b7ed6 | by: test-quality/cleanup | rescoped: yes | evidence: doctor line-budget findings over PLAN-155's 14 slice directories total 61 at bf1b7ed6, not the recorded 55 (60 at 9fd095718); test_claude_runtime.py has grown to 5394 lines with TestInstallTerminalTitleHooks now starting at :604 rather than 663 lines at :482, so the exactly-one-class premise is no longer confirmed. Re-scoped on both count and premise

## Expected Surface

⚠️ **This is PLAN-060's slice, enumerated so the disjointness check can resolve it. Re-derive it from
PLAN-060's own spec at outline** rather than trusting the transcription.

- OBSERVED: `test/plan-marshall/extension-api/`
- OBSERVED: `test/plan-marshall/lsp-client/`
- OBSERVED: `test/plan-marshall/manage-files/`
- OBSERVED: `test/plan-marshall/manage-logging/`
- OBSERVED: `test/plan-marshall/manage-providers/`
- OBSERVED: `test/plan-marshall/platform-runtime/`
- OBSERVED: `test/plan-marshall/ref-toon-format/`
- OBSERVED: `test/plan-marshall/script-shared/` — ⛔ **the control-pair directory; the highest-risk part of
  the surface and the reason D1 is gating**
- OBSERVED: `test/plan-marshall/tools-file-ops/`
- OBSERVED: `test/plan-marshall/tools-input-validation/`
- OBSERVED: `test/plan-marshall/tools-permission-doctor/`
- OBSERVED: `test/plan-marshall/tools-permission-fix/`
- OBSERVED: `test/plan-marshall/tools-script-executor/`
- OBSERVED: `test/plan-marshall/untrusted-ingestion/`
- OBSERVED: `test/conftest.py` — ⛔ **added by the orchestrator from PLAN-150's landing, not transcribed from
  PLAN-060.** PLAN-150 ran this same conversion on the architecture slice and touched `test/conftest.py`
  (+12 lines, the shared `parse_ns` helper) while its own Expected Surface declared 29 paths all under
  `test/plan-marshall/` and omitted it. This plan is the identical conversion on PLAN-060's slice and will
  reach the same file. The declaration matters because `test/conftest.py` is **also claimed by PLAN-020,
  PLAN-090 and PLAN-110** — leaving it undeclared makes the disjointness gate pass a PLAN-155/PLAN-110
  pairing it should sequence. See `landings/PLAN-150.md` § Deliverable Fidelity vs Spec.
- OBSERVED: **no `marketplace/bundles/**` file**, **no module split**, and **no docstring rewrite for B3** —
  those are WS-03's, WS-04's and PLAN-130's respectively

## Dependencies and Sequencing

- Depends on: PLAN-010, PLAN-020 (landed). Nothing else blocks it.
- ⛔ **Must not run concurrently with**: PLAN-140 run 3 (the same slice), PLAN-130 or PLAN-135 (both sweep
  every slice — and PLAN-130 rewrites docstrings this plan is collapsing into `ids=` lists, which is the
  worst pairing in the epic), PLAN-110 (`lsp-client/`, `platform-runtime/`, `tools-file-ops/` carry its skip
  sites and its absent-dependency stub).
- **May run concurrently with**: PLAN-150 (PLAN-070's slice, disjoint), PLAN-120, PLAN-145's production half.
- ⚠️ **Sequence PLAN-130 before this plan, not after.** PLAN-130 rewrites docstrings; this plan folds
  docstrings into `ids=` lists. Doing them in the other order means PLAN-130 rewrites prose this plan has
  already moved, and the `ids=` entries silently fall out of the rule's view.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-155-close-the-runtime-slice-parametrization.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
