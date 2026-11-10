# Landing Analysis: PLAN-LB-125 — The review gate does not accept a second disabled test in an accepted class, and triage honours a dropped functional review

epic: live-blockers
workstream: WS-03
pr: #1939 (https://github.com/cuioss/plan-marshall/pull/1939)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> Merge commit `bbe421f15bbcc0e9b1eb8fa181829c7f96c3e3ef`, a merge-queue squash with ONE parent `19da7ed840c22aa37c1bdf69b9210754e0b2f1e7`
> (the PLAN-LB-124 merge), read with git before the leaf prompt named it. `ci pr view` reports `state: merged` with that merge commit.
> Lane: runbook, harness `opencode`, model `deepseek-v4.1-flash/high`, `total_tokens` unknown. The inbox message is `complete: false`,
> `missing_keys: total_tokens` (out of scope per the focus rule). The lane's review history, CI and merge-queue claims were not re-read;
> the standing-authorization narrative was not assessed (policy is settled, never asked). The plan carried the PLAN-LB-75 D1 triage
> exemption folded in by ruling 23.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a disabled JVM test is decided per method; an acceptance pairs each marker with its test | shipped-modified | JVM method arm `Class::method` gated by suffix, class headers are scope, paired `{test, marker}` units, the retired key re-raises (`review_support.py:346-358`, re-read); holds for Java, fails open for idiomatic Kotlin (L3-1) |
| D2 triage honours a dropped functional review | shipped-as-specified | one `functional_review_drop_reason` reader in `_criteria_snapshot.py`, `open_criteria` returns `review_dropped` after the deleted/tampered refusal, the completion gate delegates to it (`_cmd_lifecycle.py:1250`); both verify-first clauses held; `refreeze_requires_decision` routed in `phase-3-outline` |
| D3 placement and coverage marker fail closed | shipped-as-specified | placement never reads the mutable commit (`github_ops.py:730-742`); a marker after an unterminated fence is present-but-unreadable; two-line payload read with a 40-line bound; the answer admission goes through the parser |
| D4 the close and the move proof state their reach | shipped-as-specified | accepted removals refused without a validated review head; cross-step laundering pinned; a JS identity is qualified by its enclosing `describe` |
| D5 documents and tests state what they pin | shipped-modified | rubric, tests and the splitter done; the splitter was made fence-aware instead of only stating its limit; `markdown_fence.py` is the one fence owner; history wording in three places (conformance) |

## Three-Layer Analysis

Read by one read-only leaf (`execution-context-level-5`). The orchestrator re-read the points marked "re-read"; the rest are unverified leads.

- **Dispatch:** one read-only leaf per landing — reason: reading the merged review-gate code is the depth the Dispatch Decision Rule exists for.
- **Verdict:** layer 1 clean; layer 2 findings (minor); layer 3 findings — **one major (L3-1)**.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 | D1's premise holds: before the merge a Java/Kotlin file fell back to one identity per class | checked | confirms | `_review_support_integrity.py` diff, removed lines |
| L1-2 | D2 clause 2 holds: `refreeze_requires_decision` was read as an unreadable outline | checked | confirms | `phase-3-outline/SKILL.md:677` (removed text) |
| L1-3 | spec tension: D1 says the Python and JS fixtures keep their results, D4 says a JS identity is describe-qualified; the two cannot both hold for a describe-nested `it` | checked | refutes | `_review_support_integrity.py:436-438` (re-read), `:1068` |
| L1-4 | D5 asked only to state the splitter's limit; the code made it fence-aware and states the remaining unterminated-fence limit instead | not_shown_by_reading | none | `_plan_parsing.py:66-104` |

