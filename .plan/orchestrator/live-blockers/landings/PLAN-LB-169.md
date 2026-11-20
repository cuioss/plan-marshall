# Landing Analysis: PLAN-LB-169 — A `retired` functional-review verdict closes a deliverable only on the operator's own retirement decision

epic: live-blockers
workstream: WS-01
pr: #2029 (https://github.com/cuioss/plan-marshall/pull/2029)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (the merged code, the PR state through the CI abstraction, the lane's own progress file). The landing message is a lead, not a fact. Merge commit `f327251591aa1b065d63d44a456dd117dd328944` (parent `a024fc8c2`), squash, nine files, 693+/82-. Landing message: `rb-lb-169-retired-verdict-needs-its-own-operator-decision-001.md` (runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`). `landing-check`: `complete: false`, `missing_keys` = `total_tokens` only; per the standing ruling of 2026-10-23 that is no defect. `deliverables_done=4` of `deliverables_total=4`.

## Deliverable Fidelity vs Spec

The fix does what the spec asks for the `retired` route: nothing the leaf read closes a retired deliverable on a rewrite approval or on a record written before the change. The gaps are minor and sit around the fix (an untested refusal branch, an untested CLI path, an undisclosed beyond-spec fail-closed change, a stale PR body).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 a retirement is its own operator decision; `retirement_state` closes only on a retirement decision; the one predicate stays shared | shipped-as-specified: a typed `decision_type` on the entry (`rewrite` the default and the reading of every record without the field); the second alternative of the spec (refuse when the authorized text still stands) was not needed | `_criteria_snapshot.py:1445-1461`, `:1492-1507` (re-read); `manage-solution-outline.py:1743-1753` (re-read) |
| D2 the validator and the gate refuse a retirement on a rewrite approval with a named cause; grading continues; nothing closes | shipped-as-specified, with two additions beyond it (below) | `_review_support_validate.py:490-529`, `_criteria_snapshot.py:2186-2240` (re-read) |
| D3 the rubric and the functional-review workflow state how a retirement is recorded | shipped-as-specified | `review-rubric.md:33`, `functional-review.md:91`, `:280`, `:353`, `review_support.py:86-94` (leaf reading; the flag name, default and help text match the parser) |
| D4 tests pin D1 to D3, written against the unfixed tree first | shipped-modified: 14 tests (the PR body says 12) in a new module outside the spec's Expected Surface; seven of the eight reds at `46d3308ea` are a `TypeError` on the new keyword and one is behavioural | `test_retirement_decision_d4.py:168-454` (leaf) |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`); the orchestrator re-read the load-bearing points below at the merge commit. The working tree of the main checkout holds the nine paths byte-identical to `f32725159` (the leaf's `git diff --stat f32725159 HEAD`). The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf for this landing — reason: the change is a predicate shared by a validator and a completion gate across two bundles, and testing it for fail-closed behaviour means tracing odd inputs and the seal through the merged code, which is the depth the Dispatch Decision Rule exists for; one landing's read does not share context with another's.
- **Verdict:** layer 1 findings (2 minors); layer 2 findings (4 minors); layer 3 findings (no blocker, no major; 10 minors). No layer-3 defect fails open on the `retired` route.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec premise holds: the parent's retired branch returned before `_grade_criteria` and `retirement_state` read the type-blind `_authorization` | checked | confirms | `_review_support_validate.py:490` and the diff hunk at the parent's `:488` (leaf); `_criteria_snapshot.py:1428-1442` (re-read, `_authorization` is now documented as not deciding a retirement) |
| L1-2 | The spec's Expected Surface omits the new test module; its Standing Constraint allows "their tests" and D4 requires tests, so the surface is under-declared (a spec defect, not a lane deviation) | checked | refutes | the merge stat: `test_retirement_decision_d4.py` (+462, new) is on no declared path |
| L1-3 | The spec's Objective ("a rewrite approval can never close a deliverable") is broader than D1 to D4: the gate's type-blind exemption still closes rewrite-authorized frozen criteria under `met`, `not_met`, an out-of-vocabulary word and an absent verdict; that is the pre-existing criteria-drift design, and the spec's scope is the `retired` route only | checked | refutes | `_criteria_snapshot.py:2234` (re-read) |
| L1-4 | Verify-first (d): `landing-payload-spec.md` describes no authorization entry and needed no change | checked | confirms | `landing-payload-spec.md:211-214` (leaf); it lists no `retired` counter although the validator emits `deliverables_retired` (`_review_support_validate.py:102`), a pre-existing gap |

