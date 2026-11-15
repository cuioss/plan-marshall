# Landing Analysis: PLAN-LB-129 — `review-gate` reads a resolved thread by its last bot comment, counts a section by its declared count, and refuses placeholder evidence

epic: live-blockers
workstream: WS-04
pr: #1947 (merge commit `d1e4b512850fe81ac08f824098fd6d0eaa8f69da`, one parent `be02c096b`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent, and it changes four files (+492/-65) — `runbook_lane.py`, `runbook-lane/SKILL.md`, `test_runbook_lane_review_gate.py` and one line of `plan-orchestrator/standards/landing-payload-spec.md`. The landing's facts block (`pr=#1947`, `merge_state=merged`, `deliverables 3/3`) agrees with git. `total_tokens=unknown` is an unobserved fact, not a defect (token work is out of scope).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — last BOT comment decides a resolved thread | shipped-as-specified | `_thread_concern_remains` at `runbook_lane.py:2706-2720` takes the last bot-authored comment via `next(... reversed(thread) if _bot_of(...))`, returns false when there is none, and tests only its body against `_CONCERN_REMAINS_MARKERS`. Re-read. Tests named by the lane (`test_a_lane_reply_below_the_bot_s_restatement_does_not_discharge_the_concern`, the acknowledgement control) exist at `test_runbook_lane_review_gate.py:249` and following. |
| D2 — count from the declared count; undeclared count is not one | shipped-modified | `_declared_count` (2488-2502) reads the raw title, `_count_section_findings` (2526-2548) lets a declared count win and otherwise takes `max(row markers, nested counts)`. The refusal arm (2606-2609) now covers any counted title that is neither a section nor a declared non-finding label. Modified beyond the letter of the spec: `Additional comments (N)` is counted as an `additional` section (2297) rather than declared a non-finding label, with the reason recorded at 2312-2315 (the capture does not carry it). The spec's own hypothesis was refuted by the lane and said so. |
| D3 — evidence is a real commit or a real reason | shipped-as-specified | `_disposition_evidence_is_real` (2457-2468) reduces the evidence to `[a-z0-9]` and refuses the placeholder set (`''`, tbd, todo, na, none, later, wip, pending). `-`, `?` and `n/a` reduce to `''` or `na`. Re-read. |
| Spec hypothesis: provider publishes no `outdated` flag | confirmed (leaf, pickaxe) | Not re-read. The rule ignores the flag either way. |
| Spec "Verify-first (D2): capture a live review body through the CI abstraction" | not done as written | Every new gate-test body is constructed from the #1940 titles; the verbatim capture at `_github_pr_fixtures.py:425` is unused (leaf, not re-read). The lane records the label list as one capture deep. |

