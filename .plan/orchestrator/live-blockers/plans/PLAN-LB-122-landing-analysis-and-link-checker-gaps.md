# PLAN-LB-122: The verdict mapping covers a finding that confirms a premise, and `verify-links` names every link it hides

epic: live-blockers
workstream: WS-03

> Plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-122-landing-analysis-and-link-checker-gaps.md`. This spec is NOT queued: the operator asked for the follow-up
> plans to be specced and not staged, so no row file exists. The orchestrator EMITS the command below; it never launches the plan
> inline, and a row is added when the operator launches it.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Specced on the operator's word (decision 13): the fix plan for the PLAN-LB-114 findings (PR 1915, merge `3404d904c`; report
> `landings/PLAN-LB-114.md`). Every finding id below (L1-n, L2-n, L3-n) is that report's. The points the orchestrator re-read at their
> lines are OBSERVED; the points the analysis leaf read and the orchestrator did not re-read are HYPOTHESIS and are settled first.
>
> Ruling check. D1 is a gap in the tool the orchestrator uses to read every landing (a wrong `contradicted` on a staged claim blocks that
> spec at the prep-ready test), graded high. D2 is a checker that reports an unexamined form nowhere, against its own fail-closed
> constraint (high). D3 and D4 are minor and separable. No token or measurement work. No Sonar.

## Objective

PLAN-LB-114 corrected the landing template, the link checker and the secure-logging text. Its verdict mapping still has no row for a
finding that confirms a premise, its two masks erase some live links without counting them, and the owning secure-logging standard still
states the claim its Java leaf narrows.

After this plan every leaf finding maps to exactly one corpus verdict or to none, by a stated rule; `verify-links` counts or names every
link form it masks, including the passthrough forms that hide `xref:` and `<<anchor>>`; the owner of the secure-logging rule states the
narrowed claim; and the checker's remaining edges and the guide texts say what holds.

## Deliverables

1. **The Step 4 verdict mapping is total, and a confirming finding is never a contradiction.** *(L1-1, L1-2, L1-3, L2-2; high)*
   - A leaf finding carries layer, severity, file, line, claim and verdict, and no polarity (`three-layer-analysis.md:39-43`). The mapping
     in `analyze.md:184-187` reads a `checked` finding as "found it wrong". The leaf return carries a polarity — the finding says whether
     the premise holds or fails — or the mapping takes it from the finding's layer and kind; the choice is recorded at outline.
   - The bullet at `analyze.md:182` ("a claim this layer corroborates is persisted by `corpus set-verdict`") and the statement at
     `:189` ("a layer-1 finding never yields `corroborated`") no longer contradict each other: one rule states which verdicts a layer
     persists.
   - The never-downgrade rule covers every settled verdict, not only `corroborated`: a `not_shown_by_reading` finding never overwrites a
     claim that Step 2b settled as `contradicted`, and two findings on one claim with different verdicts have a stated precedence
     (`analyze.md:189`).
   - The doc test derives the verdicts from the mapping and asserts the mapping table is total over the leaf's verdict values, instead
     of hard-coding the corpus verdicts (`test_analyze_three_layer_contract.py:546-560`).

   *Done when:* a doc test fails at HEAD for a mapping that has no row for a `checked` finding that confirms a premise; a test over the
   mapping shows each leaf verdict value maps to one corpus verdict or none; a contradiction between the two `analyze.md` statements
   fails the test; a downgrade of `contradicted` by `not_shown_by_reading` is refused by the stated rule.

2. **`verify-links` counts or names every link form its masks hide.** *(L3-1, L3-2, L1-4; high)*
   - A `link:` macro whose target is itself wrapped in a passthrough (`link:++https://example.org/a_b++[x]`,
     `link:https://x/?q=+foo+[y]`) is counted: the mask no longer erases the macro prefix together with the target, so the link is in
     `total_links`, `issues` or `unchecked_link_classes` (`_cmd_verify_links.py:14-17,74,105-106,293`).
   - `xref:` and `<<anchor>>` hidden by the same masks (`++…++`, `pass:[…]`, a code span) are counted under their mask class, not only
     `link:` (`:105,255-292`). The parent extracted and checked the `++` and `pass:[` forms; the coverage lost is restored or the form is
     named, never silent.
   - `ref-asciidoc/SKILL.md` states the guarantee the code gives ("a macro the checker skipped is counted") and no more.

   *Done when:* fixtures show `link:++url++[x]`, `link:…+foo+[y]`, `++xref:missing.adoc[x]++`, `pass:[<<a>>]` and a code span carrying
   `xref:a.adoc[b]` each counted or named (red at `3404d904c`); a syntax example in backticks is still not `broken` (control); the
   existing link-verify fixtures stay green unchanged.