**Layer 1 verdict:** findings — 2 minors (L1-2, L1-3)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_criteria_snapshot.py:1445-1461`, `:1501` | `test_a_retirement_decision_closes_a_retired_deliverable` (`:168`), `test_a_pre_change_authorization_does_not_close_a_retired_deliverable` (`:187`) | the lane's "no other reader of `authorized_changes`" holds by a history search (sites `:1227`, `:1358`, `:1409`, `:1437`, `:1454`, `:1826`, `:1842`); the lane's own line numbers cite an older tree | checked |
| D2 | `_review_support_validate.py:490-529`, `_criteria_snapshot.py:2219-2236` | the validator and gate tests (`:206`, `:269`, `:339`); each would turn red if the predicate were reverted | two additions beyond D2: the `untrusted_verdict` rule (`:2193`, `:2230-2236`, re-read) and the "no criterion grades" error (`:514-520`, re-read) | checked (minor, L2-3) |
| D3 | the three documents | the existing doc-contract guards | none | checked |
| D4 | `test_retirement_decision_d4.py` | 14 tests drive the real `run_validate`, `open_criteria`, `retirement_state` and `authorize_change`; only `compute_test_integrity` and `_main_checkout_root` are monkeypatched | the module is outside the Expected Surface (L1-2) | checked |

Findings: L2-1 (minor) the recorded red run at `46d3308ea` shows the API absent more than the defect: seven of eight failures are a `TypeError` on the new `decision_type` keyword and only `test_a_pre_change_authorization_does_not_close_a_retired_deliverable` (`:187`) is a behavioural red (leaf, by reading the old code); it matches the PR body's own admission. L2-2 (minor) the PR body and the squash message say "12 cases" (the module has 14; `:322` and `:339` came with `1f5a77c07`), cite the green runs at `5d138cb35` and not at the final head, and do not describe the `1f5a77c07` changes. L2-3 (minor) `untrusted_verdict` (`_criteria_snapshot.py:2193`, re-read) fails closed by removing every decision exemption while the verdict is unsealed or unreadable, including the rewrite exemption of non-retired rows; it is beyond the spec and in neither the PR body nor the squash message. L2-4 (minor) `test_a_refused_retirement_carrying_no_grades_is_reported_ungraded` (`:309`) is named "reported ungraded" and asserts the `0 criteria rows` count error. Not shown by reading: whether the suite is green at the final head and whether any other test module relied on the unsealed-verdict authorization exemption.

**Layer 2 verdict:** findings — 4 minors

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_criteria_snapshot.py:2193` (re-read) | a deleted (absent) verdict file | an unsealed or unreadable verdict closes nothing on a decision, but an absent verdict still lets the type-blind `_authorization` close rewrite-authorized criteria; reachable only when every frozen criterion of the plan is authorized | minor |
| L3-2 | `_criteria_snapshot.py:2127-2146` | n/a | the `open_criteria` docstring still lists the authorization exemption without the untrusted-verdict carve-out at `:2189-2193`; the rubric is silent too | minor |
| L3-3 | `_criteria_snapshot.py:1726-1732` (re-read) | `authorize_change(decision_type='x')` | the `decision_type_invalid` refusal branch has no test (leaf, by history search) | minor |
| L3-4 | `manage-solution-outline.py:1743-1753` (re-read) | `criteria-authorize --decision-type retirement` | no test exercises the flag from the parser to the commit | minor |
| L3-5 | `_criteria_snapshot.py:2154-2263`, `:2230-2236`; `_review_support_validate.py:463-540` | n/a | `open_criteria` is about 110 lines and now holds a nested conditional expression; `_grade_row` about 78 lines | minor |
| L3-6 | `_review_support_validate.py:512-513` (re-read) | a refused retired row whose `criteria` is not a list | the value is coerced to `[]`, so the precise `criteria must be a list` error is lost; with outline criteria two overlapping errors fire (`:518`, `:408`) | minor |
| L3-7 | `_criteria_snapshot.py:1909-1916` | `authorize_change` success | the payload does not echo `decision_type`, so the operator cannot confirm the recorded type from the return | minor |
| L3-8 | `_criteria_snapshot.py:1824-1841` | a rewrite recorded after a retirement for one criterion | the verb keeps one entry per (deliverable, criterion) and the last write wins: a later rewrite downgrades a retirement (fail closed), a later retirement replaces a rewrite while drift stays exempt; undocumented and untested | minor |
| L3-9 | `review_support.py:506-507` | an invalid verdict | the grading findings of a refused row are computed and never published; only the errors show the grading | minor |
| L3-10 | `_criteria_snapshot.py:601` | a snapshot in the legacy `present` state (a file with no recorded freeze) | no digest check, so a hand edit adding `decision_type: retirement` would close; pre-existing (the same state already let whole entries be added) | minor |

