# Landing Analysis: PLAN-LB-171 — PLAN-LB-167 completion: the carry-forward binds itself, every caller gets its own body slot; the delegating-consumer case descoped

epic: live-blockers
workstream: WS-04
pr: #2033 (https://github.com/cuioss/plan-marshall/pull/2033)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (the merged tree, the PR state through the CI abstraction, the lane's own progress file). The landing message is a lead, not a fact. Merge commit `c22d103fbf1b6a73ba66c82c238813b79b460f1c` (parent `51859e67b`, the ledger land #2034), squash, eighteen files, 728+/133-. Landing message: `rb-lb-171-lb-167-completion-delegating-checkout-gate-binding-body-slot-001.md` (revision 4, amended after the merge; runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`). `landing-check`: `complete: false`, `missing_keys` = `total_tokens` only; per the standing ruling recorded on the PLAN-LB-170 landing that is no defect. `deliverables_done=4` of `deliverables_total=5`: **D1 was descoped and is not met**.

## Deliverable Fidelity vs Spec

Four of five deliverables shipped. D1, the deliverable the plan was named for, did not: the lane's descope commit `1506824a0` (landing: -1049 lines, on the operator's direction) removed the delegated branch and the 13 D1 tests, and the merged tree holds none of it. The PR body and the squash message on `main` were written for the 66825feec head and still describe D1 as shipped (see L2-1): the text of record on `main` states a change the tree does not contain.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a delegating consumer's docs-only delta is decided | **dropped** (descoped on the operator's word, per the landing; not corroborated by the lane's progress file, which stops at `88ba55d5f`) | `git grep "delegated_"` and the D1 test names over `c22d103fb` find nothing in the lane, its tests or the Sonar skill; `runbook_lane.py:1849-1984` has no delegated branch (re-read); `SKILL.md:848-851` says the case "answers `undecidable`" |
| D2 the carry-forward binds itself in code: (a) head-bound read licence, (b) the marker travels to the gate and the facts | **shipped-modified**: (a) shipped as specified; (b) shipped as an opt-in check, so "non-opt-in" is not met (L2-2) | `sonar.py:1022`, `:1081-1116`; `runbook_lane.py:2065-2134`, `:2537-2588`; `test_sonar_analysis_revision.py:472`, `:492` |
| D3 no two callers share a PR body slot | shipped-as-specified, with the settle-at-outline choice made (refuse the shared default slot for a body-reading caller) | `ci_base.py:211-262`, `:311-313`, `:381-394`; `land.md:135`, `:142`; `SKILL.md:783`, `:788`, `:888-890`; the inventory search finds no remaining default-slot caller under `NO_PLAN` (`.claude/**` and `.github/**` are not inventoried) |
| D4 the documents state what the code does | **shipped-modified**: the retry promise and the inverted cause are fixed, but the descope left a contradiction between §6 and §7, a false sentence about delegating consumers, and a canonical invocation without the marker flags (L3-1, L3-2, L3-3) | `SKILL.md:848-851`, `:867-877`, `:971-972` (re-read) |
| D5 tests pin D1 to D4, red-first | **shipped-modified**: the D1 tests are gone with D1; two of the surviving D2/D4 tests cannot fail on the tree they were meant to pin (L2-3); the twins are `order: none` | `test_runbook_lane.py:3203-3208` (re-read), `:3184`; `test_runbook_lane_sonar.py:1033-1068` |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`); the orchestrator re-read the load-bearing points listed at the end of this section at the merge commit. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf for this landing — reason: the landing descoped its main deliverable after the PR body was written, so testing it means comparing the merged tree against a squash message, a spec and a landing narrative that disagree, and tracing the D2 binding through three verbs; that is the depth the Dispatch Decision Rule exists for, and one landing's read does not share context with another's.
- **Verdict:** layer 1 findings (3 minors, 1 not shown by reading); layer 2 findings (1 major, 1 major test defect, 8 minors); layer 3 findings (1 major, 9 minors). The three majors are the false squash message (L2-1), the D2(b) gap that the docstring itself admits (L2-2) plus the vacuous D4 test (L2-3), and the lane text that says a delegating consumer is never decided while the code decides it (L3-1).

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D2(b) asks that "a carried-forward count without its marking is refused" at the gate and the facts, but those verbs receive only flags the caller asserts and the spec names no token from the read that binds them; the verbs cannot tell a carried-forward count with no flags from a plain one. The spec asked for a check its own surface cannot make | checked | refutes | `runbook_lane.py:2085-2086` (re-read) |
| L1-2 | D5 asks for a recorded red run per new behaviour "incl. a real-classifier twin"; a twin pins behaviour that does not change, so it cannot have a behavioural red run. The spec contradicts itself; the lane's evidence table records both twins as `order: none` | checked | refutes | `test_runbook_lane_sonar.py:1033` |
| L1-3 | The premise "PLAN-LB-167 did not fix the delegating-consumer case" is partly wrong: this repository is itself a delegating consumer (`python-verify.yml:43` uses a reusable workflow, `:55` sets `skip-on-docs-only`) and the architecture documentation-surface fallback already classifies such a consumer's delta; which input counts as "not fixed" is not shown by reading | not_shown_by_reading | none | `runbook_lane.py:1592` (re-read) |
| L1-4 | Both HYPOTHESIS labels stay unverified on the merged tree: no code path reads a called workflow at a pinned ref (D1 descoped), and the cause of PR #2028's body is worded only "consistent with" | checked | confirms | `ci_base.py:213-218` (re-read) |

**Layer 1 verdict:** findings — 3 minors (L1-1, L1-2 are consistency defects of the spec; L1-3), 1 not shown by reading

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | none on the merged tree | none on the merged tree | **L2-1 (major)**: the squash message and PR body describe a delegated branch, `repo file read`, `delegated_*` refusals, "about 13" D1 tests and "§7's retry exemption covers every `delegated_*` refusal" as shipped; none exists, and `sonar-stale-delta` has no `--pr-number` (re-read) | checked |
| D2(a) | `sonar.py:1022`, `:1081-1087`, `:1106-1116` | `test_sonar_analysis_revision.py:472`, `:492` assert the fetch is not called, so they can fail | none | checked (confirms) |
| D2(b) | `runbook_lane.py:2087-2134`, `:2537-2584` | the gate and landing tests that pass the marker or omit it | **L2-2 (major)**: dropping all three flags still yields a plain `merge_allowed` and a current-head figure; `_carried_forward_revisions` returns `(None, None)` at `:2085-2086` and its own docstring (`:2073-2078`) says it "does not stop a plain figure being reported plainly". The spec's "non-opt-in" is not met; this is a different case from the recorded "a caller that invents all three" residue. The gate and the facts also never check revision format, so any two distinct strings pass | checked (refutes) |
| D3 | `ci_base.py:237-262`, `:311-313`, `:381-394` | `test_ci_base_cli.py` (+61) | `workflow-integration-gitlab/SKILL.md:122` is outside the Expected Surface and the standing write boundary; `tools-integration-ci/SKILL.md:230-237`, `api-contract.md:141`, `issue-operations.md:20-22`, `pr-operations.md:203-205` and `test_runbook_lane.py` are likewise not named by the declared surface (L2-5) | checked |
| D4 | `SKILL.md:848-877`, `:971-972` | `test_runbook_lane.py:3184`, `:3203-3208` | **L2-3 (major test defect)**: `test_the_lane_text_passes_the_carried_forward_marking_to_the_gate_and_the_facts` asserts `'--carried-forward' in section`, a substring of `--carried-forward-analysis-revision`, which the base §6 text already held, and its two other asserted strings were present at the base too; it was not red-first and stays green if the marker is dropped from the gate command (re-read). The absence check at `:3184` could not fire on the base text because the base sentence broke across a line (L2-4) | checked |
| D5 | `test_runbook_lane_sonar.py:1033-1068` | both twins exercise `_read_footprint_rule` and `_classify_paths`, which the diff does not change; they can fail on a regression and could not have been red at `a024fc8c2` for a behavioural reason | the recorded 20-failure runbook-lane red run included the 13 D1 tests `1506824a0` later deleted; which surviving lane tests were red is not shown | checked |

Findings: **L2-1** (major) above. **L2-2** (major) above. **L2-3** (major) above. **L2-4** (minor) the vacuous absence check at `test_runbook_lane.py:3184`. **L2-5** (minor) the files outside the declared surface, above. **L2-6** (minor) the narrative's "quoted-path handling … untouched by design" is contradicted by the diff: `_delta_paths` now runs `git diff --name-only --no-renames -z` and splits on NUL (`runbook_lane.py:1838`, the comment at `:1833` says `-z` is what keeps a path Git quotes whole, re-read); no deliverable explains it and no test feeds a path Git would quote. **L2-7** (minor) new refusal branches with no test that reaches them: `carried_forward_head_requires_an_analysed_revision` (`sonar.py:1086-1087`), a head flag without `--pr` (`:1076`), the facts `carried_forward_revisions_equal` refusal (`runbook_lane.py:2573-2584`), a leftover default file under an optional body (`ci_base.py:392`), and `not_configured` with `--carried-forward` (`runbook_lane.py:2340`, `:2467`). **L2-8** (info) the narrative's "red-first, including two real-classifier twins" does not agree with its own evidence table (`order: none`). **L2-9** (info) the PLAN-LB-170 doc-contract coupling holds: the diff does not touch `_read_review_surfaces`, its hunks are `15-26`, `1828-1871`, `2065-2135`, `2340-2351`, `2457-2588`, `4330-4400`, and the new banner at `:1844` sits outside the block the test extracts (`test_analyze_false_claim_contract.py:160-166`).

**Layer 2 verdict:** findings — 3 majors (L2-1, L2-2, L2-3), 5 minors, 2 info

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `SKILL.md:848-851` (re-read), `runbook_lane.py:1592` (re-read), `:1867-1868` | a delegating consumer whose workflow sets `skip-on-docs-only` and holds no `paths-ignore`, with a delta made only of documentation-module doc-suffix files (this repository, `doc/*.adoc`) | `_read_footprint_rule` returns an extra list with `skip` `None` (`:1368-1370`, `:1381-1418`) and `_classify_path` reaches `docs-only` through the architecture documentation surfaces, so the delta reaches `carry_forward: true` (`:1979-1983`); the lane text and the docstring at `:1867-1868` say the case is "not carried forward", while the docstring at `:1384-1389` says the opposite. The reader is told the case is undecided, while it is decided by a rule the CI does not apply | major |
| L3-2 | `SKILL.md:867-873` (re-read), `:970-973` | a reader following §6 and §7 | §6 makes all eleven stale-delta refusals no-retry blockers and lists `rule_unreadable` twice (`:869-870`); §7 exempts only `delta_buildable` and `rule_unreadable` from the general retry (`:971`). Both are artifacts of the descope commit, which replaced "every `delegated_*` refusal" with `rule_unreadable`. §6's "retrying cannot succeed" is also wrong for `worktree_dirty`, `worktree_not_at_head` and `revision_unresolvable`, which a corrected checkout settles | minor |
| L3-3 | `SKILL.md:122-127`, `runbook_lane.py:4330-4347` | a run copying the canonical `sonar-gate` block | the block omits `--carried-forward` and the two `--carried-forward-*` revisions the parser declares, and the skill has no canonical `sonar-stale-delta` block although the module docstring at `:18-19` lists it; D4's "the documents state what the code does" is incomplete | minor |
| L3-4 | `ci_base.py:211`, `:232` (re-read) | the slot `default` followed by a newline | `_BODY_SLOT_RE` ends in `$`, which `re.match` lets match before a trailing newline; `default\n` passes validation, is not equal to `default`, skips the `shared_body_slot_refused` check at `:252` and creates `pr-create-default\n.md`. No path traversal (`/` and `.` stay rejected); the anchor pattern is older than this diff, which widened only the length bound | minor |
| L3-5 | `runbook_lane.py:183-195` | a spec name with `_` or `.`, or a `{plan}` longer than 128 characters | `_plan_id_from_spec` only lower-cases `PLAN-[^/]+`, so the derived slot is rejected by `_BODY_SLOT_RE` and `prepare-body` answers `invalid_slot`; fails closed but stalls the lane at PR open. Confirms the recorded residue (a resolver-exposed, bounded `body_slot`) | minor |
| L3-6 | `sonar.py:1106` | an analysis revision unavailable while the head moved | the head-mismatch branch runs for any non-confirmed revision result, not only `stale_analysis`; the read is reported as `carried_forward_head_mismatch`, hiding the real reason. Still answers `undecidable` | minor |
| L3-7 | `ci_base.py:381-385` | an invalid slot at `read_and_consume_body` | `invalid_slot` is computed, then `get_body_path` raises on the same slot and the caller receives `invalid_kind`: misnamed, still fails closed | minor |
| L3-8 | `runbook_lane.py:4337`, `:4343`, `:4396`, `sonar.py:1069`, `:4390` | a flag spelling copied from another verb | one value carries four spellings: the analysed revision is `--analysis-revision` on `sonar-stale-delta`, `--analysed-revision` on the read and the facts, `--carried-forward-analysis-revision` on the gate; the head is `--head-revision` on the stale-delta and `--carried-forward-head-revision` elsewhere. `allow_abbrev=False` rejects the wrong spelling, so this fails closed: naming drift, not a bypass | minor |
| L3-9 | `runbook_lane.py:1844-1846`, `SKILL.md:851`, `test_runbook_lane_sonar.py:1009-1012` | a reader of the module | descope leftovers: a section banner heading no code of its own, "which is a separate body of work" in normative text, and the descope history in a test comment | minor |

**Layer 3 not shown by reading:** L3-10 — the read's `head_revision` is resolved from local refs (`test_sonar_analysis_revision.py:697-698` shows `rev-parse HEAD`); whether that is the PR head when the lane runs from the main checkout, and so whether the head binding compares two independent observations, is not shown by reading. A run would show it. Also not shown: which surviving lane tests were red in the recorded 20-failure run.

**Layer 3 verdict:** findings — 1 major (L3-1), 8 minors (L3-2 to L3-9), 1 not shown by reading (L3-10)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | Current state only | deviates | `SKILL.md:851` ("a separate body of work"), `test_runbook_lane_sonar.py:1009-1012`, the orphan banner `runbook_lane.py:1844-1846` |
| CLAUDE.md § Documentation Standards | No version history | deviates | `SKILL.md:781-782` and `test_runbook_lane.py:3155` cite the PR #2028 incident as history inside normative text |
| CLAUDE.md § Documentation Standards | No duplication | deviates | the shared-slot rule is restated in `tools-integration-ci/SKILL.md:230-237`, `api-contract.md:141`, `issue-operations.md:20-22` (which then says "not repeated per workflow below"), `pr-operations.md:203-205` and `workflow-integration-gitlab/SKILL.md:122` |
| `ref-code-quality` error handling | Fail-closed gate semantics | conforms | `sonar.py:1076-1124`, `runbook_lane.py:2087-2134`, `:2537-2584`, `ci_base.py:252-262`; the one open direction is the caller dropping all three flags (L2-2) |
| `plugin-script-architecture` | Structured TOON errors, strict argparse | conforms | `runbook_lane.py:4280`, `:4352` (`allow_abbrev=False`) |
| `ref-code-quality` review rules | Test quality including negative cases | deviates | the vacuous test `test_runbook_lane.py:3203-3208` (re-read), the vacuous absence check `:3184`, the untested refusal branches of L2-7 |
| PLAN-LB-171 standing constraint | No file outside the lane, the Sonar skill, the CI body-slot path, `land.md` and their tests | deviates | `workflow-integration-gitlab/SKILL.md` was edited (the merge stat shows it) |
| PLAN-LB-171 standing constraint | `--dismissed-keys` stays refused | conforms | `runbook_lane.py:2315-2326` unchanged |
| PLAN-LB-171 standing constraint | A buildable delta stays undecidable; no invented glob or job-name lists | conforms | `runbook_lane.py:1971-1977`; the D1 job-graph code was removed in `1506824a0` |
| CLAUDE.md § Merge Authorization | A failing gate still blocks the merge and is reported | deviates, with the operator's recorded override | source is the landing narrative, not the tree: `review-gate` answered `merge_allowed: false` (`thread_concern_remains`), the operator chose "Merge anyway (operator override)" with the gap named in the question. Recorded as an operator override of one gate condition, never as a gate pass |

**Re-read by the orchestrator at the merge commit (which points were re-read):** the squash message against the tree (`git grep` for `delegated_`, the D1 test names and `_read_delegated` over `c22d103fb` — no hits); `runbook_lane.py:2065-2134` (the marker helper and its docstring, L2-2); `runbook_lane.py:1546-1595` (the doc-surface fallback at `:1592`, L3-1); `runbook_lane.py:1833-1838` (the `-z` change, L2-6); `SKILL.md:848-877` and `:971-972` (L3-1, L3-2); `test_runbook_lane.py:3203-3208` (L2-3); `ci_base.py:211-262` (L3-4); `land.md:135`, `:142` and the merge stat (the outside-surface edit). **Not re-read, recorded as unverified leads:** L2-4's claim about the base wording at `:3184`, L2-7's missing-test claims, L3-3, L3-5 to L3-8, the leaf's claim that no default-slot caller remains, and the layer-2 D5 red-run reading.

## Metrics and Anomalies

- Tokens: `unknown` (the harness measured none; recorded as an unobserved fact, never a zero).
- Duration: not recorded by the landing.
- Anomalies: five self-review rounds (the lane's limit is three; the operator authorised a fourth, and the fifth verified the fourth's closures); round 4 found a blocker (the decider/gated pair picked up plumbing jobs, so the real reusable workflow refused on the normal shape) in code that was then descoped; the lane's progress file records none of the descope, the merge override or the amendment — the descope commit `1506824a0`, the override and the re-staging are in the landing message alone, and the file stops at `verify at 88ba55d5f`; the landing message was filed at revision 2 before the merge and amended to revision 4 after it.

## Routing and Merge Behavior

- Review: coderabbit and sourcery were triggered on `66825feec`. `review-gate --pr-number 2033` on the merged head reproduces the landing's `unresolved_review_threads` (**0**) and `review_body_findings_total` (**16**). The verb answers `merge_allowed: false`, reason `body_findings_undisposed`, with `review_body_findings_handled` 0 because no `--disposition` was supplied to the re-read; the landing's `review_body_findings_handled=16` is **not re-verified**, as the progress file holds no `finding:` lines. That is not evidence the landing lied.
- CI/merge: merged through the merge queue as `c22d103fb`; the merge-group run is reported `success` by the landing. The merge was an operator override of the `review-gate` thread-concern condition on a thread about the removed delegated branch (recorded under Conformance). Cleanup: worktree removed, branch deleted locally and on the remote, the main checkout fast-forwarded (landing; the lane's `cleanup_owed=false`).
- Collision: PLAN-LB-168 (also in `runbook_lane.py`) had merged first as #2030; no rebase conflict is recorded.
- Sonar: `sonar_open_new_issues=n/a`, an answered absence (the epic does not read Sonar); nothing to compare.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-171 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-171 --field pr --value 2033`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-171 --field landing --value landings/PLAN-LB-171.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-171 --field plan_marshall_plan_id --value lb-171-lb-167-completion-delegating-checkout-gate-binding-body-slot` (the `{plan}` the sender `rb-{plan}` carries)
- [x] epic.md narrative reconciled against the queue rows (Open Defects, Watches, queue annotation)
- [x] landing message archived after the disposition was persisted
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

- **The delegating-consumer case (D1) is re-staged by the lane, not by this run.** The landing says it is re-staged as its own plan; no spec for it exists in this epic's corpus yet. It goes into the single fix plan the operator ordered, or into its own plan on the operator's word: its review asked for run-identity evidence, which needs a CI-abstraction field that does not exist, and L1-3 and L3-1 above are its premises to re-ground first.
- **The single fix plan** (operator instruction, `epic.md` Decisions) takes the layer-2 and layer-3 findings above that carry a behavioural edge: L2-2 (the D2(b) opt-in), L2-3 and L2-4 (the vacuous tests), L3-1 (the false delegating-consumer sentence), L3-2 and L3-3 (the document contradictions), L3-4 (the trailing-newline slot). The rest stay Watches.
- **The false text of record on `main`** (the squash message and PR #2033's body describing D1 as shipped) is not edited by this run: a corrected body is the operator's call, as it was for #2028.
- **`/apply-changes` is owed** after this merge: PLAN-LB-171 changed bundle sources.
