# Gaps — skills-carry-incident-history-as-normative-prose

**Source:** verification.md (same directory)   **Open items:** 4

## G1 — Remove the `PR #1013` narration left two lines from the passage D3 corrected

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md:388` — the paragraph naming `test_self_review_reachability_regression.py`
- **What is wrong:** Line 388 reads *"pins the **PR #1013** pre-fix scanning and post-fix anchored forms end-to-end"*. Line 390, the very next paragraph, was edited by D3 from *"the two **PR #1067** defects"* to *"the two defects"* and from *"the **#1067** head ref"* to *"the **pre-fix** head ref"*. Same document, same section, same construction ("pins the PR #N pre-fix X"), opposite treatment. The plan named this file as one of its dense sites.
- **Why it matters:** A reader of that section sees one paragraph that names a mechanism and one that names an unseeable PR, and cannot tell which convention is authoritative — the exact drift the rule exists to stop. It also leaves an in-scope-by-the-plan's-own-criterion occurrence live in the file the plan pointed at.
- **Fix:** Rewrite line 388 the same way line 390 was: replace `pins the PR #1013 pre-fix scanning and post-fix anchored forms` with `pins the pre-fix scanning and post-fix anchored forms`. Cross-references at lines 264 and 416 point at `standards/unreachable-guard-detection.md`, which carries the worked example, so no meaning is lost. If the reference is judged genuinely referential, say so at the site (name the worked-example document) rather than leaving a bare PR number.
- **Done when:** `grep -n 'PR #1013' marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` returns nothing at line 388, or the line names the worked-example document instead of the PR number.
- **Module/topic:** `pm-plugin-development` / `ext-self-review-plan-marshall`

## G2 — Close the back-tick bypass in `no-incident-references`

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_incident_reference_in_docs.py:280` — `_scan_file`, the `_offset_in_inline_code(m.start(), spans)` skip
- **What is wrong:** Any incident reference wrapped in backticks is exempt, whatever the surrounding prose. Verified by execution: a fixture reproducing the live prose `` ### Why the post-merge move does not revert `#990` `` / `` the failure mode `#990` closed cannot recur `` returns **0 findings** from `analyze_incident_reference_in_docs`. That exact prose is in the tree at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-preference-emitter.md:91,93,100,104,175`, and the same shape recurs at `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:356,419,493,672,673,675`. The exemption is justified in the module docstring as "a code token, exempt as inline code", but `` `#990` `` in a heading is narration, not a code token. The sibling rule added later for the test tree already states the correct posture — `rule-catalog.md:624`: *"The exemption is per occurrence, so backticking one id cannot launder a segment."*
- **Why it matters:** A future author can regress the whole pattern the plan removed by adding two backticks, and the gate stays green. The rule ships as the plan's only anti-regression guarantee, so a one-character bypass makes the guarantee nominal.
- **Fix:** Narrow the inline-code exemption to references that are genuinely code tokens. Concretely: do not exempt a back-ticked `#NNNN` / `plan-marshall#NNNN` when an incident noun (`failure mode`, `signature`, `shape`, `defect`, `incident`, `regression`) appears within a bounded window on either side of it, and do not exempt one that sits inside a markdown heading. Add a positive test using the `finalize-step-preference-emitter.md` prose verbatim, and register a suppression entry for that file (or clean it) so the tree stays at zero findings.
- **Done when:** the analyzer, executed over a fixture containing `` the failure mode `#990` closed cannot recur ``, returns one `incident_reference` finding, and `test_real_marketplace_has_zero_findings` still passes over the real tree.
- **Module/topic:** `pm-plugin-development` / `plugin-doctor` — `no-incident-references`

