# PLAN-LB-113: Domain-content gaps close — Java review rules and guidance, secure-logging guidance, and a link checker that says what it did not check

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-113-domain-content-gaps.md` and is queued as one row file, `queue/PLAN-LB-113.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged in the 2026-11-04 inbox drain on the operator's instruction ("put all the domain changes into one plan"). The seven
> findings were first discarded under the focus rule and then reversed at the operator's request; this is the one plan that carries
> all of them. Source findings, all routed by `lessons-routing` and checked at `f6830b837`:
> - `-077` javadoc (medium), `-078` junit-core (medium), `-079` test spec citations (low), `-080` bidi characters in
>   cui-http-testing (low), `-081` java-core switch statement (medium), `-082` `verify-links` (medium), `-083` secure logging (low).
>
> The cited lines were re-read in the source tree at HEAD for this draft (see Claim Labels). The full source-lesson bodies are in
> `lessons-routing`'s archive under `lessons-archive/filed-live-blockers/sweep-2026-11-02/`.

## Objective

Seven gaps in domain content each let a defect pass that the guidance should have caught. Six are missing or incomplete rules in
the Java and security guidance (a code review has no rule for them, or the guidance teaches the unsafe form). One is a script, the
AsciiDoc link checker, that reports a clean pass over link classes it never examined.

After this plan, each gap has its rule in the domain bundle that owns it, stated once and cross-referenced rather than copied, and
`verify-links` names the link classes it did not check. No per-language surfacer is added: the operator's standing direction is a
content rule in the domain bundle.

## Deliverables

1. **The JavaDoc review rules cover a restated count and an unverified ordering claim** (`-077`).
   - The Review Rules block of the `javadoc` skill gains two rules, in the harvestable-block form its four existing rules use:
     - JavaDoc that restates a count derivable from the declaring source as a literal (a preset count, a number of constants), so
       the literal drifts when the source changes;
     - JavaDoc that asserts a guard or sanitisation ordering ("validated before X", "sanitised first") that the calling code does not
       have, so a reader trusts a guarantee the code does not give.
   - `javadoc-method-documentation.md` already says to state ordering as a guarantee. It gains the verification half: an ordering claim
     is checked against the caller before it is written.

   *Done when:* a doc test asserts both rules are present in the `javadoc` skill's Review Rules block and satisfy the harvestable
   block contract, and that the method-documentation standard names the caller check. Each fails at HEAD, where the block holds four
   rules and none covers either.

2. **The JUnit review rules cover tests that cannot fail, and spec citations that name no clause** (`-078`, `-079`).
   - The test-code Review Rules block of `junit-core` gains rules for the four shapes that recurred:
     - a relational or parity assertion with no anchor to a concrete value, which passes on a uniformly wrong value;
     - a test named for a builder default that passes the value explicitly instead of reaching the default through the production path;
     - a negative assertion that goes vacuous when a new invariant makes the absence unreachable by construction, which needs a
       positive control;
     - a hardcoded name list or enum-cardinality assertion that mirrors a set defined elsewhere.
   - It also gains the two rules from `-079`: a security test that cites a specification names the clause, and an assertion that a
     request is accepted (fail-open) states why.
   - `testing-junit-core.md` gains a section that explains the shapes and gives a before/after for each. It points to
     `persona-module-tester`'s matched positive/negative controls and non-vacuity guidance for the language-agnostic form and does
     not copy it.
   - `cui-testing` and `cui-http-testing` carry a one-line pointer where a CUI test commonly meets the shape (the attack-database and
     enum-driven cases); they do not restate the rule.

   *Done when:* doc tests assert each of the six rules in the `junit-core` block (satisfying the block contract), the section and its
   before/after examples in `testing-junit-core.md`, and the pointer in each CUI skill. Each fails at HEAD, where the block holds four
   rules and a search for anchor, vacuous, cardinality and tautology across both bundles is empty.

