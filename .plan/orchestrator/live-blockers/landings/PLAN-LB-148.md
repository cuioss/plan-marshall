# Landing Analysis: PLAN-LB-148 — the lane's required-review check reads the raw review and cannot be satisfied by a quoted marker or a refusal

epic: live-blockers
workstream: WS-05
pr: #1983

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-148.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `21c9a205d9fff7cc33ea470d8fc8c85cfeebf333`, a squash commit with one parent `3f8d54323` (the #1985 `uv.lock` refresh, read with
git). Runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`, executor `0.1.2123`. The message
`rb-lb-148-required-review-check-truth-001.md` is `complete: false` on `total_tokens` alone (`unknown`; out of scope under the ruling of
2026-10-23, so no Open Defect). The squash carries 19 files, +678 -249.

## Deliverable Fidelity vs Spec

Read against `plans/PLAN-LB-148-required-review-check-truth.md` and the merge's file list (`git show --stat 21c9a205d`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the lane's required-reviewer check reads the raw comment bodies | shipped-as-specified, with one Done-when that cannot hold as written (L1-2) | `runbook_lane.py:2675-2723` (the in-process raw read, `undecidable_read` before the predicate), `:2726-2755` (no strip, no re-split), `:2920-2921`; `strip_fenced_regions` removed from `_github_pr.py` and `github_re_review.py`; no flag added |
| D2 — the one predicate refuses both refusal shapes | shipped-as-specified, plus an unplanned follow-up the spec's premise missed (L1-1) | `_github_pr.py:315-318` (casefold in the registry arm), `:588-594` and `:664` (exempt only on `review_coverage_names_commit`), `github_pr.py:2179-2181`; `refusal_cause` / `refusal_condition` folded in `10079bac1` after the reviewer's finding |
| D3 — the label's fixture is the real block | shipped-as-specified | `runbook_lane.py:2162` (the label appears once, not added twice), the fixture and its capture pin in `test_runbook_lane_review_gate.py` (not re-read) |
| D4 — the pins cover what the review found uncovered | shipped-as-specified | three rows in `test_finished_review_shape_table.py`, the lane column through the lane's two transport seams, the three population modules reseeded by description string only (leaf read; not re-read) |
| D5 — the prose says what the code does | shipped-modified: change-history wording remains in three touched places (L2-7) | `runbook-lane/SKILL.md`, `workflow-integration-github/SKILL.md`, the six `_REQUIRED_REVIEW_PINS` (leaf read; not re-read) |

Surface: the declared surface is 16 files plus three hypothesised population tests; the squash touches 19. Every declared file was touched except
`github_ops.py` (declared as a hypothesis, only if the lane read it directly; it did not). Two files are outside the declared list:
`test/plan-marshall/workflow-integration-github/test_comments_stage_filters.py` and `test_github_pr_refusals.py`, both explained by D2. The lane's
statement that it "stayed inside the spec's Expected Surface" is therefore not borne out (L2-6). The two files are unlisted in the spec, not unrelated.

## Three-Layer Analysis

- **Dispatch:** one read-only leaf (`execution-context-level-5`, resolved on the `orchestrator.analyze` surface) — reason: a full-ship landing is read by one leaf each, with no size qualifier; the leaf read the merged code and the diff against the parent, wrote nothing, and returned 38 findings and 9 conformance rows.
- **Re-read by the orchestrator** (a point not in this list is an unverified lead): `runbook_lane.py:2108-2170, 2189-2208, 2320-2392, 2395-2482, 2640-2760, 2820-2935`; `_github_pr.py:248-254, 584-595`; `github_re_review.py:1586-1595`; the merge's file list; the live `ci pr comments` body of #1983; the `review-gate` verdict on #1983; the lane's progress file.
- **Verdict:** layer 1 findings — 2 minor, 2 not shown by reading; layer 2 findings — 7 (1 unborne claim, 1 unexplained-file claim, the rest minor test or prose gaps); layer 3 findings — 1 major (L3-1), 2 minor (L3-2, L3-3). One further defect, a pre-existing parser gap the landing's residue named and the leaf did not find, is recorded as L3-4 below (major, orchestrator-reproduced).

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| — | The display read flattens and the data read does not | checked | confirms | leaf: `github_ops.py:649-657`, `_github_pr.py:2133-2139` (not re-read) |
| — | The post chokepoint asks the predicate about raw bodies and answers `None` on an incomplete read | checked | confirms | leaf: `github_re_review.py:1906-1925` (not re-read) |
| — | At the base the lane stripped fences from the flattened body and re-split on `<!--` | checked | confirms | the removed lines of `runbook_lane.py` in the diff (re-read as the removal) |
| — | Shapes D (blockquoted, inline-code, indented) are rejected by the raw reader | checked | confirms | leaf: `_github_pr.py:456-470` (not re-read) |
| — | The registry arm was case-sensitive while the pre-`c9dcfd290` chokepoint casefolded | checked | confirms | leaf: `c9dcfd290` diff (not re-read) |
| — | The predicate exempted a refusal on `review_coverage_is_finished`, which requires no commit name | checked | confirms | `_github_pr.py:588-594` (re-read) shows the stricter test that replaced it; the old line is the diff's |
| — | `_NON_FINDING_SECTION_LABELS` is closed and the label appears once | checked | confirms | `runbook_lane.py:2149-2167` (re-read) |
| — | The lane was the only user of `strip_fenced_regions` | checked | confirms | leaf: git pickaxe over the three files that held it (not re-read) |
| — | HYPOTHESIS: the lane's cwd equals the `project_dir` the raw read needs | checked | confirms (superseded) | `runbook_lane.py:2698-2701` (re-read): `set_default_cwd(str(project_dir))` explicit |
| L1-1 | D2's premise "every refusal consumer reads `refusal_layers`" | checked | refutes | leaf: `_github_pr.py:908-911, 952-955`; `refusal_cause` and `refusal_condition` kept their own case-sensitive tests, folded only after the reviewer flagged them (`10079bac1`); the lane's progress file line 38 agrees (not re-read at the lines) |
| L1-2 | D1's Done-when "fails at `c9dcfd290`, driven through the lane's real read seam" | checked | refutes | leaf: `github_re_review.fetch_pr_comments_data` does not exist at `c9dcfd290`, so a seam test errors at its monkeypatch rather than failing on the verdict; red is showable only by mutation, which is what the lane did (not re-read) |
| L1-3 | The lane is the only Python caller of the `pr comments` command line | not_shown_by_reading | none | needs a repository-wide content search the leaf's envelope could not run |
| L1-4 | HYPOTHESIS: `pre_merge_gate.py` and `review_completeness.py` tolerate a narrower `finished_review_bots[]` | not_shown_by_reading | none | the lane's progress file (line 15) states it confirmed membership-only reads; the leaf did not read them and neither did this analysis |

**Layer 1 verdict:** findings — 2 minor (L1-1, L1-2); not shown by reading — 2 (L1-3, L1-4)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook_lane.py:2675-2755, 2874-2886` (re-read) | the six quoted-marker params, truncated and failed reads, driven through `github_re_review.fetch_pr_comments_data` and `subprocess.run` only (leaf; not re-read) | L2-1 the "several comments each count" test cannot fail for its own defect: both comments carry a qualifying marker for the one required reviewer, so a loop reading only the first still passes; L2-2 no test reaches the new `except` at `runbook_lane.py:2704` or a success envelope with no `complete` key; L2-3 the `restore_default_cwd` fixture resets the default cwd to `None`, a presence-keyed teardown (leaf, test lines approximate; none re-read) | checked (traces), checked (L2-1 to L2-3, leaf only) |
| D2 | `_github_pr.py:315-318, 588-594, 664`; `github_pr.py:2179-2181`; `github_re_review.py:1596-1601` (leaf) | `test_a_case_variant_refusal_is_a_refusal_at_both_sites`, the shape-table rows (leaf) | none | checked |
| D3 | `runbook_lane.py:2162` (re-read) | `test_the_no_reviewable_changes_block_is_the_captured_one` asserts substrings of the module's own fixture, so it is self-referential (L2-4); whether the block is a verbatim capture of #1964 cannot be shown by reading | the label comment at `runbook_lane.py:2157` names #1971 while the fixture names #1964 — the spec itself names both (the label from #1971, the block from #1964), so this is not shown to disagree | checked (L2-4 leaf only) |
| D4 | the three rows and `_lane_admits` in `test_finished_review_shape_table.py` (leaf) | deleting the refusal arm turns row 61 red at every site, by reading | whether a planted unguarded site still fails the three population modules needs a run | checked; population guards not shown by reading |
| D5 | six `_REQUIRED_REVIEW_PINS` with planted-old controls (leaf); the three statements in `runbook-lane/SKILL.md` | the controls end in `assert not _states_done_rule(planted, …)`, weak by construction (L2-5) | L2-6 the surface claim, above; L2-7 change-history wording left: `github_re_review.py:1591-1594` ("It is now also VISIBLE", "far narrower than it was when this layer read `ignore_patterns`"; re-read) and `_github_pr.py:252-254` ("preserved BYTE-IDENTICALLY from when they were inline literals"; re-read), plus a broken line wrap in `runbook-lane/SKILL.md` near 878-880 (leaf) | checked |