Fail-closed, answered by reading (all at `f32725159`): `_retirement_decision` returns true only on `entry.get('decision_type') == 'retirement'` (`:1459`, re-read), so an absent type, `null`, `''`, `'Retirement'`, `' retirement'`, a list and a number all fail closed for `retired` while still passing drift through the type-blind `_authorization`; the API cannot write them (`authorize_change` returns `decision_type_invalid`, `:1726-1732`; argparse `choices=DECISION_TYPES`, `manage-solution-outline.py:1743-1753`, re-read); a hand edit of the typed field changes the snapshot bytes, so `snapshot_state` reads `tampered` and the validator refuses (`frozen_snapshot_tampered`), the gate answers `frozen_tampered` (open) and the verb refuses (leaf, `:596-600`, `:616-622`, `:2154-2168`, `:1764-1772`; seal is tamper evidence, not authentication); an entry whose criterion matches no frozen criterion is ignored and the criterion stays `unauthorized` (`:1501`, re-read); `retired` on a deliverable with no frozen criteria is `no_criteria` and the validator refuses it with "nothing to authorize" and still grades it (`:501-528`, re-read), while the gate has nothing to iterate (vacuous and pre-existing); a retirement for deliverable N does not close M (the check is keyed by number, `:1457`, re-read). ONE predicate: the validator calls `retirement_state` (`:491`, re-read); the gate calls `retirement_state` (`:2219`, re-read) and, per criterion, `_retirement_decision` (`:2234`, re-read), the predicate `retirement_state` itself uses (`:1501`); `_authorization` decides only drift and non-retired rows. The retirement goes through the same guard, commit, digest re-record, rollback and tamper path as a rewrite (leaf, `:1740-1742`, `:1796-1798`, `:1843-1908`); the decision-log line carries the type (`:1868-1875`, leaf) and the decision text stays required (`:1733-1739`, re-read). The CodeRabbit finding (an edited verdict falling back to the rewrite exemption) is fixed by `untrusted_verdict`, and `test_retirement_decision_d4.py:339-360` pins it (leaf). `criteria_drift`, `deleted` and `spec_criterion_missing` carry no diff hunk (leaf, `:1511-1690`). The refusal text names the criteria and the exact command (`_review_support_validate.py:496-500`, re-read), and re-running the verb with `--decision-type retirement` replaces the old entry (`:1824-1832`), so the advice works. No new `except`; the write stays atomic (`atomic_write_file`, `:1847`).

**Layer 3 not shown by reading:** the suite at the final head, the actual red counts at `46d3308ea`, the `--decision-type` flag end to end, and whether `untrusted_verdict` breaks another module that expected the old exemption. Only a run could show these.

**Layer 3 verdict:** findings — 10 minors, no blocker, no major; 1 not shown by reading

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec | fail closed for `retired` on untyped and rewrite records | conforms | `_criteria_snapshot.py:1459`, `:1501`, `:2234` (re-read) |
| spec | a rewrite approval keeps its meaning for drift | conforms | `_criteria_snapshot.py:1440`, `:1557` |
| spec | one predicate shared by validator and gate | conforms | `_review_support_validate.py:491`; `_criteria_snapshot.py:2219`, `:2234` (re-read) |
| spec | same guarded commit, rollback and tamper rules; the decision text required and logged | conforms | `_criteria_snapshot.py:1733`, `:1740-1908` |
| spec | `criteria_drift`, `deleted`, `spec_criterion_missing` unchanged | conforms | no diff hunk at `:1511-1690` |
| spec | no file outside `manage-solution-outline`, `phase-6-finalize` and their tests | conforms | `git show --stat f32725159`: nine files |
| ref-code-quality | a refusal branch the change adds has a test | deviates | `_criteria_snapshot.py:1726-1732` |
| ref-code-quality | a docstring matches the behaviour | deviates | `_criteria_snapshot.py:2127-2146` |
| python-core | no swallowed broad exception; atomic writes | conforms | no new `except`; `:1847` |
| CLAUDE.md Commit Trailer | exactly the plan-marshall trailer and nothing else by way of attribution | deviates | the squash message also carries a GitHub-added `Co-authored-by: cuioss oliver …` line, on every merge, not this plan |

Points re-read by the orchestrator at the merge commit: `_criteria_snapshot.py:1426-1507`, `:1722-1742`, `:2186-2242`; `_review_support_validate.py:486-531`; `manage-solution-outline.py:1740-1755`; the PR body of #2029. Not re-read, recorded as unverified leads: the seal and snapshot-state lines (`:596-622`, `:1764-1772`, `:2154-2168`), the commit path (`:1796-1908`), the documents' line numbers, the history searches for other readers and for untested tokens, the test counts and names, and every `not_shown_by_reading` point.

