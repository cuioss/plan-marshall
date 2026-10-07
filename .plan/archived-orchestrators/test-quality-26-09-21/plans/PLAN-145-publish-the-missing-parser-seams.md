# PLAN-145: Publish the Missing Parser Seams and Close the Circular Import

epic: test-quality
workstream: WS-03

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator during epic ingestion.** Every item below was routed to PLAN-090 by a
> landed report and is **not** in what PLAN-090 actually shipped.

## Objective

PLAN-090's own brief called for a tree-wide `ParserSeamNotFound` re-derivation, and its report **explicitly
declined it** — *"a per-call-site read … not something this sweep replaces"* — scoping D1 to the 27 sites
PLAN-060 had named. PLAN-070 and PLAN-080 had already routed their own blockers there on the strength of
that brief. The result is a set of production gaps that are **formally owned and actually unowned**:
`effort_presets.py` and `manage_terminal_title.py` still publish no parser seam at HEAD, three directories
publish no top-level CLI script at all, one confirmed circular import sits behind an `E402` suppression, and
`credentials.py`'s coverage is the sole cause of a landed plan's verification shortfall. All are
`marketplace/bundles/**`, which is this workstream's exclusive tree. Close them, so **PLAN-150 can convert
what they block**.

## Deliverables

1. **D1 — Re-derive the blocked set tree-wide.** ⛔ **Gating, and it is the derivation PLAN-090 declined.**
   For every skill whose tests hand-build an argument namespace, determine whether its script publishes a
   seam `parse_ns` can call, and classify each into exactly one of:
   * **has a seam** — nothing owed;
   * **has a callable `main()` only** — `parse_ns` intercepts it; nothing owed;
   * **`ParserSeamNotFound`** — a seam must be published; **D2**;
   * **publishes no top-level CLI script at all** — ⛔ **a different shape**, and a seam is the wrong remedy;
     **D3**.

   ⚠️ **The distinction in the last two rows is the whole point of this deliverable.** PLAN-070 reported
   both shapes together and routed both to "missing parser seam", which is why the second never got a
   remedy anyone could act on.
   *Done when:* every skill carries exactly one class with the evidence for it; the counts are recorded with
   their commands; and the list of sites each blocked skill would unblock is stated, so **PLAN-150** can be
   sized from it.

2. **D2 — Publish the missing seams.** Add a `build_parser()` seam to each `ParserSeamNotFound` script,
   following the shape PLAN-090 already shipped for the `script-shared` build CLI
   (`_build_cli.py:588`, `_build_execute_factory.py:114`) and `credentials.py:29` — so the tree has **one**
   seam convention rather than a second.
   ⛔ **Named starting points, both confirmed missing at HEAD**:
   `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` and
   `marketplace/bundles/plan-marshall/skills/manage-terminal-title/scripts/manage_terminal_title.py`. **The
   full set is D1's output**, not this list.
   ⚠️ **A seam is a refactor of production code, so it carries its own tests.** Each new seam is exercised by
   a test that asserts the parser's own defaults reach the namespace — which is the property **B6** exists to
   protect and the reason a hand-built namespace is a correctness defect rather than bloat.
   *Done when:* every `ParserSeamNotFound` script from D1 publishes a seam; each is covered by a test
   asserting default propagation; and `parse_ns` resolves against each without raising.

3. **D3 — Decide the shape for the directories that publish no CLI script.** Three were named by PLAN-070 —
   `manage-lifecycle`, `build-server`, `q-gate-validation-agent` — and D1 may find more. A seam cannot be
   added to a script that does not exist, so the remedy is a **decision**, not a patch: either the skill's
   tests do not need `parse_ns` at all (its scripts are libraries, not CLIs, and **B6** does not apply), or
   a CLI genuinely is missing and that is a production gap of a different kind.
   ⛔ **Record the decision in the standard that teaches `parse_ns`**, so the next reader finds it rather
   than re-deriving the halt. Do **not** invent a CLI to satisfy a test convention.
   *Done when:* each such directory carries a recorded verdict with its reasoning, and
   `pm-dev-python:pytest-testing` / `plan-marshall:persona-module-tester` state that a library-only skill is
   outside **B6**'s scope, if that is the verdict.

4. **D4 — Report the measured deltas.** D1's full classification, one row per skill; the seams added; the
   D3 verdicts; the count of `parse_ns` call sites this plan **unblocks** (the input to PLAN-150's
   sizing); and the collected test count before and after.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: PLAN-090's D1 was scoped to the `script-shared` build CLI and `manage-providers` only, and its
  report **explicitly declined** the tree-wide re-derivation its own brief called for — read at
  `.plan/orchestrator/test-quality/archive/090-harness-and-rule-gaps/plan.md:316` and `report-01.md` § D1