Narrative claims tested against the diff: "no executor regeneration is owed" holds (no verb and no flag added; `runbook_lane.py:2906-2922` reads only existing arguments); "stayed inside the declared Expected Surface" does not (L2-6); "the change-history sentences were rewritten to present tense" does not hold in full (L2-7).

**Layer 2 verdict:** findings — 7 (L2-1 to L2-7), all minor; not shown by reading — the three population modules' guards

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `runbook_lane.py:2920-2921`, consumed at `:2834-2886` (re-read) | a required reviewer's review body, or inline threads, lands after the display read returns and before the raw read starts; the two are separate calls (a seconds-long subprocess, then an in-process fetch) | threads and body findings come from the first snapshot and the required-review presence from the second, so the gate answers `all_handled` / `merge_allowed: true` for a review it credits but whose findings it never read. At the base one read fed both. | major |
| L3-2 | `runbook_lane.py:2698-2705` (re-read) | `gh repo view` returns an owner of `null` or a non-object, so `get_repo_info`'s `.get` chain raises `AttributeError` outside the fetch's parse `try`; or an `ImportError` on the two imports, which sit outside the `try` | a traceback instead of `undecidable_read`; fail-closed by crash but unclassifiable, unlike the display read's "never a traceback" contract at `:2657-2661` (the `AttributeError` path is the leaf's reading of `github_ops.py:800`, not re-read) | minor |
| L3-3 | `_github_pr.py:588-594` (re-read) | a refusal body plus `{"kind":"reviewed","coveredCommitId":"pending"}` | `review_coverage_names_commit` treats any non-empty `coveredCommitId` or `sourceCommitId` as a commit with no shape check, so the refusal is a finished review at all three sites; the function predates the change, which makes it the sole refusal exemption | minor |
| L3-4 | `runbook_lane.py:2120-2131` (the section table), `:2189` (`_SUMMARY_RE`), `:2395-2482` (`_body_findings`) — all re-read; the live body of #1983 | a CodeRabbit review body in the CAUTION shape: `> [!CAUTION] > … > **⚠️ Outside diff range comments (1)** > > <details> > <summary>…Major · {finding title} · <code>file:line</code></summary><blockquote>…` | the section heading is a bold line, not a `<summary>`; the only `<summary>` tags are the finding's own title and `Suggested fix`, neither of which names a section or declares a count (`:944` has no space after its colon, so `_COUNT_SUFFIX_RE` does not read it). `_body_findings` therefore yields zero findings: `review-gate --pr-number 1983` reports `review_body_findings_total: 0` for a body holding one Major finding, and a review whose findings all ride in such a block reads `all_handled`. Pre-existing, outside this plan's declared scope (the spec keeps the flattened read and the findings parser out), reproduced by the orchestrator. | major |