One file no deliverable names: `plan-orchestrator/standards/landing-payload-spec.md` (the spec's Expected Surface excludes plan-orchestrator files). The leaf read the edit as one added word, `and additional`, in the section list, a consequence of the new `additional` section. Accurate under the current-state rule; recorded as an unexplained-by-spec file whose edit follows from a lane choice. The edit itself was not re-read.

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace and the merged code — by one read-only leaf (`execution-context-level-5`, resolved on the `orchestrator.analyze` surface), and the orchestrator re-read the points recorded below as re-read. The reading is **by reading, no build, no test run, no write**: what only a run could show is tagged `not shown by reading`, never left as clean.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with the two sibling landings drained in the same scan.
- **Verdict:** layer 1 findings (2, minor); layer 2 findings (2, minor); layer 3 findings (6, minor) plus one point not shown by reading. No blocker or major.

Re-read by the orchestrator at `runbook_lane.py` 2292-2328, 2372-2384, 2440-2568, 2590-2609 and 2705-2720, and at `test_runbook_lane_review_gate.py` 247-256 and 314-330. **Not re-read** (recorded as unverified leads): `runbook-lane/SKILL.md` 182-206 and 850-867, `_github_pr_fixtures.py:425`, the landing-payload-spec edit, the pickaxe result for `outdated`, the test lines 347/445/487/500/518/530/541/736/745-773, the `_threads` order at 2693-2703, and `bot_registry.bot_kind_for_login`.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's D2 widens the refusal to every counted title outside a section or label, yet leaves the label list "to be completed from a captured body" and asks that observed titles not become false blocks. With one capture (#1940) the Done-when on false blocks cannot be met by reading alone. | checked (spec re-read) | refutes | spec D2; `runbook_lane.py:2316-2323` |
| L1-2 | The spec says the declared count wins but is silent on a declared count SMALLER than the row markers present; the code takes the declared value, which is fail-open for that shape. | checked (spec and code re-read) | refutes | spec D2; `runbook_lane.py:2538-2539` |
| — | D1's premise (the old gate tested `thread[-1]` only) holds at the base. | checked (leaf) | confirms | `runbook_lane.py:2716` |

**Layer 1 verdict:** findings — 2 (minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook_lane.py:2716-2720` | `test_runbook_lane_review_gate.py:249` and the stub parametrization | none | checked |
| D2 | `runbook_lane.py:2488-2548, 2606-2609` | the colon-counted, undeclared and undecidable cases (leaf: lines 317-347) | the lane did not use the verbatim #1940 capture (L2-2) | checked |
| D3 | `runbook_lane.py:2441-2468` | the placeholder and real-evidence cases (leaf: lines 518-541) | none | checked |
| — | `landing-payload-spec.md:105` | — | file outside the spec's surface, follows from the `additional` section (L2-1) | checked (leaf) |

- **L2-1 (minor):** the plan-orchestrator standard was edited though the spec excludes plan-orchestrator files. The edit is one word and follows from a lane choice.
- **L2-2 (minor):** the spec asks for the label list to be verified against a captured live body; every new gate-test body is CONSTRUCTED and three of them are not labelled so (leaf, `test_runbook_lane_review_gate.py` 347/445/487/500, not re-read). One docstring labels `Nitpick comments: 3` as OBSERVED while the observed title is `Nitpick comments: 1` (re-read, `test_runbook_lane_review_gate.py:318`).

The leaf also flagged the narrative's mention of `test_a_nested_file_summary_is_not_read_as_an_unreadable_section` as a test the diff does not add. The lane's own table lists it under controls "green at base", so it is not an overclaim and is **not** recorded as a finding.

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `runbook_lane.py:2538-2539` | `Nitpick comments: 1` over three `cr-comment` rows, or `: 0` over real rows | the declared count wins unconditionally, so one disposition clears three; contradicts the docstring's own reason at 2533-2535 | minor |
| L3-2 | `runbook_lane.py:2465-2468` | evidence `TBD later`, `todo: wip`, `n/a — see later` | the regex also strips spaces, so these collapse to `tbdlater`, `todowip`, `naseelater`, outside the set; the finding counts as disposed. The lane pinned `n/a — see later` as accepted. | minor |
| L3-3 | `runbook_lane.py:2454, 2465` | a reason written entirely in a non-Latin script | reduces to `''`, which is a placeholder, so a real reason is refused as `disposition_unparsable` (a wrong block, fail closed) | minor |
| L3-4 | `runbook_lane.py:2716-2720` | a restating bot comment spelt `still\napplies`, with a double space, or `has not been addressed`; or a later comment by a different bot | the marker is a lowercase substring, so a variant reads as discharged; any registered bot's later markerless comment discharges, even one other than the restating bot | minor |
| L3-5 | `runbook_lane.py:2542-2547, 2596-2599` | an uncounted last section followed by `Files selected for processing: 19` | a section with no declared count spans to the next recognised section or the end of the body, and nested counted summaries are summed, so phantom findings are minted. Fails closed, but the lane must dispose them | minor |
| L3-6 | `runbook_lane.py:2297, 2312-2315` | a counted `Additional comments (N)` | at base a hard `undecidable_read`; now clearable by N dispositions. More permissive than base for the counted form, stricter for the uncounted one; the disposition requirement stays | minor |
| L3-7 | `test_runbook_lane_review_gate.py:254, 326` | — | test docstrings describe the old behaviour ("Reading `thread[-1]` let it through", "The defect the colon spelling caused"), against the current-state documentation rule | minor |

**Layer 3 not shown by reading:**

- **L3-8:** any counted `<summary>` outside a recognised section that is not one of the six labels (`runbook_lane.py:2316-2323`) now refuses the whole gate (2606-2609), in every review body on the PR, at any depth inside an unrecognised wrapper. Plausible CodeRabbit titles that would trigger it: `Files skipped from review as they are similar to previous changes: N`, `Files with no reviewable changes: N`, `Learnings`, `Code graph analysis (N)`. The effect would be a permanent `undecidable_read` that a retry cannot clear. The leaf graded this a major but could not show it by reading; **the orchestrator's own `review-gate` reads of #1947, #1949 and #1951 on the fixed code parsed all three live CodeRabbit bodies without that refusal** (they returned `body_findings_undisposed` / `all_handled`), which is evidence against it for those bodies, not a proof for every body. Recorded as an unverified lead, held on the Watch.
- The `cr-comment:v1` row markers may or may not survive the CI display path; if they do not, row-marker counting never fires in production.
- Whether a bot comment with no author resolves fail-open through `bot_registry.bot_kind_for_login(None)`, and whether the provider returns a thread's comments in chronological order.
- Whether the tests were written first, and whether the `PLAN_MARSHALL_HOME` fixture applies through conftest.

**Layer 3 verdict:** findings — 7 (minor); not shown by reading — 1 (L3-8)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec standing | gate fails closed; no change makes it more permissive | deviates | `runbook_lane.py:2297` (counted `Additional comments (N)` clearable); D1 is stricter than base |
| spec standing | one reader: reuse the producer's predicates | conforms | the producer has no section counter or label predicate to reuse (leaf) |
| spec standing | documentation states current behaviour | deviates | `test_runbook_lane_review_gate.py:254, 326` describe old behaviour |
| spec standing | tests use captured live shapes or are labelled CONSTRUCTED | deviates | unlabelled constructed bodies; `:318` mislabels one as OBSERVED |
| spec standing | tests use the `PLAN_MARSHALL_HOME` fixture | not_shown_by_reading | conftest was not read |
| spec Expected Surface | no plan-orchestrator file | deviates | `landing-payload-spec.md:105` |
| spec D1-D3 | Done-when tests present and able to fail | conforms | tests named at `test_runbook_lane_review_gate.py:249` and following; test-first order not shown by reading |
| CLAUDE.md § Documentation Standards | no version history, no timestamps | conforms | the SKILL.md and standard edits carry no dated wording (leaf) |
| CLAUDE.md § Workflow Discipline | no shell file operations | conforms | the lane issued none; one `df -h /tmp` read outside the repository is reported by the lane itself |

## Metrics and Anomalies

- Tokens: `unknown` — not measured by the harness; recorded as an unobserved fact. Token and measurement work is out of scope for this epic, so the `landing-check` `missing_keys: [total_tokens]` verdict is no defect.
- Duration: the inbox message is stamped 2026-11-09T21:52:22Z; the lane's own times are not summarised in the report.
- Anomalies: four self-review rounds (the operator authorised a fourth); the first full `module-tests` hit the known xdist target-tree race; a routed `verify` failed 1049 tests on transient `No space left on device` in `/tmp`. That is the inode-exhaustion leak PLAN-LB-141 has since closed in the test harnesses. The lane also reported one guard refusal (`R7`, a main-checkout edit, corrected at once) and a `worktree-create` call that exceeded the tool timeout.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `59e4315da` (four nitpicks) and `7a1eca316` (clean). Sourcery (optional) refused on hard quota. Dispositions: nitpick-1 and nitpick-2 declined with reasons, nitpick-3 and nitpick-4 fixed in `7a1eca316`. Review numbers re-read with `runbook_lane review-gate --pr-number 1947` on the fixed code: `unresolved_review_threads` 0 (agrees with the landing) and `review_body_findings_total` 4 (agrees). `review_body_findings_handled` is **not re-verified**: the re-read was made without the run's progress file, so it reports 0 handled, which is the absence of a disposition record and not a difference.
- CI/merge: `verify / verify` success at the final head; the merge was a merge-queue squash with one parent. The merge gate was evaluated with the branch's own fixed `review-gate`, by the operator's selection, because the installed gate ran the pre-fix code (it read the PR's body as 0 findings, the false pass D2 closes). Future runs on `main` carry the fixed gate.
- Sonar: `n/a`, consistent with a project without Sonar.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-129 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-129 --field pr --value 1947`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-129 --field landing --value landings/PLAN-LB-129.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-129 --field plan_marshall_plan_id --value rb-lb-129-review-gate-thread-and-count-truth`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned; the drain's closing summary names the exact outcome.)

## Follow-Ups

- **Watch, not a plan:** the `review-gate` undecidable-title refusal (L3-8) and the minors L3-1 to L3-7. None is a confirmed major or blocker, so none is staged. Layer-3 findings are reported to the operator in the same turn.
- The PLAN-LB-129 `<picture>`-decorated `Nitpick comments` title Watch is retired by this landing: `_declared_count` and `_normalise_section_title` drop markup before matching (re-read, `runbook_lane.py:2484-2485, 2497-2498`), which closes the case on the code path. A live `<picture>`-decorated body was not exercised.
