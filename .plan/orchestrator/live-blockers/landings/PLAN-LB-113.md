# Landing Analysis: PLAN-LB-113 — domain content gaps and `verify-links` unchecked classes

epic: live-blockers
workstream: WS-02
pr: #1909

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-113.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `144ccdbfcd8598e9e0d60674cf688c399a7df6f4` (merge queue), read through the `ci` abstraction as `state: merged`. Landing message `rb-lb-113-domain-content-gaps-001.md`. The diff `8859bc1b0..144ccdbfc` touches 24 files, 1001 insertions and 45 deletions; the files match the message's deliverable table plus the disclosed `MAX_DOMAIN_RULES` bump and `uv.lock` refresh.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — javadoc review rules (restated counts, ordering claims) | shipped-as-specified | `javadoc/SKILL.md`, `javadoc-method-documentation.md`; `test_domain_content_rules.py` |
| D2 — junit-core rules for tests that cannot fail, spec citations, fail-open reasons | shipped-as-specified | `junit-core/SKILL.md`, `testing-junit-core.md` (+91 lines), pointers in `cui-testing` and `cui-http-testing` |
| D3 — `cui-http-testing` bidi characters from code points | shipped-as-specified | `cui-http-testing/SKILL.md`, `testing-mockwebserver.md` |
| D4 — `java-core` switch statement caveat | shipped-modified | `java-17-features.md`, `java-core/SKILL.md`. The text corrects the spec's premise (an enum statement over plain constants is not exhaustiveness-checked) rather than copying it |
| D5 — masking is not sanitising, C1 controls | shipped-as-specified | `java-security-patterns.md`, `java-security/SKILL.md`, `secure-logging.md`, `cui-logging` pointer |
| D6 — `verify-links` `unchecked_link_classes` and relative `link:` target verification | shipped-as-specified | `_cmd_verify_links.py` (+240), `ref-asciidoc/SKILL.md`, four fixtures, `test_asciidoc.py` |
| not a deliverable | added-unplanned | `target.py` `MAX_DOMAIN_RULES` 15 → 25 with its pinned test constant (the java domain now harvests 22 rules; D1+D2+D4 make that unavoidable); `uv.lock` re-resolved to the minimums `pyproject.toml` already declares |

