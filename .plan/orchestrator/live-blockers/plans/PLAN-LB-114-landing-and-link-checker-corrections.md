# PLAN-LB-114: Correct what the first three-layer reads found — the landing template and Step 4, the `verify-links` coverage edges, and the secure-logging text

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-114-landing-and-link-checker-corrections.md` and is queued as one row file, `queue/PLAN-LB-114.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word after the first landings read on three layers (PLAN-LB-111, PR #1908 at `8859bc1b0`, and PLAN-LB-113,
> PR #1909 at `144ccdbfc`). The findings are in `landings/PLAN-LB-111.md` and `landings/PLAN-LB-113.md`, section
> `## Three-Layer Analysis`. They come from two read-only leaves; the orchestrator re-read the points marked OBSERVED below at the
> cited lines before writing them. Points marked HYPOTHESIS are the leaves' account and were not re-read.

## Objective

The first two landings read on three layers each carried defects in merged code that the lane's report passed. This plan corrects them
in one unit, on three disjoint surfaces:

1. the landing-analysis template and `analyze.md` Step 4, which contain the only **major** finding: a layer-1 or layer-2 point that
   only a run could show has no slot in the template, so the template forces the "clean" Step 4's own limit forbids;
2. the `verify-links` checker, whose new `unchecked_link_classes` field still leaves several link forms neither verified nor named;
3. the secure-logging text, where the Java example contradicts the rule that owns it and two skills repeat each other.

No finding here is a blocker. The operator asked for the fixes, and the operator's standing preference is to fix a defect rather than
accept it.

## Deliverables

1. **The landing template and Step 4 can say "not shown by reading" at every layer, write the report once, and map a finding to a corpus verdict.**
   - `templates/landing-analysis.md`: the layer-1 and layer-2 summary slots and their per-layer verdict slots offer the same third value
     layer 3 has (`not shown by reading — N`), so a point only a run could show is never forced to `clean`.
   - `analyze.md` Step 4: the analysis block returns its result as data for item 1's single `Write` of the landing report. It no longer says
     to write `## Three-Layer Analysis` itself, so the report is written once, and the Inline-only APPLY index still names only item 1's
     Write.
   - `analyze.md` Step 4 routing: a mapping from the leaf's `verdict` and `severity` to the corpus vocabulary
     (`corroborated` / `contradicted` / `unverifiable`) that `corpus set-verdict` accepts, and a statement of which layers persist a
     verdict (layer 1 only, or layer 2 too). Two orchestrator runs persist the same value for the same finding.
   - The template's `Dispatch` line carries the same choice the section preamble does: `{one read-only leaf per landing | the orchestrator
     inline, because the dispatch did not return}`.
   - Return shape spelled once: `conformance[M]` in the leaf document, Step 4 and the tests (today `[N]` in Step 4, which reads as one row
     per finding).
   - `standards/three-layer-analysis.md`: a cross-repo landing names the other repository's path in a prompt field that is not
     `WORKTREE` (the envelope contract keeps `WORKTREE` repo-relative); and the leaf does not fetch PR bodies, comments or any other
     third-party text itself — it reads git, the repository and the files the prompt names, and the orchestrator passes anything else
     through the reader and `validate_struct` as Step 2 requires.

   *Done when:* doc tests assert the three-value slots at layers 1 and 2 in the template, that Step 4 names one report write and no second
   one, the verdict mapping and its layer scope, the two-valued Dispatch line, a single spelling of the conformance shape across
   `analyze.md`, the leaf document and the tests, the cross-repo prompt field, and the leaf's no-fetch rule. Each fails at HEAD.

2. **`verify-links` verifies or names every `link:` form it sees, and a bad target cannot abort the run.**
   - A target that is not relative to the containing file (leading `/` or `\`) is not joined onto the file's directory (which discards the
     directory and checks the host root). It is reported under `unchecked_link_classes` as its own class and is not `broken`.
   - A target whose `{attribute}` reference follows a leading `#` (`link:#{section-id}[x]`) is classed `attribute-reference`, not looked up
     as the literal anchor `{section-id}`. The `{` test runs before the `#` test.
   - A `link:` macro that the checker skips because it sits in an inline code span, in `+…+`, `++…++` or `pass:[…]` is counted and named
     under `unchecked_link_classes` (one class per mask), so the field says what it did not examine. The unconstrained `++…++` and the
     `pass:[…]` macro join the masked forms so a passthrough example is not reported `broken`. The existing masking is not removed: a
     documented syntax example in backticks must not become a false `broken`.
   - An `.adoc` target with a fragment whose file cannot be read (a directory named `x.adoc`, a permission error, a non-UTF-8 file) is
     reported as an issue on that link with the reason. It does not escape as an exception and abort a multi-file run.
   - A delimited block closes only on a delimiter of the same length that opened it, so a nested `----` line inside a `-----` listing no
     longer ends it early.
   - An anchor or fragment is percent-decoded before the lookup, as the path already is.

   *Done when:* fixture tests show each of the six cases above, red at HEAD: an absolute target is not `broken` and is named; `link:#{x}[y]`
   is `attribute-reference`; a link in a code span and in `++…++` is counted under its class; an unreadable `.adoc` fragment target yields an
   issue and the run completes with the other files' results; a nested longer block hides its inner `----` content until its own close; a
   `%`-encoded anchor that exists is not `broken`. The existing link-verify fixtures stay green unchanged.

