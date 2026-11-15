envelope_version=1
sender_type=plan
sender_id=rb-lb-147-qualifying-review-one-reader
epic=live-blockers
kind=landing
created=2026-11-12T20:01:44Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-147-qualifying-review-one-reader
epic=live-blockers
pr=#1973
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=3
review_body_findings_handled=3
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# PLAN-LB-147 — one qualifying-review reader

PR #1973 merged into `main` at `c9dcfd290901f4e0889157c18c026968a5889cb2`. Branch and worktree removed; the main checkout is fast-forwarded to the merge commit.

## 1. Deliverables

Each Done-when is graded as written. Order is one of `test-first`, `mutation-after`, `none`; every failing run below came from mutating or reverting the committed fix.

**D1 — the post chokepoint and the lane use the producer's finished-review predicate (commit `6d158d139`)**
- Chokepoint reports an empty-`commit_id`, marker-less `review_body` as NO finished review, as the producer does — **met**, order `mutation-after`, test `test_the_chokepoint_refuses_an_empty_commit_review_body`; failing run `927984e7a`, `.plan/local/plans/NO_PLAN/build-results/plan-marshall/workflow-integration-github/python-2026-11-12-141911.log`.
- An enumerative-refusal body with a commit gets the same verdict from producer, chokepoint and lane — **met**, order `mutation-after`, tests `test_the_chokepoint_and_the_producer_agree_on_an_enumerative_refusal`, `test_an_enumerative_refusal_with_a_commit_is_a_qualifying_review`; failing runs `927984e7a` (`…141911.log`, `…142032.log`).
- The three "hold at base" cases (review with a commit; marker+commit; refusal+marker) — **met**, order `none` (they hold at base by construction), `test_the_chokepoint_and_the_producer_admit_*`.
- `_is_refusal_body` retired; the lane stops importing it — **met** (0 occurrences in the tree), same commit.
- Foreign-commit decision — **met**: left as-is; a named commit is accepted without checking it is one of this PR's heads. Disclosed in `workflow-integration-github/SKILL.md` § "The one handled review" and recorded in the PR body.
- Executor regeneration — **not owed**: no verb or flag added; the predicate is shared by import (stated in the PR).

**D2 — the three sites are pinned to agree, and the one test that pinned the disagreement is moved (commit `31ada0380`, typing fix `3d9733a04`)**
- Shape table over 8 artifacts × 3 sites, one verdict per artifact — **met**, order `mutation-after`, `test_every_site_reaches_one_verdict_per_artifact`; failing run `927984e7a`, `.plan/local/plans/NO_PLAN/build-results/plan-marshall/workflow-integration-github/python-2026-11-12-142032.log` (planted a second predicate at the chokepoint site).
- Invariant over `trigger-bot` and `request_fresh_review` — **met**, order `mutation-after`, `test_the_chokepoint_and_trigger_bot_never_both_hold`; same log; the empty-commit review and the refusal-without-marker rows failed.
- The empty-commit test moved to the agreed reading, never deleted — **met** (`test_a_formal_review_record_with_a_commit_refuses_the_trigger` + `test_a_formal_review_record_without_a_commit_does_not_refuse_the_trigger`).
- The scoped-join control gets its CodeRabbit subject back beside Sourcery — **met** (`test_the_same_finding_joins_for_its_own_pr[sourcery|coderabbit]`).
- Every done-rule test that passes today still passes — **met** (local `verify`, 33,749 tests green on the merged head).

**D3 — the prose and the comments say what the code does (commit `b1f1e0da5`, self-review corrections `293f9ae26`, CodeRabbit wording fix `2dde733fc`)**
- `resolve_recovery_action` item 8 + `SKILL.md` prose + table row admit `undecidable` and run ahead of every cause/window/budget arm — **met**, order `mutation-after`, `test_each_corrected_statement_is_pinned_in_its_section`; failing run `927984e7a`, `.plan/local/plans/NO_PLAN/build-results/plan-marshall/automatic-review/python-2026-11-12-142140.log`.
- `review_completeness.py` comment rewritten (done arm precedes the refusal arms) — **met**, same run.
- `github_re_review.py` "never reaches this line" corrected — **met**, same run.
- Comparative wording replaced in `bot_registry.py`, `branch-cleanup-rereview.md`, the `list_bots_for_trigger` docstring and `request_fresh_review`'s docstring — **met**, same run.
- Documentation test pins each corrected statement in its section, with a planted-old-sentence control — **met**, 11 pins + 11 per-pin controls; the failing run above is the real documents reverted to the old reading.