**Layer 1 verdict:** clean (L1-3 is a spec wording the lane resolved in favour of D4).

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|----------------------------------|---------|
| D1 | `_review_support_integrity.py:99-133,1064-1113`, `review_support.py:346-358` | the Java and pairing tests (`test_lb118_accepted_removals_d2.py`, `test_lb118_test_integrity_d1.py`) | the retired-key re-raise has no test in the diff (unverified negative) | checked |
| D2 | `_criteria_snapshot.py:1795-1892`, `_cmd_lifecycle.py:1250` | dropped, scheduled and tampered fixtures | none | checked |
| D3 | `github_ops.py:730-742`, `_github_pr.py:480-492`, `github_re_review.py` | the placement test pins only the fetch field (`commit_id == ''`); the unterminated-fence fixture uses kind `reviewed` and head `a`, not an in-progress summary with a real head SHA, and never drives the token-arm fall-through | the Done-when "not credited at the consumer" is not exercised | not_shown_by_reading |
| D4 | `_cmd_loop_back.py:702-716,764` | the laundering, non-review-step and describe-qualification tests | none | checked |

- **Surface:** undeclared: `markdown_fence.py` (new), `test_lb105_accepted_removals_d2.py`, `test_lb55_merge_head_binding.py`, `test_re_review_strategy_match.py` (three test files; the lane said four, which holds only if the hypothesis entry `test_github_pr_currency.py` is counted). Every diff file is explained by a deliverable. `_cmd_lifecycle.py` is declared "only if the drop reader moves", and it did.
- **L2-1 (minor):** the retired-key re-raise (`_pair_set` returns `None` for an entry with no pairs, so it never accepts) is read in the code and the spec asks for it, but the leaf found no test pinning it. Unverified negative.
- **N7 narrative:** the lane calls the wrapped-parameter-list and generic-return-type limits "documented". They are stated in the PR body Notes, but the leaf found no merged docstring, rubric or workflow text that states them (an unverified negative).