The leaf judged the lane's residue claim "not borne out by the code" because it assumed the heading sat inside a `<summary>`; the live body places the
heading in bold text outside any `<summary>`, so the lane's residue stands. Blockquoting is incidental: the gap is the heading's location, not the `>` prefix.

Also read and not a defect: `set_default_cwd` installs a process-global cwd that is never restored and the raw read also runs after a failed display read — a one-shot CLI process, so a wasted `gh` call at most (the lane accepted it); the casefold widens the refusal match to a review body that quotes a registered phrase in any case, the fail-closed direction and the documented tradeoff (`github_re_review.py:1587-1594`).

**Layer 3 not shown by reading:** the leaf could not show what the lane's three review-gate runs actually parsed on the head before `10079bac1`; that needs the parser run on the captured body, which the live read of #1983 above now supplies for the current head.

**Layer 3 verdict:** findings — 4 (L3-1 major, L3-2 minor, L3-3 minor, L3-4 major)

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec standing constraint | fail closed: an incomplete or failed read is never a finished review at the merge gate | conforms | `runbook_lane.py:2708-2723, 2880-2882` (re-read); the `except` at `:2704` is partial (L3-2) |
| spec standing constraint | the gate never states a verdict about a surface it did not read | deviates | `runbook_lane.py:2920-2921` (L3-1) |
| spec standing constraint | one reader per concept | conforms | `is_finished_review` is the only predicate at `runbook_lane.py:2753`, `github_re_review.py` and `github_pr.py` (leaf) |
| spec standing constraint | the allow-list of non-finding titles stays closed | conforms | `runbook_lane.py:2149-2167` (re-read) |
| CLAUDE.md Documentation Standards | current state only, no change-history wording | deviates | `github_re_review.py:1591-1594`, `_github_pr.py:252-254` (L2-7) |
| spec standing constraint | the PR states whether an executor regeneration is owed | conforms | the PR body and the diff agree |
| spec Declared Expected Surface | touched files within the declared surface | deviates | two test files outside the list (L2-6) |
| spec standing constraint | tests use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so | not_shown_by_reading | the red runs are cited as mutation logs, which only a run verifies |
| spec standing constraint | no token or measurement work; no Sonar | conforms | the diff carries neither |