3. **`cui-http-testing` teaches invisible and bidirectional characters built from code points** (`-080`).
   - Step 3 and the attack-database section of `testing-mockwebserver.md` state that an invisible or bidirectional control character
     in a Java test literal is built from its code point (an escape or `Character.toChars`), never embedded raw. A raw character is
     invisible in review and trips the static-analysis rule against bidirectional characters (Sonar `text:S6389`).
   - Sonar is not enabled for this project. The rule is stated for the reviewability reason and cites the analyzer rule only as the
     example of a tool that rejects it; no Sonar step is added.

   *Done when:* a doc test asserts the rule in both places with a code-point example, and fails at HEAD, where a search for unicode,
   bidi and codepoint across `cui-http-testing`, `cui-http` and `cui-testing` finds nothing.

4. **The `java-core` switch guidance says when exhaustiveness is checked** (`-081`).
   - The section "From an if/else chain over a closed constant set" in `java-17-features.md` keeps its advice, and adds the caveat the
     advice depends on: the compiler checks exhaustiveness for a switch **expression**, or an enhanced switch with pattern or enum
     exhaustiveness. A constant-only switch **statement** is not checked and silently falls through for an unmatched value.
   - Removing the trailing `throw` is shown to be safe only under the first form. The section states that a switch statement keeps its
     `default -> throw`, and gives the fail-open authorization path as the case where dropping it is a defect.
   - `java-core`'s Review Rules block gains the matching rule: a trailing `throw` or `default` removed while the switch remains a
     statement.

   *Done when:* a doc test asserts the caveat, the statement-keeps-`default` rule and the new Review Rules entry, and fails at HEAD,
   where lines 94 and 106-108 say the throw disappears and no caveat names the statement form.

5. **The secure-logging guidance says masking is not sanitising, and that `\p{Cntrl}` is ASCII-only** (`-083`).
   - `java-security-patterns.md` § Masking Pattern states that a masking helper redacts content and does not neutralise CR, LF or
     other control characters, so a masked value can still forge a log line. The example is paired with the neutralisation step.
   - `persona-security-expert`'s `secure-logging.md` (the sanitise-event-data item) names the control-character set to neutralise as
     CR, LF, tab, the other C0 controls, DEL and the C1 range (U+0080 to U+009F), and states that `\p{Cntrl}` covers only the ASCII
     range. It names `Character.isISOControl` or an explicit C1 range as the check.
   - `pm-dev-java`'s `java-security` skill carries the Java form (a short neutralise-then-log example) and points to the persona standard
     for the rule. `cui-logging` gains a pointer only if its standards discuss value neutralisation; its throwable and cause-chain
     coverage stays as it is.

   *Done when:* doc tests assert the masking-is-not-sanitising statement beside the example, the C1 range and the `\p{Cntrl}`
   statement in `secure-logging.md`, and the Java pointer. Each fails at HEAD, where a search for `isISOControl`, `Cntrl` and C1 across
   the three skills is empty.

6. **`verify-links` names the link classes it did not check, and checks the `link:` targets it can** (`-082`).
   - The result `data` gains `unchecked_link_classes`: one row per class the checker saw but did not verify, with the class name, the
     count and the first occurrence. A `link:` macro to an external URL is one such class, because the checker does no network access.
     A zero is a measured zero, and a file with no `link:` macros reports none.
   - A `link:` macro whose target is a relative file path is verified for existence, relative to the containing file, and reported as
     `broken` when absent. The grammar is added beside the three existing ones (`<<anchor>>`, `xref:` and the deprecated `<<file.adoc>>`).
   - The `link:` text in a section title that the anchor derivation strips (the existing line that removes `link:https?://…` from a
     title) is unchanged.
   - `broken_links: 0` is no longer readable as full coverage: the skill's documentation of the result states what the field covers and
     points at `unchecked_link_classes`.
   - `PLAN-LB-58` already refuses a Markdown file; this deliverable is about `link:` macros inside `.adoc` files and does not touch
     that branch.

   *Done when:* fixture tests show: an `.adoc` file with a relative `link:` to an existing file reports it checked, one to a missing
   file reports it `broken`, one to an external URL reports it under `unchecked_link_classes` with its count, and a file with none
   reports an empty list. The existing link-verify fixtures stay green unchanged. The relative-missing and external cases are red at
   HEAD.