3. **The secure-logging owner states the narrowed claim.** *(separable; L3-3)*
   - `persona-security-expert/standards/secure-logging.md:54-55` no longer says JSON "automatically escape[s] CRLF and special
     characters, so forged entries cannot be injected": it states what the JSON string grammar guarantees (quote, backslash and
     U+0000–U+001F) and that DEL, the C1 range and U+2028/U+2029 are still neutralised before the value is logged. The regex arm of
     `:55` includes U+2028/U+2029. The Java leaf points at the owner for the claim, since the owner holds the rule.

   *Done when:* a doc test asserts the narrowed statement and the U+2028/U+2029 mention in the owner and a pointer, not a restatement,
   in `java-security-patterns.md`; it fails at `3404d904c`.

4. **The checker's remaining edges and the guide texts state what holds.** *(separable; L2-1, L2-3, L3-4 to L3-7)*
   - `xref:/etc/hostname[x]`: an absolute xref target is not joined onto the file's directory, and an xref target is percent-decoded
     as its anchor is. A self-referencing symlink does not abort a multi-file run (`RuntimeError` from `Path.resolve` is handled with
     the other path errors; an interpreter-dependent shape is confirmed first). A double-backtick span pairs correctly. A run whose
     only failures are unreadable targets does not report `broken_links 0` beside `status: failure`.
   - The comment "outermost first" states the real order; an unterminated or mismatched-length block is named, not silent.
   - Tests: the cross-file fragment decode, the xref anchor decode and the unreadable-fragment shapes other than a directory named
     `x.adoc` (a permission error, a non-UTF-8 file) are tested; the test anchor with a space is replaced by one Asciidoctor registers;
     the guard `test_the_inline_only_index_names_only_the_item_one_write` is labelled a guard in its docstring; the D3 assertion that
     holds at the parent is dropped or tightened.
   - Dangling references: "§ Worktree-Resolution Root" in `agents/execution-context.md:37` names the heading that exists; the ext-point text
     names a field only under a section that declares it; `logging-standards.md:319` points at the owner and does not restate its
     check set; the leaf document and the dispatch prompt agree on the corpus read (`three-layer-analysis.md:12`); the
     `WORKTREE` / other-repository paragraph is pinned by a test.

   *Done when:* each shape above is a fixture red at `3404d904c` (the interpreter-dependent symlink case is a fixture or is dropped with
   the reason recorded); a read of each cited line shows the wording corrected.

Split guard: four deliverables on three disjoint surfaces (the orchestrator skill, the AsciiDoc checker, the security guidance). D1 and
D2 are independent of each other; D3 and D4 are the first to split off, D4 first. A split runs in sequence only where two deliverables
touch one file.

## Standing Constraints

- **Settle each HYPOTHESIS first.** A refuted claim is dropped from its deliverable, not worked around, and the PR says so.
- **Corrections only.** No new verb, no new skill. The `landing-check` completeness check, the queue surface and START HERE stay out of
  scope.
- **Fail closed in `verify-links`.** A form the checker did not examine is named, never reported as examined, and a syntax example in a
  code span does not become a false `broken`.
- **State once, point elsewhere.** The owning rule keeps the rule; the Java skill keeps the Java form and points to it.
- **Documentation states the current behaviour.** No comment or doc describes a change or the old behaviour.
- **Tests state their purpose**, use the `PLAN_MARSHALL_HOME` fixture, and are shown red at `3404d904c` where a Done-when says so;
  counts come from an enumeration, not a hand list.
- **No token or measurement work.** **No Sonar.**

## Claim Labels