## Metrics and Anomalies

- Tokens: `unknown` (the lane wrote no figure; recorded as unobserved, not zero)
- Duration: about 4 h 48 min from the lane's session start (11:15 local, the progress file) to the landing message (15:02Z)
- Anomalies: the lane was told by the operator to force-remove its worktree because `uv.lock` was dirty there (the lock lagged `pyproject.toml` on `main`); #1985 has since refreshed it, so the residue is resolved. The lane's shell refusals (R1, R2) were both obeyed. One full run reported a pollution-guard error from a module it edited only in a docstring; it passed alone and in the next two full runs (the lane's account; not re-read).

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed `632ab1f37` with one Major outside-diff finding, fixed in `10079bac1`, and re-reviewed the merge head `814bb9b2c` on its own pass: "No actionable comments were generated in the recent review" and a marker naming `814bb9b2c` (read in the live body). Sourcery (optional) refused on its weekly budget (read). The lane's progress file records the disposition as `finding: coderabbit outside-diff outside-diff-1 — 10079bac1`. `review-gate --pr-number 1983` re-read: `unresolved_review_threads: 0`, `review_body_findings_total: 0`, `review_body_findings_handled: 0`, `all_handled` — the landing's three numbers agree with it. **The agreement is with a parser that undercounts this body by one (L3-4):** the review held one finding that the progress file disposed, so the true figures were 1 and 1, and the landing's `0` / `0` are not a false claim but an inherited parser result.
- CI/merge: #1983 `merged` as `21c9a205d` through the merge queue; the merge-group run `43604683472` concluded `success` (read through `ci pr queue-state`).
- Sonar: `n/a` — the project does not use Sonar.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-148 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-148 --field pr --value 1983`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-148 --field landing --value landings/PLAN-LB-148.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-148 --field plan_marshall_plan_id --value rb-lb-148-required-review-check-truth`
- [x] epic.md narrative reconciled: a landing entry, two Open Defects (the CAUTION-shape parser gap and the two-snapshot gate), a Watch for the minors, and a Decisions entry
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

No `corpus set-verdict` call was made: the verdict field serves the prep-ready admission of STAGED specs, and this spec's row is now shipped, so nothing would read it.

## Follow-Ups

- **L3-4 and L3-1, one surface (`review-gate`).** Reported to the operator; not staged — a fix plan for a defect the operator did not name is not an operator word.
- **L1-1, L1-2, L2-1 to L2-7, L3-2, L3-3.** Recorded as a Watch; nothing staged.
- **A harness sync is owed** for the `automatic-review`, `runbook-lane`, `phase-6-finalize` and `workflow-integration-github` edits; no verb or flag was added, so no executor regeneration is owed.
