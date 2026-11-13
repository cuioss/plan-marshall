# PLAN-LB-148: The lane's required-review check reads the raw review and cannot be satisfied by a quoted marker or a refusal, and a boilerplate block no longer stalls it

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-148-required-review-check-truth.md` and is queued as one row file, `queue/PLAN-LB-148.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-12 ("yes. stage, land and emit") as plan A of the per-surface fix plans settled the same day, from
> the residue of the PLAN-LB-147 landing (`landings/PLAN-LB-147.md`: one major, L1-4 with its document half L3-1, and the minors L1-1 to
> L1-3, L2-1 to L2-4, L3-2 to L3-4) and from the review-gate parser Open Defect (decision 5: add the observed title, keep the allow-list
> closed). One plan for one surface, per the operator's rule of 2026-11-11. Grounded against `main` at `c9dcfd290` by a read-only leaf that
> traced the fence constructions by hand, with the orchestrator re-reading the chokepoint's raw read, the display read, the lane's read seam,
> the predicate and the stripper, and tracing constructions A, B and C itself. Every Done-when below fails at `c9dcfd290` unless it says
> "holds at". No Sonar. No token or measurement work.

## Objective

The runbook lane decides whether a required reviewer has reviewed by asking one predicate, `_github_pr.is_finished_review`, but it asks it
about a different text than the producer and the post chokepoint do: it feeds the predicate the display read, which flattens every comment
body to one line, and then tries to rebuild fences and comment boundaries from the flattened text. Flattening loses what the raw marker
reader needs, so three fence shapes and three non-fence shapes (a blockquoted, inline-code or indented marker) still count a QUOTED finished
marker as the bot's review at the merge gate, and two docstrings say it cannot happen. The predicate also accepts two refusal shapes the
old reading refused (a registered phrase in another letter case, and a refusal whose finished marker names no commit), and a CodeRabbit
block titled "Files with no reviewable changes" makes the gate refuse a pull request for good. This plan makes the lane read the raw
bodies, closes the two refusal shapes, adds the observed title, pins all of it with the three-site shape table, and makes the prose say what
the code does.

## Deliverables

1. **The lane's required-reviewer check reads the raw comment bodies and no longer reconstructs structure from a flattened one.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `_required_reviewers_without_a_review` (`runbook_lane.py`) asks `is_finished_review` about the provider's RAW comment bodies, the text
     the producer and the post chokepoint already ask. The lane's `strip_fenced_regions` call and its `<!--` re-split are deleted, with
     the stripper (`_github_pr.py`) and its re-export (`github_re_review.py`) when the lane is their only user (verify-at-outline).
   - The raw read is in-process and needs no new CLI flag: either the lane asks `github_ops.fetch_pr_comments_data` directly, or it asks
     `github_re_review._qualifying_review_on_record(pr, bot)` once per required bot. Decide at outline and record why. The first reads once
     but gives up the provider routing the lane's `_CI_NOTATION` read has (the raw read is GitHub-only today); the second takes a second read
     at another moment than the findings read. A third form, a new flag on `ci pr comments`, needs a non-table encoding because a TOON table
     cell cannot carry newlines, and it adds a flag: it is allowed only if both in-process forms are shown unworkable, and then the PR
     states that executor regeneration is owed.
   - An incomplete or failed raw read is `undecidable_read` at the gate for a required reviewer whose review would be the only evidence: it
     is never read as "present" and never as "missing". The chokepoint's own `None` answer is a fail-open for a POST decision; the merge
     gate must not inherit it.
   - The findings parser (`_body_findings`, `_inline_status_findings`, `_thread_concern_remains`) keeps the flattened read; it was written
     to work on both forms and is out of scope.

   *Done when:* each of these fails at `c9dcfd290`: for a coderabbit `issue_comment` whose only finished marker is quoted in each of
   constructions A, B and C (Claim Labels) and in each of the non-fence shapes D (a blockquoted marker, an inline-code marker, a four-space
   indented marker), the lane's `review-gate --required-reviewer coderabbit` answers `required_review_missing`, driven through the lane's
   real read seam with the raw body and not through a stub that hands the check a pre-flattened string; a required reviewer whose raw read
   is incomplete or failed answers `undecidable_read`. These hold at `c9dcfd290`, as behaviour (their test inputs move from flattened to raw
   multi-line bodies): a marker on its own line after a prose line is a qualifying review; a marker inside a plain closed fence is not; a
   fence-like run in prose is not a closing fence; several comments each carrying a marker each count.