## G3 — Extend the rule to the narration forms D1 was told to sweep

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_incident_reference_in_docs.py:124-137` — `_TERM_OF_ART_RE` and `_PATTERNS`
- **What is wrong:** `_TERM_OF_ART_RE` requires the incident noun to follow the reference (`#\d{3,4}\s+(?:\w+-\w+\s+)?(?:failure mode|signature|…)`), and no pattern covers dated or version-pinned narration. Executed against an eight-form fixture, the rule fires on two forms and misses six, including three the plan named: `the failure mode #990 closed` (noun before ref), `as of 2026-07 the check is green`, `before 0.1.1240 the writer emitted both keys`. D1's brief was explicit: *"Widen well beyond the seed pattern to cover bare `#NNNN` in prose, pull-request URLs, dated phrasings ('as of 2026-07'), and version-pinned narration ('before 0.1.1240')."* D1's sweep looked for those forms; D4's rule cannot see them.
- **Why it matters:** The plan's Goal is *"a rule prevents the pattern from returning"*. Two of the four widened forms have no guard at all, so the same content can reappear in a dated or version-pinned spelling with a green gate. `CLAUDE.md` § Documentation Standards forbids dates and version numbers in document content independently of this plan, and nothing enforces that today.
- **Fix:** Add to `_PATTERNS` (a) a reversed term-of-art form — incident noun immediately followed by an optionally back-ticked `#NNNN` — and (b) a dated/version-pinned narration family: `\b(?:as of|since|before|after)\s+(?:20\d{2}(?:-\d{2})?|\d+\.\d+\.\d+)\b`. Extend `rule-catalog.md:748` and `rule-provenance.md:206` with the new forms, and add one positive test per new form plus one negative that keeps a legitimate version constraint (e.g. `requires Python 3.12 or newer`) unflagged.
- **Done when:** the analyzer fires on all three of `The failure mode #990 closed cannot recur.`, `as of 2026-07 the check is green.`, and `before 0.1.1240 the writer emitted both keys.`, and the real-marketplace zero-findings test still passes (registering suppressions or cleaning sites as needed).
- **Module/topic:** `pm-plugin-development` / `plugin-doctor` — `no-incident-references`

## G4 — Dispose of the `#1027` narration in the normative automatic-review documents

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:646`; `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:275`; `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py:16`
- **What is wrong:** All three carry *"on #1027 PR-Agent posted its Guide — valid participation — while reporting 'no major issues' on a diff in which CodeRabbit found two Major defects"*, and all three carried it at `6792510a~1`. `report-01.md` § D1 enumerates the KEEP set and names only `pr-agent.md`/`sourcery.md` as the bot-data-sheet carriers of this shape; these three files are not data sheets — `SKILL.md` and `bot-participation-contract.md` are normative contract documents and `review_completeness.py` is production code. They are covered only by a blanket "softer references … classified KEEP" clause, so D2's *Done when* ("every occurrence in D1's list carries exactly one verdict") is not met for them.
- **Why it matters:** These are the plan's DELETE arm almost verbatim: the sentence *after* the reference already states the mechanism (*"A satisfied quorum MUST NOT be rendered as a reviewed diff"* / *"participation is not review quality"*), so the incident sentence adds nothing a reader can act on while asking them to reason from a PR they cannot see. Leaving it undisposed in a normative document is precisely the pattern the plan set out to end.
- **Fix:** In each of the three sites, replace `on #1027 PR-Agent posted its Guide` with a mechanism-only statement of the same fact — e.g. *"a bot can post its Guide (valid participation) while reporting no major issues on a diff another reviewer found Major defects in"* — keeping the surrounding normative clauses byte-identical. `pr-agent.md:377` carries the same sentence in a data-sheet rationale; either give it the same treatment or record it explicitly as a data-sheet KEEP.
- **Done when:** `grep -rn '#1027' marketplace/bundles/plan-marshall/skills/automatic-review/` returns hits only in files whose disposition is recorded as a data-sheet observation record, and the surrounding participation-is-not-review-quality obligations are unchanged.
- **Module/topic:** `plan-marshall` / `automatic-review`
