envelope_version=1
sender_type=plan
sender_id=rb-lb-148-required-review-check-truth
epic=live-blockers
kind=landing
created=2026-11-14T15:02:58Z

guard: present (this harness enforces tool-call rules; the log is `.plan/temp/guard.log`)

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-148-required-review-check-truth
epic=live-blockers
pr=#1983
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2123
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=0
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

# PLAN-LB-148 — the required-review check tells the truth

Merged as `21c9a205d9fff7cc33ea470d8fc8c85cfeebf333` (PR #1983), four commits:
`5865773fb` (D1–D5), `2bce9acf2` (lane-text literal), `632ab1f37` (self-review fixes),
`10079bac1` (the reviewer's finding).

## 1. Deliverables

Every Done-when was graded as written. `order` is one of `test-first` /
`mutation-after` / `none`; where it is not `none`, the failing run is named by commit and
log identifier. The mutations were applied to the committed tree, the failing run captured,
then reverted — the tree at each pushed head is byte-identical to its commit.

**D1 — the required-reviewer check reads the raw comment bodies.**
- *quoted marker in A, B, C and in blockquoted / inline-code / indented shapes answers
  `required_review_missing`, through the lane's real read seam with the raw body* — **met**;
  `order: mutation-after`; tests `test_a_quoted_marker_is_not_a_qualifying_review[A…, B…, C…,
  D-blockquoted-marker, D-inline-code-marker, D-indented-marker]` (six params, stubbing only
  `subprocess.run` and `github_re_review.fetch_pr_comments_data`); failing run `5865773fb` +
  mutation (flattened reading reintroduced at the lane's site) — `python-2026-11-14-110207.log`,
  6 failures; fixed in `5865773fb`.
- *a required reviewer whose raw read is incomplete or failed answers `undecidable_read`* —
  **met**; `order: mutation-after`; `test_an_incomplete_raw_read_is_undecidable_never_missing[truncated|failed]`;
  same log (it answered `required_review_missing` under the mutation); `5865773fb`.
- *these hold at `c9dcfd290`: a marker on its own line after prose is a qualifying review; a
  marker inside a plain closed fence is not; a fence-like run in prose is not a closing fence;
  several comments each carrying a marker each count* — **met**; `order: none` (green at HEAD,
  `python-2026-11-14-115057.log`, 94 passed). Their base behaviour is what the flattened-input
  tests this change moves to raw input pinned; two of those controls are also red under the
  mutation above, which is why they are reported as controls rather than as base-sha evidence.

**D2 — the one predicate refuses both refusal shapes.**
- *a case-variant registered refusal with a commit and no notice shape is not a finished review at
  the producer, the post chokepoint and the lane* — **met**; `order: mutation-after`;
  `test_a_case_variant_refusal_is_a_refusal_at_both_sites` plus shape-table row
  `case-variant refusal with a commit` (driven through all three sites); failing run
  `5865773fb` + mutation (casefold removed, `review_coverage_is_finished` restored) —
  `python-2026-11-14-110300.log`, 5 failures.
- *a refusal with a `{"kind":"reviewed"}` marker that names no commit, beside a non-empty
  `commit_id`, is not a finished review at all three sites* — **met**; `order: mutation-after`;
  `test_a_commit_less_marker_does_not_lift_a_refusal` plus row
  `refusal with a commit-less marker and a commit`; same log.
- *a refusal whose finished marker names a commit is a finished review; a refusal with a commit
  and no marker is not* — **met (holds)**; `order: none`;
  `test_a_marker_beside_a_refusal_notice_is_still_a_finished_review`,
  `test_a_refusal_naming_a_commit_and_no_marker_is_not_a_finished_review`, row
  `refusal with a commit and no marker`; `python-2026-11-14-115218.log`, 32 passed.

**D3 — the label's fixture is the real block.**
- *the label test's fixture carries the real icon URLs of the captured block* — **met**;
  `order: mutation-after`; `test_the_no_reviewable_changes_block_is_the_captured_one`; failing run
  `5865773fb` + mutation (placeholder icons restored) — `python-2026-11-14-110207.log`;
  fixed in `5865773fb`.
- *a review body that carries the block beside a findings section reads only the findings, with no
  refusal; a counted title that is neither a findings section nor a listed label is still refused;
  the existing label tests pass* — **met**; `order: none`;
  `test_the_captured_block_beside_a_findings_section_reads_only_the_findings`,
  `test_a_counted_title_that_is_neither_a_section_nor_a_label_is_undecidable`, and the four
  `Files …` label tests; `python-2026-11-14-115057.log`. The second clause required no edit: the
  allow-list is untouched and still closed.

**D4 — the pins cover what the review found uncovered.**
- *deleting the refusal arm turns at least one shape-table row red* — **met**; `order:
  mutation-after`; `test_every_site_reaches_one_verdict_per_artifact` (3 rows red, including
  `refusal with a commit and no marker`, the row the base table did not have) —
  `python-2026-11-14-110414.log`.
- *the table's lane column is driven through the lane's read seam with a raw body, so a second
  predicate planted at the lane's site turns a row red* — **met**; `order: mutation-after`;
  same test, 2 rows red — `python-2026-11-14-110532.log`.
- *these hold at `c9dcfd290`: the three participation-site population tests fail on a planted
  unguarded site* — **met (holds)**; `order: mutation-after`; all three modules raise
  `UnrecordedSiteError` at import when `participation_evidence` is planted in an unrecorded file —
  `python-2026-11-14-110800.log`.

**D5 — the prose and the comments say what the code does.**
- *the documentation test pins each corrected statement in the section that states it, with a
  planted-old-sentence control that ends in an assertion that the checker fails on the planted
  text* — **met**; `order: mutation-after` (the planted control IS the mutation, and the pins were
  red before the statements were corrected); the six `_REQUIRED_REVIEW_PINS` cases; first run
  `python-2026-11-14-105316.log` (one pin missed its section window — red), green in
  `python-2026-11-14-105443.log`, 68 passed.
- *every snippet the existing pins in `test_review_complete_after_handling_docs.py` name still
  passes* — **met**; `order: none`; the pre-existing `_SURFACE` / `_DONE_ARM_PINS` cases, same log.

**Per-head runs** (full `module-tests`): `5865773fb` → 33874 passed / 2 failed (this change's own
lane contract named a reviewer bot — `python-2026-11-14-110857.log`); `2bce9acf2` → the full run at
that head is the `110857` run's successor (targeted `test_runbook_lane*` 360 passed,
`python-2026-11-14-112638.log`); `632ab1f37` → **33877 passed, 0 failed**
(`python-2026-11-14-122312.log`); `10079bac1` → **33878 passed, 0 failed**
(`python-2026-11-14-132023.log`); merged head `814bb9b2c` → **33878 passed, 0 failed**
(`python-2026-11-14-135441.log`). Quality gate (ruff + mypy + plugin-doctor) green at each commit.

## 2. Personas and skills

Per deliverable, from the spec's own `Persona:` / `Skills:` lines, loaded as standards:

- D1, D2, D3 — `persona-implementer`; `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`.
- D4 — `persona-module-tester`; `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.
- D5 — `persona-documenter`; `pm-documents:ref-documentation`.
- Self-review and PR-comment triage — `persona-code-reviewer` (one `general` sub-agent, one round).

No skills were added for surface drift; the change stayed inside the spec's Expected Surface.

## 3. Hypotheses

- **D1 — the lane's process working directory equals the `project_dir` the in-process raw read
  needs**: **confirmed**, and the code no longer relies on it. `github_ops.run_gh` →
  `ci_base.run_cli` honours the process-global default cwd (`github_ops.py:162-170`,
  `ci_base.py:814`), so `_read_required_review_comments` calls `set_default_cwd(project_dir)`
  explicitly — the same anchor the display read's `cwd=` gives it (`runbook_lane.py:2698-2703`).
- **D2 — the producer's consumers tolerate a narrower `finished_review_bots[]`**:
  **confirmed**; `pre_merge_gate.py` and `review_completeness.py` read the set's MEMBERSHIP, never
  a count, so a narrower list loses an exemption and can never manufacture one.

## 4. Findings

- **Self-review (one round, `persona-code-reviewer`)**: 7 findings; 6 fixed in `632ab1f37` and
  `10079bac1` — the chokepoint docstring still described the old exemption; the new `undecidable`
  sentence over-claimed (now names the `review_state_undecidable` arm only); four
  change-history sentences introduced or left in the touched files; the several-comment pin did
  not literally use several marker-bearing comments; the captured block lacked a
  beside-a-findings-section pin; a participation-loop docstring named the wrong reader; one unused
  test import removed. 1 accepted with reason: the raw read sets the process-global cwd (one
  command per process, and the display read passes its own `cwd=`).
- **CI**: the full run at `5865773fb` failed two lane-text neutrality tests because the new
  refusal sentence named a reviewer bot — fixed in `2bce9acf2`.
- **PR review (CodeRabbit)**: one Major finding, `outside-diff-1` — *fold the body before the
  no-unreviewed-commit literal test*: recognition became case-insensitive while `refusal_condition`
  and `refusal_cause` stayed case-sensitive, so a capitalised "already reviewed the last commit"
  would be recognised and then routed to a wait it cannot use. Real defect, introduced by D2.
  **Fixed in `10079bac1`** (both overlays fold case, with
  `test_refusal_cause_and_condition_fold_case_like_the_recognition_arm`). No thread existed (the
  reviewer posts outside-diff findings in the review body), so the disposition is the progress
  line `finding: coderabbit outside-diff outside-diff-1 — 10079bac1`.
- CodeRabbit's re-review of the merge head reported **no actionable comments**.

## 5. Reviewers

| Reviewer | Required | Outcome | Head | History |
|---|---|---|---|---|
| `coderabbit` | yes | reviewed | `632ab1f37` (first review, one finding), then `814bb9b2c` (delta: nothing to report, `Merge Risk: Minimal`, marker names the merge head) | triggered with `@coderabbitai review` at 12:43Z; quota-limited, `review_complete_after_handling` — its review on record is the review, so no re-trigger was posted for a later head; it re-reviewed the merge head on its own incremental pass |
| `sourcery` | no | refused | — | triggered at 12:44Z; refused on its weekly budget ("4 days and 14 hours"); optional, so it does not gate |

## 6. Operator questions

1. *"PR #1983 merged as 21c9a205d. The worktree is clean except for `uv.lock`, which the build
   toolchain refreshed … How should the worktree be cleaned up?"* — options *"Leave the worktree,
   report cleanup_owed"*, *"Force-remove the worktree"*, *"You clean it, then I finish"*;
   **selected: "Force-remove the worktree"**. The removal ran as authorized; `cleanup_owed=false`.

No free-text operator messages beyond that answer.

## 7. Rule check

- **Guard**: present on this harness. The audit log is `.plan/temp/guard.log`.
- **Shell refusals (2, both obeyed, no workaround)**:
  - R1 at the first call — a `cd … &&` chain; re-issued as a single command.
  - R2 — a `cp` of the committed test files into the base worktree; the base-evidence run was then
    captured with the `mutation-after` order instead (see below), which needs no file copy.
- **Spec read**: `spec_source=ledger_worktree`, no `spec_differ` marker — the ledger copy was read
  and the main checkout's copy did not differ.
- **`executor-skew`**: `not_applicable` (source checkout: the lane text is the checkout's own and
  the executor maps its scripts), answered and recorded, never asked about.
- **Base-sha evidence**: a detached base worktree was created at `c9dcfd290`
  (`worktree-create --detach`, `executor_in_worktree: present`), claimed with the
  `base-evidence-owner` marker, and removed with `git worktree remove` (no force). The failing runs
  were then captured with `mutation-after` rather than by copying tests into it — the copy the
  section describes was refused by the guard (R2), and `mutation-after` is the §1-sanctioned order
  that needs no copy. Every mutation was reverted; `git status` showed the tree identical to its
  commit before each commit.
- **One deliberate deviation, recorded**: `review-gate` was invoked through the WORKTREE's executor
  with the shell in the worktree, not through the main checkout's. The verb's decision is made by
  the very code this PR changes, so the merge gate had to be decided by the branch's code — the
  main checkout still carries the pre-change lane. The form stayed relative
  (`python3 .plan/execute-script.py …`).
- **Routed builds**: every build ran through the resolved `build` commands; no `./pw`, `pytest`,
  `ruff`, `mypy`, `gh`, `glab` or inline Python was invoked directly.
- **Operator messages**: one question (above). No model switch during the run.

## 8. Build server

- Setup preflight on the worktree: **ready** (enrolled, version 1).
- Mechanisms: **daemon_longpoll** for the 7 full-suite runs; **in_process_fallback** for the 22
  targeted and quality-gate runs (explicit `--execution-mode in_process` while iterating, and for
  the two runs that had to finish inside the harness's own shell budget).
- Fallbacks/retries, one per build: one **bound expiry** on the full suite (`timeout_used_seconds:
  1260`, `timeout_source: explicit`) — continued with the split form's `module-tests` part alone at
  `--timeout 1800`, which then ran green; no launch fault occurred, so no launch-fault retry was
  needed.
- One full run reported a home-level pollution-guard error from `test_comments_stage_fetch.py` (a
  module this change edits in its docstring only); the module passes alone
  (`python-2026-11-14-122220.log`) and the next two full runs are green, so it is recorded as a
  cross-process flake, not a build failure of this change.
- No `killed` job. No `runtime_stamp_reason` was carried by either resolve (the executor version
  moved from `0.1.2076` to `0.1.2123` because main's executor was regenerated by the base merges).

## 9. Residue

- **A blockquoted counted section is invisible to the findings parser.** CodeRabbit posted this
  PR's one finding as an `Outside diff range comments (1)` block, entirely blockquoted
  (`> [!CAUTION] … > <details> > <summary>`). `review-gate` reported
  `review_body_findings_total: 0` for it, on this head and on the two before it — the block never
  becomes a section, so a finding of that shape is neither counted nor disposed. The finding itself
  was fixed regardless (`10079bac1`), and the parser is explicitly out of this plan's scope ("keeps
  the flattened read … out of scope"), but a review body whose findings ALL ride in a blockquoted
  outside-diff block would read as `all_handled`. Worth a plan of its own.
- `uv.lock` on `main` pins `ruff 0.17.3` while `pyproject.toml` requires `>=0.17.4` (from #1978), so
  every fresh worktree refreshes it on its first build. That churn is what the cleanup question
  above was about; it is reproducible toolchain state, in none of this plan's commits.
- The spec's Claim Label "no PLAN-LB-136 worktree exists yet" is now stale: a
  `lb-136-antigravity-standing-rules-and-task-gate` worktree exists. Its declared surface does not
  overlap this plan's, and no file of it was touched.