Split guard: six deliverables, at the ~6 threshold, and kept as one plan on the operator's instruction. The
rationale is that D1 to D5 are documentation edits in two bundles plus one persona standard, each independent of the others and of
D6, so the plan has no internal ordering and any deliverable can be dropped without touching another. D6 is the only code change.
If the outline finds D2's six rules need their own review, D2 is the natural split.

## Standing Constraints

- **Content rules, not surfacers.** The operator's standing direction is a rule in the domain bundle that owns the subject. No
  per-language surfacer, no new scanner script, no new skill.
- **State once, point elsewhere.** A rule that already has a home (`persona-module-tester`'s controls and non-vacuity guidance, the
  harvestable block contract in `review-rubric.md` § 10) is referenced, not copied.
- **Review-rule blocks keep their contract.** Every new Review Rules entry follows the harvestable block contract the existing entries
  follow, and a rule describes a defect a reviewer can see in a changed file.
- **Fail closed in `verify-links`.** A class the checker did not examine is never reported as examined, and the new field is present on
  every result.
- **Documentation standards.** Present-state wording; no dates, version numbers or changelog text in a bundle document.
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none. D3 cites the analyzer
  rule as an example only.
- **Tests state their purpose.** Every new or changed test states what it protects and is shown red at HEAD where its Done-when says so.

## Claim Labels

- OBSERVED: the `javadoc` skill's Review Rules block holds four rules (`@param`, `@throws`, a nullness or return claim, `{@link}` or
  `@see`) — read at `marketplace/bundles/pm-dev-java/skills/javadoc/SKILL.md` L145-152.
- OBSERVED: the `junit-core` test-code Review Rules block holds four rules (`try`/`catch` without `fail()`, an assertion-free test,
  order-dependent state, `Thread.sleep`) — read at `marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md` L141-148.
- OBSERVED: `cui-http-testing` documents the attack databases and says to drive adversarial inputs from them — read at
  `marketplace/bundles/pm-dev-java-cui/skills/cui-http-testing/SKILL.md` L122-124; it says nothing about building invisible or bidi
  characters.
- OBSERVED: the if/else-to-switch section says the trailing `throw` disappears (L94) and that an exhaustive switch over an enum needs
  no `default` and no trailing `throw` (L106-108), with a `default -> throw` kept only for an open `String` input (L109-110) — read at
  `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md` L75-110. No caveat names the switch statement.
- OBSERVED: the Masking Pattern example logs the first three characters of a username with no warning that masking is not sanitising —
  read at `marketplace/bundles/pm-dev-java/skills/java-security/standards/java-security-patterns.md` L29-42.
- OBSERVED: `secure-logging.md` item 2 lists CR, LF, tab and delimiter characters to strip or encode, and item 3 notes that
  parameterisation does not neutralise CRLF — read at
  `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secure-logging.md` L55-56. Neither names C1 controls.
- OBSERVED: `verify-links` scans three link grammars — `<<anchor>>` (L70), `xref:` (L82) and the deprecated `<<file.adoc>>` (L97) —
  and the only `link:` occurrence strips `link:https?://…` from a section title (L48); the result `data` carries `files_processed`,
  `total_links`, `broken_links`, `format_violations` and `issues`, and no unchecked-class field (L225-244). File mode refuses a
  non-`.adoc` file (L185-199) — read at `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py`.
- HYPOTHESIS: `javadoc-method-documentation.md` L38 is the only existing statement about ordering, and it says nothing about
  verifying the claim against the caller (the finding's account; verify-at-outline).
- HYPOTHESIS: `testing-junit-core.md` has no section on anchoring, positive controls, cardinality or mirrored lists, and
  `persona-module-tester/standards/testing-methodology.md` L332 and L612-652 carry the language-agnostic controls and non-vacuity
  guidance (the finding's account; verify-at-outline, and read the methodology before writing D2's pointer).
- HYPOTHESIS: `cui-logging`'s `logging-standards.md` L292-312 covers only the throwable and cause-chain channel (the finding's account;
  verify-at-outline).