- OBSERVED: the routing table's `checked` row reads "the reading settled the point and found it wrong", and a leaf finding carries no
  polarity — `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` L184-187 and `.../standards/three-layer-analysis.md` L39-43.
- OBSERVED: the routing bullet says a claim this layer corroborates is persisted and also that a layer-1 finding never yields
  `corroborated` — `analyze.md` L182 and L189; the never-downgrade rule names only `corroborated` — L189.
- OBSERVED: a mask counts a `link:` macro only when it lies wholly inside the masked text, and `_LINK_MACRO_RE` needs a non-blank
  target, so `link:++url++[x]` is in no count — `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` L14-17,
  L74, L105-106, L293.
- OBSERVED: the masks hide `xref:` and `<<anchor>>` and only `_LINK_MACRO_RE` is counted — `_cmd_verify_links.py` L105, L255-292.
- OBSERVED: the owning standard states "automatically escape[s] CRLF and special characters" and the Java leaf narrows it —
  `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secure-logging.md` L54-55 and
  `marketplace/bundles/pm-dev-java/skills/java-security/standards/java-security-patterns.md` L69.
- OBSERVED: the target resolution catches `(OSError, ValueError)` — `_cmd_verify_links.py` L403-405.
- HYPOTHESIS: `cmd_corpus_set_verdict` does not refuse a downgrade of a corroborated verdict, so the never-downgrade rule is
  procedural only — confirm/refute at `plan-orchestrator/scripts/` § `corpus set-verdict` (verify-at-outline). It decides whether D1
  adds a script refusal or only the text rule.
- HYPOTHESIS: `_cmd_verify_links.py:474,496` (the xref path), `:63` (the double-backtick pairing), `:654` (the unreadable-only counts)
  and `:80,232,124,633,458,282` read as the report says — confirm/refute at outline; they are leaf readings, not re-read (D4).
- HYPOTHESIS: a self-referencing symlink raises `RuntimeError` from `Path.resolve` under Python 3.12 — confirm by a run before adding
  the case (verify-at-outline). The interpreter behaviour is external.
- HYPOTHESIS: the dangling references and the restated check set read as the report says (`execution-context.md:37`,
  `ext-point-execution-context-workflow.md:67`, `logging-standards.md:319`, `doc_references.py:23`) — confirm/refute at outline (D4).
- Verify-first clause (D1, D2): add each fixture first and run it at `3404d904c`; each must be red for the reason stated. A case that
  is already green is dropped and the PR says which and why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 4 routing, L182-189 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/three-layer-analysis.md` — the finding shape, the corpus-read sentence (D1, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` — only if D1 changes the leaf's finding shape (D1; verify-at-outline)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_analyze_three_layer_contract.py` — the mapping tests (D1)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` — the masks, the xref path, the edges (D2, D4)
- OBSERVED: `test/pm-documents/ref-asciidoc/test_asciidoc.py` — fixture tests (D2, D4)
- OBSERVED: `test/pm-documents/ref-asciidoc/fixtures/link-verify/` — fixtures (D2, D4)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md` — the guarantee sentence (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secure-logging.md` — L54-55 (D3)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/java-security/standards/java-security-patterns.md` — the pointer (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — the set-verdict refusal, only if the outline chooses a script rule (D1; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/agents/execution-context.md` and `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md` — the dangling references (D4; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java-cui/skills/cui-logging/standards/logging-standards.md` — L319 (D4; verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/pm-dev-java/test_domain_content_rules.py` — the pointer assertion for D3 (verify-at-outline)

## Dependencies and Sequencing

- **Depends on:** the merge of PLAN-LB-114 (`3404d904c`), which is on the base branch.
- **Overlaps with parked PLAN-LB-69** on `analyze.md` Step 4 and the landing template: reconcile PLAN-LB-69 D1 against this plan's
  result before it is un-parked. The disjointness gate decides the pairing at emit.
- **Adjacent to** (left untouched): the landing-check completeness check, the queue surface, the corpus verdict storage.
- **Owed outside this plan, operator-run:** a harness sync after merge. No verb or flag is added unless the outline chooses a
  script refusal in D1; then an executor regeneration is owed and the landing says so.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-122-landing-analysis-and-link-checker-gaps.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
