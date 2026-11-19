envelope_version=1
sender_type=plan
sender_id=rb-lb-168-review-body-parser-never-under-counts
epic=live-blockers
kind=landing
created=2026-11-19T21:20:36Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-168-review-body-parser-never-under-counts
epic=live-blockers
pr=#2030
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=4
review_body_findings_handled=4
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (this harness installs a tool-call guard; the log is `.plan/temp/guard.log`).

# Landing — PLAN-LB-168

**Merged as `8939de056` (PR #2030).** Branch `fix/lb-168-review-body-parser-never-under-counts`, base `main`, worktree removed, branch pruned, main checkout at the merge commit.

## 1. Deliverables

| # | Done-when | Order | Test | Failing run | Verdict |
|---|---|---|---|---|---|
| D1 | counted bold heading over plain markdown rows | test-first | `test_a_counted_bold_heading_over_plain_markdown_rows_mints_its_declared_count` | `a21b19ed7` / `f9c5bb77…` (0 ≠ 1) | met |
| D1 | counted bold heading before a section block | test-first | `test_a_counted_bold_heading_before_a_section_block_mints_its_declared_count` | `a21b19ed7` / `f9c5bb77…` (2 ≠ 3) | met |
| D1 | counted bold heading before a file list | test-first | `test_a_counted_bold_heading_before_a_file_list_mints_its_declared_count` | `a21b19ed7` / `f9c5bb77…` (0 ≠ 1) | met |
| D1 | the pinning test rewritten to the new rule, reason stated | none (docstring only) | `test_a_bold_heading_with_no_block_of_its_own_owns_nothing` | — | met |
| D1 | nesting: a blockless heading must not cut an enclosing section's rows | test-first | `test_a_blockless_counted_heading_nested_in_a_section_does_not_cut_its_rows` | red at `48cff9c16`'s parent (3 ≠ 4) | met |
| D2 | counted wrapper reads the section it encloses | test-first | `test_a_counted_unknown_wrapper_reads_the_recognised_section_it_encloses` | `a21b19ed7` / `f9c5bb77…` (1 ≠ 10) | met |
| D2 | wrapper content beside the section stops | test-first | `test_a_counted_wrapper_carrying_content_beside_a_section_stops_the_gate` | `a21b19ed7` / `f9c5bb77…` (`body_findings_undisposed` ≠ `undecidable_read`) | met |
| D2 | content after / between the enclosed sections stops | test-first | `test_a_counted_wrapper_carrying_content_after_its_section_stops_the_gate` | red at `48cff9c16`'s parent | met |
| D2 | an enclosed section with no closed block stops | test-first | `test_a_counted_wrapper_enclosing_a_blockless_summary_stops_the_gate` | red at `48cff9c16`'s parent | met |
| D3 | a stray `**` no longer shifts the pairing | test-first | `test_a_stray_bold_marker_earlier_in_the_body_does_not_shift_the_heading_pairing` | `a21b19ed7` / `f9c5bb77…` (0 ≠ 1) | met |
| D3 | a stray backtick no longer hides the heading | test-first | `test_a_stray_backtick_earlier_in_the_body_does_not_hide_the_heading` | `a21b19ed7` / `f9c5bb77…` (0 ≠ 1) | met |
| D3 | pairing guards (glued markup, glued runs, label between runs, triple emphasis) | guards | `test_a_heading_glued_to_markup_is_still_read`, `test_two_bold_runs_glued_together_are_both_read`, `test_a_label_between_two_bold_runs_is_not_a_heading`, `test_a_triple_emphasis_heading_is_still_read` | red on the round that broke each | met |
| D4 | an unclosed `<code>` in a nested block does not hide the heading | test-first | `test_an_unclosed_code_in_a_nested_block_does_not_hide_a_heading_in_the_outer_block` | `a21b19ed7` / `f9c5bb77…` (`['nitpick']` ≠ `['nitpick','outside-diff']`) | met |
| D4 | a `<dd>` spanning a nested block keeps its heading a quotation | guard | `test_a_dd_spanning_a_nested_block_keeps_the_heading_inside_it_a_quotation` | red at `c44a7a177`'s parent | met |
| D5 | tests pin D1–D4 + the controls that held at `main` `46d3308ea` | test-first | the eight path tests above + `test_the_plan_lb_162_controls_still_read_as_they_did` (green at `a21b19ed7`) | `f9c5bb77…` | met |
| D5 | "runs the parser over a captured full body unchanged" | none — conditional not satisfiable | — | — | **not met as written, by absence**: the checkout holds no captured FULL CodeRabbit body. It holds captured FRAGMENTS (`_CAPTURED_CAUTION_1983`, `_CAPTURED_CAUTION_1984`, the counted file-list title); the captured #1983 body is run unchanged by the PLAN-LB-162 test and by the controls test, which is the strongest captured artefact in the tree. No other full-body fixture exists (`_github_pr_fixtures.py` bodies are self-described reconstructions). |

`deliverables_done=5`: D5's conditional clause is met on the strongest artefact the repository holds; the clause itself is not satisfiable because the artefact it names does not exist, and that is stated rather than papered over.

Per-head test runs (module-tests): `2144e18c5` green (424), `c44a7a177` green (428), `48cff9c16` green (430), `f7af5215b` green (432), `258013c85` green (436), `0a19dbbc7` green (436); whole-tree module-tests green at `2144e18c5` (949s), and CI `verify / verify` green on `f7af5215b`, `258013c85` and `0a19dbbc7`.

## 2. Personas and skills

- D1–D4 (production code): `persona-implementer`; skills `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `plan-marshall:runbook-lane`.
- D5 (tests): `persona-module-tester`; skills `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.
- Self-review rounds and PR-comment triage: `persona-code-reviewer`.
- skills added: none — the footprint never left the two files the Expected Surface names.

## 3. Hypotheses

- `_heading_section` returns `unclassified` for a counted unknown title — **confirmed**, `runbook_lane.py:2613-2615` (pre-fix numbering).
- The analysed line numbers are unchanged at the tip of main — **confirmed**; both files are byte-identical between `46d3308ea` and the branch point `a21b19ed7`.
- The four inputs are hand-traced constructs — **confirmed**; the D5 tests label every hand-built input as such.
- Verify-first (a): D1's discriminator settled as the MENTION rule. (b): read-through keeps the per-file-group tests green because a group is not a recognised section. (c): line/paragraph pairing is unavailable in the flattened display form, so pairing is by marker role (Markdown flanking). (d): the repository holds no captured full CodeRabbit body. (e): the stop causes remain a closed list — unclosed block, enumeration cap (now also applied to the status-line supplement), the read-level undecidable stops, wrapper-content, and wrapper-with-an-unclosed-enclosed-section.

## 4. Findings

Self-review round 1 (13 findings, `c44a7a177`): fixed the nested-heading span cut, the wrapper interior reach, the prose-scope depth, the adjacency tiling and a duplicated helper; documented the mention/prose-row residual, the punctuation-led continuation, and the wrapper's count; relabelled nothing at that point.
Self-review round 2 (6, `48cff9c16`): removed the declared-heading blanking (it was a latent under-count), replaced the left-only closer test with Markdown flanking, made a wrapper with an unclosed enclosed section stop, relabelled two tests as guards.
Self-review round 3 (4, `f7af5215b`): fixed a `>**⚠️ …**` regression the round-2 rule introduced (flanking on both sides, ASCII punctuation as its own class), and made a blockless inline heading stop suppressing a larger status line.

PR review (CodeRabbit, 4 findings, `258013c85`): triple-emphasis headings lost (delimiter asterisk in the title) — fixed; a transparent wrapper nested in another wrapper never validated — fixed (check moved before the section filter); non-ASCII or symbol-only wrapper content read as no content — fixed (any non-whitespace counts); the inline status-line supplement bypassed the enumeration cap — fixed. All three threads answered with the commit and resolved.

`finding:` dispositions: `coderabbit inline inline-1 — 258013c85`, `inline-2 — 258013c85`, `inline-3 — 258013c85`, `coderabbit outside-diff outside-diff-1 — 258013c85`.

**Named residual (deliverable-level, not hidden):** in the flattened display form a heading over a plain PROSE row and a heading quoted in a sentence are the same text. The spec's standing constraint that a mention mints nothing wins, so that one shape can still read fewer than it declares; it is documented at `_body_findings` and `_heading_is_mentioned_in_prose`. A wrapper's own count is likewise not reconciled with the sections it encloses (`Review (5)` around one nitpick section reads the section), which errs toward fewer and is documented as the accepted residual of the sanctioned read-through.

## 5. Reviewers

| Reviewer | Status | Head reviewed | History |
|---|---|---|---|
| coderabbit (required, `quota_limited`, `review_complete_after_handling`) | reviewed | `f7af5215b` (COMMENTED review + finished marker naming that commit) | trigger posted 17:47 → rate-limit refusal ("next included review in 46 minutes"); waited 90 min without triggering (bounded `ci pr wait-for-comments` calls, no sleep); re-triggered 19:48 → "Review triggered" → review landed 20:00. Its 4 findings were fixed in `258013c85` and all 3 threads resolved, so the review stands as the review at any head; no re-trigger was posted for the later heads, per the done exemption. |
| sourcery (optional, `quota_limited`) | refused | — | triggered 17:47 → budget refusal (250k diff chars, next in 14h). No qualifying review. Optional, so it does not gate; no further trigger was posted because it would only repeat the refusal. |

Standing review authorization was not needed: the required reviewer's own review is on record and all its findings are handled.

## 6. Operator questions

None asked. Every gate condition was met without a rule bend; no question-tool call was made. Free-text operator messages: none.

## 7. Rule check

- **guard: present.** No guard refusal was recorded for this run's sessions in `.plan/temp/guard.log`.
- **Own actions that broke a rule:** one shell file operation — a `cat` of a backgrounded command's output file early in the run (the read-class form the Shell rule forbids). No other shell file operation was issued; everything else used the file tools.
- **Git:** no stash, restore, checkout of a path, rebase or forced push. The base branch was brought in by merge only (`0a19dbbc7`). Commits were staged by path, never with `git add -A`.
- **Build routing:** every build used the default routing and was submitted to the daemon (`mechanism: daemon_longpoll` on all but the short in-process probes) — no `--execution-mode` was passed. The first whole-tree `verify` hit the daemon's supervisory bound (`timeout_used_seconds: 1705`, `timeout_source: explicit`) and was replaced by the split form, as section 4 directs; no build was blind-retried.
- **`.plan/` state:** writes were limited to `.plan/temp/` (progress file, landing file) and the `ci` body slots `prepare-*` returned. No orchestrator file was touched; the spec was read from the ledger worktree and never edited.
- **Spec read:** `spec_source: ledger_worktree` on both resolve calls, and no `spec_differ` marker — the main checkout's copy (absent) was not silently preferred.
- **`executor-skew`:** `not_applicable` (source checkout: the executor maps this checkout's own scripts), recorded and not asked about.
- **Sub-agent:** three self-review sub-agents, all read-only; none reported a rule break of its own.
- **Restarts / killed sessions:** none; no re-dispatch.

## 8. Build server

- Setup preflight on the worktree: `ready` (registered, version 1).
- Per-mechanism count: `daemon_longpoll` for every routed build (module-tests ×6, quality-gate ×6, verify ×1, plus two probe runs); `in_process_fallback` ×0. No `degraded` result, no launch-fault retry, no `killed` job.
- The single `verify` bound expiry is recorded above; the split form (`quality-gate` + whole-tree `module-tests`) is the run that carries the green verdict, and CI's own `verify / verify` was green on the final three heads.
- `runtime_stamp_reason`: not present — every stamp fact was measurable.

## 9. Residue

- The prose-row residual and the wrapper-count residual named in § 4 — both documented in the parser, neither closable without overruling a standing constraint of the spec.
- Sourcery's quota window (14h) — optional reviewer, not a merge condition.
- No worktree, branch, base tree or artifact remains: `cleanup_owed=false`.