2. **The one predicate refuses the two refusal shapes the old reading refused.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - The registry refusal match is case-insensitive again, as the pre-`c9dcfd290` chokepoint and lane matched it. Decide at outline whether
     the casefold lives in the registry arm of `_is_refusal_notice` (every refusal consumer reads it) or only in the predicate, and record
     why; the default is the registry arm, because the premise of this epic's plan is one reader. Either way the tests and the two prose
     statements of case-sensitivity (`github_re_review.py` module text, the `test_comments_stage_fetch.py` docstring) say what the code does.
   - A refusal body is exempt from the refusal exclusion only when it carries a readable finished marker that NAMES a commit
     (`review_coverage_names_commit`), as the old chokepoint and lane required. A marker of kind `reviewed` that names no commit, beside a
     refusal and a non-empty `commit_id`, is not a finished review. The producer keeps a second participation gate beside the predicate
     (`github_pr.py`, `... and not review_coverage_is_finished`): decide at outline whether it moves with the predicate and record why.

   *Done when:* each of these fails at `c9dcfd290`: a CodeRabbit `review_body` with a non-empty `commit_id` whose body is a registered
   refusal phrase in a different letter case and carries no notice shape is not a finished review at the producer, the post chokepoint and
   the lane; a refusal body with a `{"kind": "reviewed"}` marker that names no commit and a non-empty `commit_id` is not a finished review
   at all three sites. These hold at `c9dcfd290`: a refusal body whose finished marker names a commit is a finished review at all three
   sites; a refusal body with a commit and no marker is not.

3. **The review-gate parser reads the CodeRabbit block "Files with no reviewable changes" as boilerplate.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `_NON_FINDING_SECTION_LABELS` (`runbook_lane.py`) gains `files with no reviewable changes`, with the observed pull request and review in
     the provenance comment the list's own rule requires. The allow-list stays CLOSED: an unlisted counted title is still refused as
     `unreadable review-body section`, because a block that cannot be shown to be boilerplate is counted so it never gives a false pass.
   - The fixture is the real block read from `cuioss/plan-marshall#1964`, a `<details>` whose `<summary>` is a `<picture>` icon wrapper
     (`file-no-changes.svg`) followed by `Files with no reviewable changes: 1`, then a `<dl><dd>` listing `* opencode.json`. The lane re-reads
     that body for the capture, so the repository holds one.

   *Done when:* each of these fails at `c9dcfd290`: a review body that carries the captured block beside a findings section reads only the
   findings, with no refusal (at `c9dcfd290` it answers `undecidable_read` with detail `unreadable review-body section: 'Files with no
   reviewable changes: 1'`). These hold at `c9dcfd290`: a counted title that is neither a findings section nor a listed label is still
   refused; the existing label tests pass.

4. **The pins cover what the review found uncovered.**
   - Skills: pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester
   - The three-site shape table gains rows for a refusal with a commit and no marker, a case-variant refusal with a commit, and a refusal
     with a commit-less finished marker plus a commit, each with one verdict across the producer, the chokepoint and the lane, and its lane
     column is driven with what production hands the lane after deliverable 1.
   - The tests that pinned the enumerative-arm direction and the refusal-plus-marker direction keep their stated purpose and are moved
     only where deliverable 2 changes the verdict.
   - The participation-site population tests name `is_finished_review` in the lane's site expectations; when the lane's call structure
     changes they are reseeded, never loosened: each still fails when a participation site is left unguarded.

   *Done when:* each of these fails at `c9dcfd290`: deleting the refusal arm from `is_finished_review` turns at least one shape-table row
   red (at `c9dcfd290` no row does, because the table's "refusal without a marker" row has an empty commit); the table's lane column is
   driven through the lane's read seam with a raw body, so a second predicate planted at the lane's site turns a row red. This holds at
   `c9dcfd290`: the three participation-site population tests fail on a planted unguarded site.

5. **The prose and the comments say what the code does.**
   - Skills: pm-documents:ref-documentation
   - Persona: documenter
   - The two docstrings that say a quote is never credited and a fence-like run is never a closer (`_github_pr.py` `strip_fenced_regions`,
     `runbook_lane.py` `_required_reviewers_without_a_review`) are rewritten or removed with their subject.
   - The old-behaviour and change-history wording in the files the PLAN-LB-147 landing lists (`bot_registry.py`, `_github_pr.py`,
     `github_re_review.py`, `workflow-integration-github/SKILL.md`, `phase-6-finalize/standards/branch-cleanup-rereview.md`, and the new tests)
     is replaced by a statement of the current behaviour. The grounding read lists the phrases in Claim Labels.
   - `workflow-integration-github/SKILL.md` on head currency names the real callers of `review_coverage_verdict` (the producer's
     merge-candidate read, the named-commit currency and the re-review await) and says that the lane's `review-gate` path and the chokepoint do
     not ask it, so a marker naming a commit outside the pull request is not checked there; `runbook-lane/SKILL.md` carries the same
     statement and the refusal-plus-marker exception in its refusal sentence.
   - `workflow-integration-github/SKILL.md` on the `undecidable` review qualifies "resolves `unmeasured`" with the flag and the finished
     review the code checks, and `branch-cleanup-rereview.md` lists the refusal-plus-finished-marker exception beside "a refusal".
   - One sentence in `runbook-lane/SKILL.md` states why the lane's direct enqueue does not take the merge mutex (this project merges through
     the platform queue, which serializes and re-tests the merge; settled by the operator on 2026-11-12). It rides here because the file is
     already edited; it is not a deliverable of its own.

   *Done when:* each of these fails at `c9dcfd290`: the documentation test pins each corrected statement in the section that states it, with a
   planted-old-sentence control that ends in an assertion that the checker fails on the planted text. These hold at `c9dcfd290`: every
   snippet the existing pins in `test_review_complete_after_handling_docs.py` name still passes (Claim Labels list them).