**D4 — the lane's re-split of a flattened review body is fence-aware (commit `927984e7a`, hardened in `2dde733fc`)**
- A review body that quotes a finished marker inside a fenced block is NOT a qualifying review — **met**, order `mutation-after`, `test_a_marker_quoted_inside_a_fenced_block_is_not_a_qualifying_review`; failing run `927984e7a`, `/home/oliver/.plan-marshall/marshalld/job-logs/d012b53de81246359be5694dc1784793.log`.
- The same marker outside a fence still counts; several flattened comments still split at each boundary — **met**, order `none` (hold by construction), `test_a_flattened_body_keeps_a_marker_outside_any_fence`, `test_a_flattened_body_with_several_comments_splits_at_each_boundary`.
- Hardened after CodeRabbit's finding: fence state is read from the runs (`strip_fenced_regions`) instead of reconstructed lines; the ` ```not-a-close ` counterexample is pinned by `test_a_fence_like_run_in_prose_is_not_a_closing_fence`.

Per-head test runs against pushed heads: `293f9ae26` (local `verify`, 33,707 tests), `2dde733fc` (local `verify`, 33,708), `b1a7118d0` (local `verify`, 33,749; CI `verify / verify` green). Every pushed head was tested.

## 2. Personas and skills

- D1: persona `implementer`; skills `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`.
- D2: persona `module-tester`; skills `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.
- D3: persona `documenter`; skill `pm-documents:ref-documentation`.
- D4: persona `implementer`; skills `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`.
- Self-review: persona `code-reviewer` (loaded by the sub-agent).
- **Gap reported:** the declared personas and domain skills were NOT explicitly loaded via the skill tool during implementation (see §7).
- No skills were added for surface drift.

## 3. Hypotheses

- H1 (refusal test home) — **confirmed**: `_is_refusal_notice` at `_github_pr.py:189`; `github_re_review.py` already imports from `_github_pr`. The duplicate's stated reason was false; the copy was removed with it.
- H2 (third lane reading) — **confirmed**: pre-fix `runbook_lane.py:2681`.
- H3 (null-commit review strands the PR) — **confirmed at the predicate level** (all three sites driven with one empty-commit fixture; the mutation run shows the chokepoint admitting it while the producer does not). The step-done guard's loop tail and `pre_merge_gate.py` were not separately exercised; D1 does not rest on them.
- H4 (~L141 test pins the empty-commit review) — **confirmed** and moved.
- H5 (flattened re-split after fences erased) — **confirmed**: pre-fix `runbook_lane.py:2692`.
- H6 (prose/docstring half at `SKILL.md` ~L1333 and `github_re_review.py` ~L926-933) — **confirmed**.
- H7 ("never reaches this line" false) — **confirmed**.
- H8 (comparative wording in four places) — **confirmed**; all four replaced.
- H9 (scoped-join control switched coderabbit→sourcery without need) — **confirmed**; coderabbit restored.

## 4. Findings

**Self-review round 1** (2 major, 7 minor, 3 preference):
- major — `_github_pr.py` participation-site record made false by the move: **fixed** in all three copies (`293f9ae26`).
- major — D2's planted-second-predicate evidence: **carried by the mutation-after run** above (the clause asks for a mutation at any one of the three sites; the chokepoint site was mutated).
- minor — `review_completeness.py` comment over-claimed reachability: **fixed** (`293f9ae26`).
- minor — retired comparative phrase in the re-review test docstring: **fixed** (`293f9ae26`, `2dde733fc`).
- minor — stale site notes in `test_participation_site_population_guards.py` / `_resolution.py`: **fixed** (`293f9ae26`).
- minor — `test_finished_review_one_reader.py` not in the Expected Surface: **declared** as D1's per-site evidence; kept.
- minors 8/9 (PR-body items, H3 loop tail): **stated in the PR** and §3 here.
- preferences 10-12: 12 addressed (the producer comment names the one reader); 10/11 accepted residue.

**Self-review round 2:** CLEAR, 0 open.

**CodeRabbit review** on `293f9ae26` (3 findings):
- `branch-cleanup-rereview.md:15` — the "re-reviewed whenever HEAD advances" sentence overstated Step 1's selection: **fixed** in `2dde733fc`, thread replied and resolved.
- `_github_pr.py:687` — the fence restoration could read a fence-like run in prose as a closer: **fixed** in `2dde733fc` (`strip_fenced_regions` + `test_a_fence_like_run_in_prose_is_not_a_closing_fence`), thread replied and resolved.
- `test_review_complete_after_handling_re_review.py:22` — exclude acknowledgments/skip notices with a commit: **declined with a stated reason** (the predicate is the producer's; the Done-when states as a hold that a `review_body` with a commit is on record; a bot's acknowledgment is an `issue_comment` shape), thread replied and resolved.

**CI:** `verify` red once on the first full run because the lane lost its participation-site marker when it stopped importing `_is_participation_evidence`; fixed by seeding `is_finished_review` in the scan (`ee2630907`) and correcting the site records.

## 5. Reviewers

| Reviewer | Required | Result | Head | History |
|---|---|---|---|---|
| coderabbit | yes | reviewed | `293f9ae26` (formal review, `COMMENTED`); done exemption (`review_complete_after_handling`) applies at every later head | triggered `15:47` → refused (rate limit, "next available in 31 minutes"); 90-minute wait; re-triggered `17:55` → accepted; review landed `18:02`; 3 findings handled; no re-trigger on later heads |
| sourcery | no | refused | — | triggered `15:47` → refused on its own review budget (6 days 9 hours); optional, does not gate |

Standing review authorization: coderabbit is quota-limited and `review_complete_after_handling`; its review on record is the qualifying review, so no later-head review was demanded.

## 6. Operator questions

None asked. No `question`/`AskUserQuestion` call was made; the merge was authorized by the standing merge authorization in `AGENTS.md`. No free-text operator messages.

## 7. Rule check

guard: present. The guard log (`.plan/temp/guard.log`) has no line for this run's session tree.

Reported from the run's own actions, not only the guard log:
- **5 read-class shell file operations** (the lane rule says files are read with the file tools): 3× `grep` on build logs, 1× `wc -l` on the guard log, 1× `git show <sha>:<path>` instead of the file tools.
- **1 shell `ls` of a directory outside the repository root** (`/home/oliver/.local/share/opencode/tool-output/`), when locating the truncated skill output. No file contents were read from there; only a filename listing.
- **No guard refusal** was recorded.
- No direct `pytest`/`ruff`/`mypy`, no `gh`/`glab`, no `python3 -c`, no `sleep`, no shell chaining, no direct build-wrapper call.
- A session restart did not occur; one sub-agent was dispatched twice (self-review rounds 1 and 2), the second continuing the first's session.
- Spec read: `spec_source=ledger_worktree`; no `spec_differ` marker.
- `executor-skew` verdict: `not_applicable` (source checkout) — answered, recorded, never asked about.

## 8. Build server

- Setup preflight: `ready`.
- Every build was submitted with the default routing: `daemon_longpoll` for all of them (module-tests ×10, quality-gate ×9, verify ×5). No fallbacks, no retries, no `in_process` runs.
- No `killed` jobs. A few submits waited in the daemon queue behind other sessions (up to ~1881s `queued_seconds`); every job then ran to a terminal result.
- `runtime_stamp_reason`: absent (no stamp fact failed to measure).

## 9. Residue

- `strip_fenced_regions` is a conservative reconstruction for the display-flattened read: an unterminated fence removes everything after it, and a genuine marker after a closed fence whose flattened line structure is ambiguous is withheld — the fail-closed direction (refuse and re-trigger, never credit a quote). The producer reads unflattened bodies and uses the exact line-based parser.
- The producer evaluates `_is_refusal_notice`/`_is_participation_evidence` immediately before `is_finished_review`, which re-evaluates them; harmless, and the pre-checks are load-bearing for the later arms.
- Sourcery could not review (its own budget); it is optional and does not gate.
- The plan's own worktree was removed after the merge; the landing-time resolve reports `executor_in_worktree: absent` / `worktree_not_created` because the tree no longer exists. Setup-time creation reported `present`.
- `cleanup_owed=false`: no base-evidence worktree was created (mutation-after evidence used no detached tree), and the plan worktree was removed with `git worktree remove` after a clean `status --porcelain`.
- H3's loop tail (the step-done guard and `pre_merge_gate.py`) remains unexercised, as disclosed in §3.