3. **The secure-logging text states one rule in one home and its Java example follows it.**
   - `java-security-patterns.md` and `java-security/SKILL.md`: the `neutralise` example escapes a control character (for example as
     `\uXXXX`) instead of replacing it with `?`, so it follows the owning rule's "prefer escaping over dropping". The sentence that
     structured JSON "escapes all three" is replaced by what the JSON string grammar guarantees (quote, backslash and U+0000–U+001F) and
     says DEL, the C1 range and U+2028/U+2029 are still neutralised before the value is logged.
   - `java-security/SKILL.md` points at the patterns standard for the code and the paragraph instead of repeating them, which its own
     "no content duplication" statement requires.
   - `persona-security-expert`'s `secure-logging.md` names U+2028 and U+2029 in the set it owns, and scopes the `\p{Cntrl}` ASCII-only note
     to the default pattern flags (the character class widens under `UNICODE_CHARACTER_CLASS`).
   - `cui-logging`'s `logging-standards.md` names one owner for the value-neutralisation principle in both of its adjacent paragraphs.
   - `javadoc` Review Rules: the ordering-claim rule covers an ordering the method states about its own body as well as one the caller
     does not implement, matching `javadoc-method-documentation.md`.
   - `java-17-features.md`: the statement-exhaustiveness caveat says the check for an enhanced switch statement applies from the Java release
     that introduced pattern switches, and the unqualified "an exhaustive switch over an enum needs no `default`" line is qualified by it.
   - `test_domain_content_rules.py`: the assertion that the Java skill points at `secure-logging.md` is anchored to the new section, not to a
     link the skill already had.

   *Done when:* doc tests assert the escaping example, the narrowed JSON statement, the single code home with its pointer, U+2028/U+2029 and
   the flag scope in `secure-logging.md`, the single owner in `logging-standards.md`, the body-ordering clause in the `javadoc` rule, the
   release qualifier in `java-17-features.md`, and the anchored pointer assertion. Each fails at HEAD.

Split guard: three deliverables on three disjoint surfaces (the orchestrator skill, the AsciiDoc checker, the Java and security guidance),
each independent of the others, so any one can be dropped without touching another. D2 holds six edge fixes in one file; if the outline finds
them too many for one review, D2 is the natural split.

## Standing Constraints

- **Corrections only.** No new capability, no new verb, no new skill. The `landing-check` completeness check, the queue surface and START HERE
  are out of scope: START HERE showing a layer-3 verdict was the PLAN-LB-111 spec's premise and needs a queue-surface change, recorded as a Watch.
- **Fail closed in `verify-links`.** A form the checker did not examine is named, never reported as examined, and a syntax example in a code
  span does not become a false `broken`.
- **State once, point elsewhere.** The owning rule keeps the rule; the Java skill keeps the Java form and points to it.
- **Documentation standards.** Present-state wording; no dates, version numbers or changelog text in a bundle document.
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.
- **Tests state their purpose.** Every new or changed test states what it protects and is shown red at HEAD where its Done-when says so.

## Claim Labels

- OBSERVED: `templates/landing-analysis.md` L33 gives the layer-1 and layer-2 summary `{clean | findings}` and layer 3
  `{clean | findings | not shown by reading}`; L47 and L59 give the layer-1 and layer-2 verdicts `{clean | findings — N}`; the rows at L45
  and L57 allow `not_shown_by_reading` — read in the source tree at `8859bc1b0`.
- OBSERVED: `workflow/analyze.md` Step 4 says to write the result into `{epic_dir}/landings/PLAN-NN.md` under `## Three-Layer Analysis`, and
  item 1 at L186 then writes the whole report from the template including the three-layer analysis — both read at `144ccdbfc`.
- OBSERVED: the routing bullet derives the corpus value "from the layer-1 finding" and gives no mapping from the leaf's `verdict` and
  `severity` — read at `analyze.md` L182.
- OBSERVED: `_cmd_verify_links.py` classes a target by `startswith('#')` before `'{' in target` (L223-227), joins the target onto the file's
  directory (L354), reads an `.adoc` fragment target with `extract_anchors_from_file` and no handler (L367), blanks every code span before
  matching (L160), masks `+…+` only (L43, regex requires `[^+\s]` after the first `+`), and cuts a delimiter run to four characters
  (L56) — read at `144ccdbfc`.