- HYPOTHESIS: the `java-core` Review Rules block exists in `java-core/SKILL.md` in the harvestable form, as the other Java skills'
  blocks do (verify-at-outline before D4's rule).
- HYPOTHESIS: a contract test enumerates or validates the harvestable review-rule blocks
  (`test/plan-marshall/phase-6-finalize/test_code_review_contract.py`, `_review_contract_scanners.py`), so D1, D2 and D4's new rules
  must satisfy it, and it may need extending (verify-at-outline).
- HYPOTHESIS: `lessons-routing-063` (discarded on 2026-11-02) concerns U+2028 and U+2029 escape notation in the same secure-logging
  area. It is not carried here; if the outline edits the same paragraph, read it in `lessons-routing`'s archive first (verify-at-outline).
- Verify-first clause (D6): add the relative-missing fixture and run it at HEAD. It must be red (a clean pass over a `link:` to a missing
  file). If HEAD already reports it, the finding's premise is wrong at its centre: loop back and re-scope.
- Verify-first clause (D2): read the rest of `junit-core`'s test-code guidance and `persona-module-tester` before writing the rules, so
  no rule duplicates one that exists.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-dev-java/skills/javadoc/SKILL.md` — two Review Rules entries (D1)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/javadoc/standards/javadoc-method-documentation.md` — the caller check for an ordering claim (D1; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/junit-core/SKILL.md` — six Review Rules entries (D2)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/junit-core/standards/testing-junit-core.md` — the tests-that-cannot-fail section (D2)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java-cui/skills/cui-testing/SKILL.md` — one-line pointer (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-java-cui/skills/cui-http-testing/SKILL.md` — one-line pointer (D2) and the code-point rule at Step 3 (D3)
- OBSERVED: `marketplace/bundles/pm-dev-java-cui/skills/cui-http-testing/standards/testing-mockwebserver.md` — the code-point rule in the attack-database section (D3)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md` — the switch-statement caveat (D4)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md` — one Review Rules entry (D4; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-dev-java/skills/java-security/standards/java-security-patterns.md` — masking is not sanitising (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/secure-logging.md` — the C1 range and `\p{Cntrl}` (D5)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java/skills/java-security/SKILL.md` — the Java form and pointer (D5; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-dev-java-cui/skills/cui-logging/standards/logging-standards.md` — pointer only if it discusses value neutralisation (D5; verify-at-outline)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py` — the `link:` grammar and `unchecked_link_classes` (D6)
- HYPOTHESIS: `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md` — what `broken_links` covers and the new field (D6; verify-at-outline)
- OBSERVED: `test/pm-documents/ref-asciidoc/test_asciidoc.py` — D6 fixture tests
- OBSERVED: `test/pm-documents/ref-asciidoc/fixtures/link-verify/` — D6 `link:` fixtures
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_code_review_contract.py` — only if the review-rule block contract test must be extended (D1, D2, D4; verify-at-outline)
- HYPOTHESIS: `test/pm-dev-java/doc-contracts/test_domain_content_rules.py` — a new doc-contract test file for D1 to D5 (new file; the outline may place it beside an existing bundle doc test)

## Dependencies and Sequencing

- **Depends on:** none.
- **Overlaps with PLAN-LB-105 and PLAN-LB-107 (staged)** only on the HYPOTHESIS test file under `test/plan-marshall/phase-6-finalize/`,
  a single file at most and below the gate's overlap-prompt threshold.
- **Overlaps with PLAN-LB-58 (shipped)** in the same file as D6, `_cmd_verify_links.py`; its Markdown-refusal branch is in HEAD and is
  not touched here.
- **Overlaps with PLAN-LB-110 (staged)** on no declared path; it is the Maven consumer test plan, and D2's rules are documentation only.
- **Running plans:** checked at emit by the disjointness gate; none were checked in this draft.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-113-domain-content-gaps.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