Split guard: five deliverables, one theme (the required-review check tells the truth). D1 and D2 are code and can ship separately; D3 is one
list entry and a fixture; D4 is tests; D5 is prose and ships last. The plan stays whole unless D1's read-form decision at outline turns out to
need a new flag, in which case the PR records the split.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- One reader per concept: the finished-review predicate stays one function, and every site that asks it asks about the same text, the
  provider's raw bodies. No site reconstructs line structure from a flattened body.
- Fail closed: an incomplete or failed read, an unreadable marker and an undecidable review state are never read as a finished review at the
  merge gate. A refusal never counts as a review unless it carries a readable finished marker that names a commit.
- The allow-list of non-finding section titles stays closed; a new title is added only from an observed capture.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so; a fixture never hands the
  lane a value its real read cannot give.
- The PR states whether an executor regeneration is owed (none if no verb or flag is added).
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: the display read flattens and the data read does not — `ci pr comments` is `cmd_pr_comments`, which returns `flatten_comment_bodies(fetch_pr_comments_data(...))`, and `flatten_comment_body` replaces tabs and newlines with a space — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `cmd_pr_comments` (L2169-2175) and `github_ops.py` (leaf, L649-672)
- OBSERVED: the post chokepoint asks the predicate about RAW bodies, through the in-process data read, and answers `None` when the read failed or `complete` is not true — read at `workflow-integration-github/scripts/github_re_review.py` § `_qualifying_review_on_record` (L1885-1930 at `c9dcfd290`)
- OBSERVED: the lane's read is the executor's `ci pr comments` invocation, so it receives the flattened bodies — read at `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` § `_read_review_surfaces` (L2619-2666)
- OBSERVED: the lane strips fenced regions from the flattened body, inserts a newline before every `<!--`, then asks the predicate — read at `runbook_lane.py` § `_required_reviewers_without_a_review` (L2698-2700)
- OBSERVED: `strip_fenced_regions` pairs fence runs by the whitespace beside them in the flattened body (an opener must be at the start or preceded by whitespace, a closer followed by whitespace or the end, same character, at least as long) — read at `_github_pr.py` § `strip_fenced_regions` (L669-717)
- OBSERVED: construction A, original lines ```` ``` ```` / ```` ``` not-closer ```` / the marker / ```` ``` ````, flattens to ```` ``` ``` not-closer M ``` ``` ```` in which the second run closes the fence and the last opens an unterminated one, so the marker survives and counts; the raw reader reads the second line as content, so the marker is inside the fence and does not count — traced by the orchestrator against the re-read function, and by the leaf against `markdown_fence.py` and `_coverage_opener_position`
- OBSERVED: construction B, original lines ``See ```code```.`` / ```` ``` ```` / the marker / ```` ``` ````, flattens so that the real opener closes the inline span, and the marker survives and counts; the raw reader reads the first line as prose (it does not start with a fence) and the last three as a closed fence — traced by the orchestrator and the leaf
- OBSERVED: construction C, a four-space-indented ```` ``` ```` (indented code, not a fence) before a real fence that quotes the marker, flattens so the indented run opens and the real opener closes, and the marker survives and counts; the raw reader treats the indented line as not a fence — traced by the orchestrator against the re-read function and by the leaf against `markdown_fence.py:27`
- HYPOTHESIS: shapes D, a blockquoted `> <!-- … -->`, an inline-code `` `<!-- … -->` `` or a four-space-indented marker, are rejected by the raw reader (`_coverage_opener_position`, L448-462) and counted by the lane, because the re-split moves the opener to the start of a line, and the parent lane did the same re-split — confirm/refute at `_github_pr.py` § `_coverage_opener_position` and `runbook_lane.py` L2699 (leaf read; not re-read; verify-at-outline)
- OBSERVED: no reconstruction from the flattened body can match the raw reader in both directions: "prose\nM" (the raw reader counts it) and "prose M" (it does not) flatten to the same string, and so do ">\nM" and "> M" — reasoned by the leaf from the two functions; the lane's own test `test_a_flattened_summary_marker_names_its_commit` needs the first to count
- OBSERVED: `ci pr comments` has no raw option or field: argparse declares `--pr-number` and `--unresolved-only`, and a TOON table cell cannot carry newlines — read at `tools-integration-ci/scripts/ci_base.py` (leaf, L1208-1211) and `ref-toon-format/scripts/toon_parser.py` (leaf, L49-71)
- OBSERVED: the registry refusal arm is a case-sensitive `marker in body`, and the pre-`c9dcfd290` chokepoint matched with `casefold`; the producer's own pre-`c9dcfd290` test was case-sensitive — read at `_github_pr.py` § `_refusal_layers` (L309), `git show 57f8e70ba:` `github_re_review.py` § `_is_refusal_body` (L1888-1890) and `github_pr.py` (leaf, L2206-2208)
- OBSERVED: CodeRabbit's registered refusal phrases are "Review limit reached", "Review rate limited", "Too many files!", "files exceed the limit of", "Already reviewed the last commit" and "No new commits to review" — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` (leaf, L91-97)
- OBSERVED: the predicate exempts a refusal when `review_coverage_is_finished` holds (marker readable, kind `reviewed`), which does not require the marker to name a commit, and the old chokepoint and lane required `review_coverage_names_commit` — read at `_github_pr.py` § `is_finished_review` (L653-654) and the parent chokepoint (L1941)
- OBSERVED: no test feeds a case-variant refusal, and the shape table has no row for a refusal with a commit-less marker — leaf read of `test/plan-marshall/workflow-integration-github/test_finished_review_shape_table.py` (L45-54) and `test_finished_review_one_reader.py`; searched under `test/`
- OBSERVED: `_NON_FINDING_SECTION_LABELS` is a closed list of seven titles matched by `startswith` on a normalised title (tags removed, lower-cased, characters outside `[a-z0-9- ()]` dropped), so an emoji-prefixed rendering of "Files with no reviewable changes (1)" would match a label of that text; an unlisted counted title is refused — read at `runbook_lane.py` L2149-2161, L2309-2346 (leaf) and L2457-2467
- OBSERVED: the block title appeared on `cuioss/plan-marshall#1964` as `Files with no reviewable changes: 1` inside a `<details>` with a `<picture>` icon wrapper, and the repository holds no capture of it — read through `ci pr comments --pr-number 1964` by the orchestrator, and searched case-insensitively under `marketplace/`, `test/`, `doc/`, `.claude/` and `.github/` by the leaf
- OBSERVED: the lane is the only Python caller of the `pr comments` command line, and no document under `marketplace/bundles/plan-marshall/skills/` describes comment-body flattening — leaf search by `grep` (the Grep tool was unavailable), coverage limited to the file types it names
- OBSERVED: the existing documentation pins that must keep passing are in `test_review_complete_after_handling_docs.py`: "whose `credited`, `stale` OR `undecidable` review settles" (about L246-251), "before every cause, window and budget arm" (L252-257), the table row (L258-263), "A bot declaring `review_complete_after_handling` is re-reviewed only when" (L52-56) and "A bot without the flag is re-reviewed when HEAD advances" (L282-287), each within a window of its section marker — leaf read
- OBSERVED: the old-behaviour wording the grounding read re-found at `c9dcfd290`: `bot_registry.py:551-552,577-578,731,752-753,879,888`; `_github_pr.py:46,735,768-769,808,876,1212-1213,1445,2181`; `github_re_review.py:88-91,146-147,240,907,1517,1522`; `workflow-integration-github/SKILL.md:415,429`; `branch-cleanup-rereview.md:58,108`; `test_finished_review_shape_table.py:7-9`; `test_finished_review_one_reader.py:106-108,146`; `test_review_complete_after_handling_re_review.py:156-160`
- OBSERVED: head currency, `review_coverage_verdict`, is asked by the producer's evidence-named read (`github_pr.py` L1641, L1647 through `named_commit_currency`, `_github_pr.py` L783) and by the re-review await (`github_re_review.py` L489), not by the lane (no `review_coverage` in `runbook-lane/scripts`) and not by the chokepoint (L1907-1909) — leaf read
- OBSERVED: no running row declares a path of this plan: PLAN-LB-146 (a build result names the tree it built) diffs against `c9dcfd290` in the build-server client, the change ledger, `manage-tasks`, `phase-6-finalize/standards/push.md` and the executor template, and PLAN-LB-136 (Antigravity rules, the runtimes, `phase-4-plan/SKILL.md`, the manifest) declares none of the surface below; no PLAN-LB-136 worktree exists yet — leaf read of `git worktree list`, the diff stat and both specs' Expected Surface
- HYPOTHESIS: the lane's process working directory equals the `project_dir` the in-process raw read needs, so `fetch_pr_comments_data` reads the right repository without a new argument — confirm/refute at `github_ops.py` § `set_default_cwd` and `run_gh` and `runbook_lane.py` § `_read_review_surfaces` (leaf: not read; verify-at-outline, D1)
- HYPOTHESIS: the producer's consumers that read `finished_review_bots[]` (`pre_merge_gate.py` and the step-done guard) tolerate a narrower list after deliverable 2 — confirm/refute at `phase-6-finalize/scripts/pre_merge_gate.py` and the guard it names (leaf: `pre_merge_gate.py` and the guard not read; verify-at-outline, D2)
- Verify-first clause: before scoping D1, drive the lane's check with raw constructions A, B, C and D and state what each returns at `c9dcfd290`, so the red runs the Done-when asks for exist; a construction that does not count at `c9dcfd290` is dropped from the clause and the PR says so. Before scoping D2, read the consumers named in the last hypothesis.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_required_reviewers_without_a_review`, `_read_review_surfaces` or the raw read beside it, `_NON_FINDING_SECTION_LABELS`, the review-gate verdict reasons (D1, D3, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — `is_finished_review`, `_refusal_layers`, `strip_fenced_regions` and its fence constant, the old-behaviour wording (D1, D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — the stripper's re-export, `_qualifying_review_on_record`, the case-sensitivity statements, the old-behaviour wording (D1, D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the participation gate beside the predicate, only if the outline decides it moves (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — the in-process raw read and its working directory, only if the lane reads it directly (D1; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — the old-behaviour wording, and the refusal-pattern reader if the casefold lives there (D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — head currency, the `undecidable` sentence, the old-behaviour wording (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the refusal sentence, the head-currency step and the one sentence on the mutex (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md` — the refusal exception and the old-behaviour wording (D5)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` — the raw-read cases, the new label, the moved flattened inputs (D1, D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_finished_review_shape_table.py` — the new rows and the lane column (D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_finished_review_one_reader.py` — the verdicts deliverable 2 moves (D2, D4)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_review_complete_after_handling_re_review.py` — the old-behaviour wording of its moved test (D5)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_fetch.py` — the case-sensitivity statement and the refusal-layer cases (D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_complete_after_handling_docs.py` — the documentation pins (D5)
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_participation_site_population_guards.py`, `test/plan-marshall/automatic-review/test_participation_site_population_records.py` and `test/plan-marshall/automatic-review/test_participation_site_population_resolution.py` — the lane's site expectations name `is_finished_review`; they move only if the lane's call structure does (D4; verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-147 (shipped, `c9dcfd290`); PLAN-LB-142 (shipped).
- Overlaps with: none. No running row declares a path of this plan (Claim Labels). PLAN-LB-146 runs on the build and freshness surface and PLAN-LB-136 on the Antigravity and manifest surface; the cross-check names the exact files.
- Adjacent to: the findings parser's flattened read (`_body_findings` and the thread-concern reader), which stays as shipped; the `pre_merge_gate.py` readers of the producer's `finished_review_bots[]`, which this plan does not edit but whose tolerance of a narrower list is a hypothesis; the PLAN-LB-142 loop-back and the step-done guard, which the PLAN-LB-147 lane did not exercise and this plan does not touch.
- The `Learnings`, `Action performed` and `Prompt for AI Agents` titles are not added: none carries a declared count, so none reaches the refusal; add a title only from an observed counted capture.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-148-required-review-check-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