The leaf's own slips: it ran one Bash call with a backtick-quoted token in double quotes (a command substitution, `retired: command not found`, harmless, re-run with single quotes); it was granted neither Grep nor Glob and used `git log -S` history searches and `git blame -L` with regex ranges, not `git grep`; it read one large spilled tool output under `~/.claude/projects`; it skipped the dispatcher's logging and `resolve-workflow` steps under the read-only instruction.

## Metrics and Anomalies

- Tokens: `unknown`, an unobserved fact, no defect.
- Duration: the squash commit is dated 2026-11-19 22:46:35 +0000; the landing message was filed at 23:11:09Z.
- Anomalies: (1) the lane waited out two CodeRabbit quota refusals (17:40 and 19:38, each followed by a 90-minute wait) and was reviewed on the third trigger (21:10); Sourcery refused on a budget. (2) The lane's progress file records that it did NOT re-read the loaded lane text after the two 90-minute waits, with its reason (the installed copy was unchanged). (3) One routed `verify` (job `da6c90ee588b4da49486837b9624937c`) ended without a verdict at 69 % of its module-tests phase, recorded by the lane as an environment or supervisory termination; later `verify` runs completed green. (4) The lane self-reports two guard refusals (`R2` on an `rm` of a base-tree test file, replaced by `git clean -f -- <path>` and `git clean -fdx -- <path>`; `R1` on a `git commit -m` whose message quoted a field name in backticks) and one `printenv OPENCODE_SESSION_ID` call. (5) `harness=opencode`, `model=deepseek-v4.1-flash/high`, as for the other lanes of this pass, recorded as a fact with no conclusion drawn.

## Routing and Merge Behavior

- Review: the landing claims 2 review-body findings, 2 handled, 0 unresolved threads; coderabbit required (a formal review plus a marker-bearing summary naming `5d138cb35`; its two findings fixed in `1f5a77c07`, the inline thread answered and resolved), sourcery optional (refused on a budget, 1 day 2 hours). Re-read by `runbook_lane review-gate --pr-number 2029`: `unresolved_review_threads` 0 and `review_body_findings_total` 2 (coderabbit `inline-1`, `additional-1`) both agree with the landing. `review_body_findings_handled`: the gate's own read is `0` (`body_findings_undisposed`); the number is re-verified from the lane's progress file, which holds two `finding:` lines naming exactly those two ids, each with the commit `1f5a77c07`, so 2 agrees. No false claim.
- **The PR body of #2029 is this plan's own.** The squash message of `f32725159` describes this change and names all nine files. The same text is also the body and the squash message of PR #2028 (PLAN-LB-167): both PRs were created with the same body, which is the observed route recorded for #2028; see `landings/PLAN-LB-167.md`. The text on #2029 has since been revised (a `verify` run of 1537 s where the #2028 text says 1030 s), which fits the lane having edited its own PR body after creating it. That is an inference from the two texts, not a read of the edit.
- CI/merge: PR `#2029`, state `merged`, merge commit `f32725159`, base `main`; the lane reports `settle merged` (merge-group run `44631794551` success), cleanup done, branch pruned. Builds reported: 28 routed builds, all `daemon_longpoll`, no `killed` job, none re-run here.
- Collision with other plans: this merge lies in `manage-solution-outline` and `phase-6-finalize` and was declared disjoint from every running plan; no collision observed, so no declared surface needs correcting.
- Sonar: `n/a` and `step.sonar-roundtrip.open_issue_rules` `n/a`, the lane's `sonar: not_configured`; compared as the claim it is.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-169 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-169 --field pr --value 2029`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-169 --field landing --value landings/PLAN-LB-169.md`
- [x] row `plan_marshall_plan_id` stamped — value `rb-lb-169-retired-verdict-needs-its-own-operator-decision`, taken from the sender
- [x] epic.md narrative reconciled: the Open Defect "A `retired` functional-review verdict is accepted on any `criteria-authorize` entry (PLAN-LB-163)" is marked FIX SHIPPED; the minors go to the Watch
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **No fix plan is needed for the `retired` route.** The defect the plan was staged for is closed; the ten minors go to the BACKLOG Watch of `epic.md` under the focus rule. The two with a behavioural edge (L3-1, the absent-versus-unsealed asymmetry, and L3-8, the undocumented last-write-wins downgrade) are the ones a plan that already edits `_criteria_snapshot.py` should take.
- The spec's Expected Surface for this plan omitted its new test module (L1-2); the declared surface of a future fix of this module should name its test.