**Layer 2 verdict:** findings — 1 minor, 1 not shown.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| **L3-1** | `_review_support_integrity.py:126` (re-read), `:1083-1086,1110` (re-read) | a Kotlin test with a backticked name (``fun `renders x`() {``) or an expression body (`fun a() = runTest {`) | the `fun` arm needs `[A-Za-z_$]` for the name and `{` or `:` after `)`, so neither shape yields an identity; the `@Disabled` above it is attributed to the next candidate (or the last), the marker sets are sets, so accepting `@Disabled` on test 1 and later disabling test 2 produces the identical `{test, marker}` pair and the acceptance covers it (`review_support.py:352-357`), or no row appears when the base already carried the marker. This is the D1 defect, unfixed for idiomatic Kotlin JUnit 5 tests; the Java shapes of the Done-when are fixed | **major** |
| L3-2 | `_review_support_integrity.py:99-101` (re-read) | a Kotlin `@Nested inner class`, or a one-line `@Nested class Inner {` / `@Disabled class FooTest {` | `_ANY_CLASS_RE` has no `inner` modifier and no annotation prefix; nested-class methods take the outer prefix, so same-named methods in sibling nested classes share one identity and one pair, and a one-line class annotation goes to the first method | minor |
| L3-3 | `_review_support_integrity.py:131,119` | a header that does not parse: a wrapped parameter list, a generic return type with a space after the comma, an annotation string containing `)` on the header line | no span is made, the marker is attributed to the NEXT method, so an accepted pair can later cover a genuine disable of that next method (stronger than the lane's "yields no identity") | minor |
| L3-4 | `_review_support_integrity.py:83-84,1076` (re-read) | `@DisabledOnOs`, `@DisabledIf*`, `@DisabledOnJre`; or a commented `// @Disabled` | `SKIP_MARKERS` is matched as a substring, so the conditional forms are recorded as `@Disabled`: an accepted conditional disable on `a()` covers a later unconditional `@Disabled` on `a()`, and a commented marker raises a false row. The spec's own claim label recorded this; no deliverable carried it | minor |
| L3-5 | `_review_support_integrity.py:157,443-450` (re-read) | a column-0 `//` line inside a class (IntelliJ's default line-comment placement) | `_significant_lines` treats only `#` lines as comments, so the `//` line is significant at indent 0 and pops the class stack; later JVM methods lose their `Class::` prefix, and a comment added or removed between pre and post gives false removed-identity rows on a legitimate change (a false block, clearable by an accept) | minor |
| L3-6 | `_review_support_integrity.py:484` | wrapping existing JS `it`s in a new `describe`, or renaming a `describe` | every identity changes, so the move proof reports removals and blocks until accepted; consistent with the Python class-move behaviour but a new false row for a common refactor | info |
| L3-7 | `_plan_parsing.py:93` | a fence nested inside a fence, or an unterminated fence | the fenced range runs to the end of the text, so every later `### N.` heading is dropped from `split_deliverable_blocks` and `extract_deliverable_headings`; whether `criterion_unparsed` still fires for the absorbed deliverables is not settled by reading | minor |
| L3-8 | `markdown_fence.py:190` | a coverage marker quoted inside a list-item fence (`- ```` ``` ````) at three spaces of indent | `fence_marker` does not see a fence inside a list item or blockquote, so a quoted marker reads as the bot's claim; it needs a crafted body that also names the right head | minor |
| L3-9 | `_github_pr.py:487` | a `{...}` after the comment terminator on the `-->` line | the multi-line scan joins the whole `-->` line, so trailing text can be taken as the payload | info |
| L3-10 | `_criteria_snapshot.py:1795` | an empty or non-string `phase_6.steps` | reads as "not scheduled" and counts as a drop, now also for triage; carried over from the gate unchanged | info (not shown that a manifest carries it) |

**Layer 3 not shown by reading:** whether the consumers of `_identity_spans` and of the inline `commit_id` outside the diff were swept (the leaf had no content search); whether the fixture homes are isolated for every new test (the leaf read the fixtures, not conftest).

**Layer 3 verdict:** findings — 1 major, 5 minor, 3 info.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only | deviates | `markdown_fence.py:5-7` ("used to carry"), `_plan_parsing.py:68-71`, `github_ops.py:710-712` narrate a past incident |
| CLAUDE.md § Script Execution | scripts run via the executor | conforms | `phase-3-outline/SKILL.md:674-677`, `triage.md` use the executor notations |
| spec standing constraint | fail closed | deviates | L3-1 to L3-3: unparsed JVM shapes misattribute markers, so a second `@Disabled` can be credited |
| spec standing constraint | the gate gets more precise, never more permissive; controls for every relaxation | conforms | D2 tamper and scheduled-review controls; D1 Java control; JS and Python results otherwise not shown |
| spec standing constraint | one identity scheme, one acceptance key, one drop reader | conforms | `functional_review_drop_reason`, `pairs` in the key and the writer, `markdown_fence.py` imported by `_github_pr.py`, `_criteria_snapshot.py`, `_plan_parsing.py` |
| memory / spec | required reviewers keep their text; no change to review authorization or quota policy | conforms | no `marshal.json`, bot-registry or policy text in the diff |

## Metrics and Anomalies

- Tokens: `unknown`.
- Anomalies: CodeRabbit refused on quota four times (03:11Z to 08:28Z) and reviewed two heads; one earlier `verify` run failed on the build-server routing timing flake, outside the plan's surface. Four CodeRabbit majors (splitter not fence-aware, cross-step laundering, `_moved_pre_image` path rebinding, hardcoded coverage hint) are borne out by the merged code (the leaf's reading; commits `23373612e`, `814a037a5`, `aae638134` exist locally).

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed twice; every finding fixed or answered and resolved; final refusal recorded. Sourcery refused on a hard quota.
- CI/merge: merged through the queue; the merge state and commit were re-read. Whether the PR carried a head later than `aae638134` cannot be read from git here.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped `1939`
- [x] row `landing` stamped `landings/PLAN-LB-125.md`
- [x] row `plan_marshall_plan_id` stamped `rb-lb-125-review-gate-jvm-acceptance-and-triage-exemption`
- [x] epic.md narrative reconciled; the layer-3 major recorded as an Open Defect, the minors as one Watch; PLAN-LB-75 D1 and D2 now absorbed (D2 clause 2 held and shipped)
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 is reported to the operator at once and is NOT staged.** It fails open on the test-integrity gate for Kotlin consumers. It becomes a staged spec only on the operator's word; the fix would widen the `fun` arm (backticked names, expression bodies) and the class regex (`inner`, one-line annotated headers), and would count markers per method rather than keep a set.
- The conditional-disable substring (L3-4) and the `//` comment (L3-5) are fold candidates for the same plan if the operator stages it.
- Owed outside the plan, operator-run: a harness sync after the merge. No verb or flag was added, so no executor regeneration is owed from this plan.