The PR body's test evidence is stale against the message (it names `83f2d8599` the merge head with 32597 tests; the message gives 32592 there and `27fc73439` as the final head), and its description of skipped delimited blocks and the D4 condition is narrower than the code.

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace, and the merged code — by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`), and the orchestrator re-read the points recorded as `checked` below before writing them here. The reading is by reading, no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is depth work, and this landing's read must not share context with the LB-111 landing read in the same firing.
- **Verdict:** layer 1 findings (minor); layer 2 findings (minor); layer 3 findings (minor/info, no blocker, no major).

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 | D4's premise ("an enhanced switch with pattern or enum exhaustiveness") misstates JLS 21 §14.11.2; the landed text corrects it. | checked | `plans/PLAN-LB-113-…md:79`; `java-17-features.md:112-117` |
| L1-2 | "D6 is the only code change" was already inconsistent with main: D1+D2+D4 lift the java code-review domain to 22 harvested rules against `MAX_DOMAIN_RULES=15`. The Expected Surface omitted `target.py`. | checked | `plans/PLAN-LB-113-…md:123` |
| L1-3 | D3's and D5's Done-when require the rule restated in two places, which contradicts the spec's own "state once, point elsewhere" constraint; the duplication in layer 3 is spec-induced. | checked | `plans/PLAN-LB-113-…md:67,130` |

**Layer 1 verdict:** findings — 3 (minor/info). The parenthetical "a search for anchor … is empty" is inaccurate at the base (`re-anchors` matches); the lane said so, and the substantive clause holds.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1–D5 | the documentation files above | `test_domain_content_rules.py`: exact rule counts, exactly-one-hit rule lookup, six Before/After subsections, `U+0080`/`U+009F` and `\p{Cntrl}` anchors | `uv.lock`; `target.py` and `test_code_review_packs.py` (the message's section 2 omits the latter, section 9 mentions it in passing) | checked |
| D6 | `_cmd_verify_links.py` | the four named fixture tests plus the grammar, block, inline and passthrough guards, with non-vacuous `total_links` assertions | none | checked |

One assertion is vacuous at the base: `'secure-logging.md' in java-security SKILL.md` (`test_domain_content_rules.py:267`) passes without the change because the skill already linked the file; the test still fails at the base through its `isISOControl` assertion. Red-at-base runs and green merge runs are `not_shown_by_reading`.

**Layer 2 verdict:** findings — 3 (minor/info).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_cmd_verify_links.py:216-229,238,354` | `link:/docs/guide.html[x]` (a site-root-relative target) | `_link_macro_class` returns `relative-file`; joining an absolute path discards the file's parent, so the checker stats the host root and reports `broken` (run status `failure`). Neither the `ref-asciidoc` wording nor `unchecked_link_classes` covers it. Re-read: confirmed. | minor |
| L3-2 | `_cmd_verify_links.py:223-227,341` | `link:#{section-id}[x]` | The `#` test runs before the `{` test, so the target is classed `internal-anchor`, looked up literally and reported `broken` instead of landing in `attribute-reference`. Re-read: confirmed. | minor |
| L3-3 | `_cmd_verify_links.py:160` | A live `link:missing.adoc[x]`, `<<x>>` or `xref:…` inside backticks | Everything in backticks is blanked before matching, but AsciiDoc constrained monospace still applies macros. The link drops out of `total_links` and is not named in `unchecked_link_classes`: a silent coverage hole in a deliverable whose purpose is to say what was not checked. The opposite case gives a false `broken` for an anchor written `[[id]]` in backticks. Re-read: the masking is confirmed; the Asciidoctor semantics are from known behaviour, not a render. | minor |
| L3-4 | `_cmd_verify_links.py:43` | `++link:missing.adoc[x]++` or `pass:[link:…]` | `_INLINE_PASSTHROUGH_RE` does not mask the unconstrained `++…++` form or the `pass:` macro, so a passthrough example is checked as a live link and reported `broken`, although the comment says passthrough examples are excluded. Re-read: the regex is confirmed. | minor |
| L3-5 | `_cmd_verify_links.py:100,367` | `link:x.adoc#a[x]` where `x.adoc` is a directory, unreadable, or not UTF-8 | `extract_anchors_from_file` opens the file with no handling, so one bad link aborts a multi-file run with no data. It fails closed. Same shape as the existing xref branch. The cmd-level absence of a guard was not re-read. | minor |
| L3-6 | `_cmd_verify_links.py:56` | A `-----` block containing a `----` line | Delimiter runs are cut to four characters, so a nested listing example closes the outer block early and the rest is parsed as live links. Re-read: confirmed. | info |
| L3-7 | `java-security-patterns.md:57,63`; `java-security/SKILL.md:96,105` | — | `neutralise` replaces each control character with `?`, which contradicts the owning rule's "prefer escaping over dropping" (`secure-logging.md:55`); "structured JSON, which escapes all three" overclaims (the JSON string grammar requires escaping only U+0000–U+001F, the quote and the backslash, so DEL, C1 and U+2028/U+2029 are not required). Re-read: both texts confirmed; the JSON grammar is outside knowledge. | minor |
| L3-8 | `secure-logging.md:55` | — | The owning rule omits U+2028/U+2029, which the Java form neutralises; `\p{Cntrl}` is described as ASCII-only without the `UNICODE_CHARACTER_CLASS` qualifier. | minor |
| L3-9 | `java-security/SKILL.md:88-105`; `cui-http-testing/SKILL.md:128` | — | The neutralise section repeats `java-security-patterns.md:47-63` inside one skill that states it has no duplication; the code-point rule is restated in two homes (spec-induced, L1-3). | minor |
| L3-10 | `javadoc/SKILL.md:154` | — | The D1 rule covers only an ordering claim the caller does not implement; the standard also covers ordering inside the method body. | minor |
| L3-11 | `_cmd_verify_links.py:16,341,354` | encoded anchors; `%00` in a target; `../../` | Targets with spaces in the `link:++…++` form are silently uncounted; anchors and fragments are never percent-decoded; a `%00` path may raise `ValueError` on some interpreters; no containment (an existence oracle only). | info |