- OBSERVED: `effort_presets.py` publishes no `build_parser` / `_build_parser` / `_build_arg_parser` and no
  callable `main()` at HEAD
  - verdict: corroborated | checked_at: 00b92fca | by: test-quality/cleanup | rescoped: n/a | evidence: re-run at HEAD 00b92fca: a combined grep for build_parser, _build_parser, _build_arg_parser and 'def main(' returns 0 in effort_presets.py AND 0 in manage_terminal_title.py. Both files re-read at HEAD rather than inferred - manage-terminal-title is one of the skills the window touched
- OBSERVED: neither `effort_presets` nor `manage_terminal_title` appears anywhere in PLAN-090's D1
  discussion across either of its reports — their only two mentions are in D3's unrelated `sys.modules`
  collision-name list
- OBSERVED: the seam convention already exists and is shipped — `_build_cli.py:588`,
  `_build_execute_factory.py:114`, `credentials.py:29` and `:153`
- HYPOTHESIS — **the whole of D1, and it is gating**: the blocked set is larger than the two named modules.
  PLAN-070 reported 2 `ParserSeamNotFound` blockers and 3 no-CLI directories **within its own slice alone**,
  and no run has ever derived the set tree-wide — confirm/refute by the D1 sweep (verify-at-outline)
  - verdict: contradicted | checked_at: 09f92b5e | by: test-quality/cleanup | rescoped: no | evidence: REFUTED by PLAN-145's own D1 at outline, filed via inbox message plan-145-...-001.md and corroborated by direct read this pass. The gating hypothesis predicted the blocked set is LARGER than the two named modules; D1's tree-wide sweep found it is ZERO. Of 118 entry-point scripts in marketplace/bundles/, 113 reach a parser seam and the 5 raising ParserSeamNotFound are all deliberate shapes (platform_runtime.py is a dispatch router whose raise is pinned as intended contract by a passing test; three are stdin-driven hooks with no argv contract; plan_logging.py is import-only). Modules owed a build_parser seam: 0. parse_ns call sites unblocked: 0. I independently verified the two named starting points publish no CLI at all - manage_terminal_title.py has zero argparse/main/build_parser hits and effort_presets.py's only two hits are DOCSTRING mentions of argparse at lines 379 and 381 - so both belong to D1's fourth class (no top-level CLI), not to ParserSeamNotFound. NOT re-scoped: the plan is parked at its 3-outline gate with outline already complete, so editing the spec now would change a brief that has already been consumed - the disposition is an operator decision, not a spec edit

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` — D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-terminal-title/scripts/manage_terminal_title.py` — D2
- HYPOTHESIS: further `ParserSeamNotFound` scripts across `marketplace/bundles/**` — **D1's output** (verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-python/skills/pytest-testing/**` and
  `marketplace/bundles/plan-marshall/skills/persona-module-tester/**` — D3's recorded verdict only
- OBSERVED: the tests for this plan's **own** production changes, under `test/plan-marshall/` in the
  directory mirroring each changed skill. ⚠️ **Only where a D2 seam requires its own test** — this plan
  does not otherwise edit `test/**`

## Dependencies and Sequencing

- Depends on: PLAN-090 (landed).
- **Split from a larger spec at cleanup.** Two unrelated production defects — the `github_ops` import
  cycle and `credentials.py`'s coverage — moved to **PLAN-165**. They shared this plan's tree but nothing
  else, and bundling them delayed the seams PLAN-150 is blocked on. See the epic's `## Decisions`.
- ⛔ **PLAN-150 depends on this plan**, and that is this plan's reason to go early: PLAN-150's ~506-site
  conversion cannot reach the sites these seams block.
- ⛔ **Must not run concurrently with PLAN-105** (§ D3 edits one analyzer in this tree; § D7 sweeps ~250
  files across it), **PLAN-160** or **PLAN-165** (same tree), or **PLAN-120** if its checker lands under
  `marketplace/bundles/**`.
- **May run concurrently with**: PLAN-130, PLAN-135, PLAN-140, PLAN-110, PLAN-155 — all of which are
  `test/`-only and touch this tree not at all. ⚠️ **The exception is this plan's own D2/D4/D5 tests**, which
  land under `test/plan-marshall/{skill}/` and could meet a campaign run in the same directory. Confirm the
  specific directories before pairing.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-145-publish-the-missing-parser-seams.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