- OBSERVED: `java-security-patterns.md` L57 replaces a control character with `?` and L63 says structured JSON "escapes all three";
  `secure-logging.md` L55 says "prefer escaping over dropping" and does not name U+2028/U+2029 — read at `144ccdbfc`.
- HYPOTHESIS (leaf account): `conformance[N]` at `analyze.md` L61 and L175 versus `conformance[M]` at `three-layer-analysis.md` L40, and the tests
  pin `[N]` (`test_analyze_three_layer_contract.py` L257 and L359). Verify-at-outline.
- HYPOTHESIS (leaf account): the execution-context envelope requires `WORKTREE` to be repo-relative and `orchestration-model.md` L325 fixes
  `WORKTREE: .`, so `three-layer-analysis.md` L14 has no legal field for another repository's path. Verify-at-outline against the ext-point
  contract before choosing the field name.
- HYPOTHESIS (leaf account): `java-security/SKILL.md` L88-105 repeats `java-security-patterns.md` L47-63 and SKILL.md L12 says "There is no
  content duplication". Verify-at-outline.
- HYPOTHESIS (leaf account): `logging-standards.md` L316 and L318 name two different owners for the same principle. Verify-at-outline.
- HYPOTHESIS (leaf account): `javadoc/SKILL.md` L154 covers only an ordering claim "the calling code does not implement" while
  `javadoc-method-documentation.md` L53 also covers ordering inside the method body. Verify-at-outline.
- HYPOTHESIS (leaf account): `test_domain_content_rules.py` L267 asserts `'secure-logging.md'` is in the Java skill, which the skill already
  contained, so it does not pin the new section. Verify-at-outline.
- HYPOTHESIS (not shown by reading): a `%00` in a `link:` target raises `ValueError` from `Path.resolve()` on some interpreters. Reproduce at HEAD
  before adding a case; if it does not reproduce, drop the case and record why.
- Verify-first clause (D2): add each of the six fixtures first and run them at HEAD. Each must be red for the reason stated. A case that is already
  green at HEAD is dropped, and the PR says which and why.
- Verify-first clause (D1): the leaf's account of the second write is a reading of two paragraphs. Re-read Step 4 as it stands on `main` at outline
  and keep only the correction that still applies.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` — layer 1 and 2 slots, the Dispatch line (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 4 single write, the verdict mapping, the conformance shape (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/three-layer-analysis.md` — the cross-repo field, the no-fetch rule, the conformance shape (D1)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_analyze_three_layer_contract.py` — assertions for D1
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` — only if the conformance spelling or the prompt field is pinned there (D1; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` — the six edges (D2)
- OBSERVED: `test/pm-documents/ref-asciidoc/test_asciidoc.py` — D2 fixture tests
- OBSERVED: `test/pm-documents/ref-asciidoc/fixtures/link-verify/` — D2 fixtures
- HYPOTHESIS: `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md` — the new unchecked classes (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/java-security/standards/java-security-patterns.md` — the escaping example and the JSON statement (D3)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/java-security/SKILL.md` — the pointer in place of the repeated code (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secure-logging.md` — U+2028/U+2029 and the flag scope (D3)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java-cui/skills/cui-logging/standards/logging-standards.md` — one owner (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/javadoc/SKILL.md` — the ordering rule's scope (D3; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md` — the release qualifier (D3)
- OBSERVED: `test/pm-dev-java/doc-contracts/test_domain_content_rules.py` — D3 assertions and the anchored pointer

## Dependencies and Sequencing

- **Depends on:** none. Both source plans are merged.
- **Overlaps with PLAN-LB-69 (parked)** on `workflow/analyze.md` Step 4 and `templates/landing-analysis.md`. Its D1 adds a two-leaf audit to the same step:
  land this plan first, and reconcile LB-69's D1 against the leaf, the return shape and the single report write that result from D1 here.
- **Overlaps with PLAN-LB-105 (running)** only if its deliverables edit `analyze.md` or the landing template; read its Expected Surface at emit.
  The gate decides, and a shared file is reported to the operator.
- **Overlaps with PLAN-LB-113 (shipped)** on `_cmd_verify_links.py`, `test_asciidoc.py`, the Java security files and `test_domain_content_rules.py`;
  its content is in `main` and this plan edits it.
- **Not carried, and why.** START HERE showing a layer-3 verdict needs a queue-surface and `landing-check` change the PLAN-LB-111 spec put out of scope.
  It is recorded as a Watch. The `execution-context-reader` variant for the leaf (the lane's injection-hardening follow-up) is a plan-level decision for
  the operator and is not carried here; D1's no-fetch rule is the in-scope mitigation. Measurement (`total_tokens`) is out of scope under the focus rule.
- **Running plans:** checked at emit by the disjointness gate; none were checked in this draft.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-114-landing-and-link-checker-corrections.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