**Layer 3 not shown by reading:** the `%00` behaviour (interpreter-dependent), whether `safe_main` turns an escaped exception into a structured error, and whether the new tests were red at the base and green at the merge.

**Layer 3 verdict:** findings — 11 (no blocker, no major); not shown by reading — 3.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | No duplication — cross-reference instead | deviates | `java-security/SKILL.md:88-105`; `cui-http-testing/SKILL.md:128` (the junit-core section does point at `persona-module-tester` correctly) |
| CLAUDE.md § Documentation Standards | No timestamps, current state only | conforms | no dates or changelog text in the added markdown |
| PLAN-LB-113 Standing Constraint | State once, point elsewhere | deviates | as above; the owning secure-logging rule omits what the Java form enforces |
| PLAN-LB-113 Standing Constraint | `verify-links` fail closed: an unexamined class is never reported as examined | deviates | inline-code-masked links and the `++…++` target form are neither verified nor named (L3-3, L3-11) |
| CLAUDE.md § Workflow Discipline | No shell file operations, `.plan/` through scripts | deviates | the lane disclosed `wc -l .plan/temp/guard.log` and reads of three harness output files outside the repository |
| CLAUDE.md § Commit Trailer | `Co-Authored-By: plan-marshall <noreply@cuioss.de>` | conforms | the squash commit ends with it, after a GitHub-added co-author line |
| PLAN-LB-113 Standing Constraint | No Sonar step | conforms | `S6389` cited only as an analyzer example |

## Metrics and Anomalies

- Tokens: `unknown` — recorded as an unobserved fact, not zero. `landing-check`: `complete: false`, `missing_keys: [total_tokens]`.
- Duration: not supplied. The message's timestamps run from the first test-first log (2026-11-04 21:39) to the last CodeRabbit trigger (2026-11-05 03:49), across four review rounds and three CodeRabbit refusals.
- Anomalies: 30 inline review threads, all resolved; the pack generator's truncation guard forced the `MAX_DOMAIN_RULES` bump; the `quality-gate` hit the 330 s supervisory floor once and passed on re-run; one `--filter "a or b"` argument was rejected by the wrapper and replaced. The build daemon was unreachable, so every build ran in process.

## Routing and Merge Behavior

- Review: coderabbit (required) reviewed `840261a16` and `8fd112fb5` and was quota-refused at the final head `27fc73439`; the standing authorization applied. Sourcery (optional) commented on two heads and approved `20b2c0d97`; its final trigger was refused on its own 250k-character budget (next review available 2026-11-06T23:43Z). The lane refuted two Sourcery exhaustiveness findings with JEP 441.
- CI/merge: merge queue, merge-group run green at `144ccdb`. The base merge at `8fd112fb5` was clean.
- Sonar: `n/a` — Sonar is not enabled for this project and is ignored.
- Collision: PLAN-LB-113 shared `ref-asciidoc` and `cui-http-testing` surfaces with nothing in flight; none observed. The undeclared `target.py` change is the only surface the declaration missed, and the cause is a guard the declaration did not know about. The gate showed one shared file between LB-113 and the emitted, unstarted PLAN-LB-105; that pairing is rechecked at the next emit and no collision was observed here.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped — `1909`
- [x] row `landing` stamped — `landings/PLAN-LB-113.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-113-domain-content-gaps` (the lane name the sender `rb-lb-113-domain-content-gaps` carries)
- [x] epic.md narrative reconciled — an Open Defect for the incomplete landing message and a Watch for the `verify-links` and secure-logging findings
- [x] resume anchor updated and `queue-view.md` regenerated

## Follow-Ups

- The layer-3 findings are reported to the operator; a fix-plan spec is staged only on the operator's word. Candidate grouping if the operator says yes: one `verify-links` correctness plan (L3-1 to L3-6, L3-11) and one secure-logging text plan (L3-7 to L3-10).
- `target.py`'s rule budget is a guard the declared surface did not know about: any plan adding review rules to the java domain must declare `target.py` and its pinned test constant. Recorded as a Watch.
