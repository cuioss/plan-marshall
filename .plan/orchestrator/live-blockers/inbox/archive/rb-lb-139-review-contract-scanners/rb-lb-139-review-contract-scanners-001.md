envelope_version=1
sender_type=plan
sender_id=rb-lb-139-review-contract-scanners
epic=live-blockers
kind=landing
created=2026-11-11T18:13:45Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-139-review-contract-scanners
epic=live-blockers
pr=#1962
merge_state=merged
cleanup_owed=false
deliverables_total=1
deliverables_done=1
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=4
review_body_findings_handled=4
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## Deliverables

**D1 — the lead-in is the preceding paragraph only, and the quoted-placeholder patterns read the `=` form.**

| Done-when clause | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| a citation two paragraphs above the first `bash` block fails the "names the rule" check | met | `test_the_lead_in_is_the_immediately_preceding_paragraph_only` | test-first | `280e6c404`, job `22fbdd597a6b44b7a54f1dea4b15529f`, `test_code_review_contract.py:514` | `e65e96ca7` |
| `--message="{x}"` is flagged by the double-quote pattern | met | `test_the_double_quote_pattern_reads_the_equals_form` | test-first (base run job `c48966dc638e427da0948fb4744a35bd`, then-combined node, failing at the double-quote assertion) + independent mutation-after (job `fc85b9fb89dd400087a07e81939ee6e1`, `:464`) | `280e6c404` | `e65e96ca7`, split in `d3ee523ff` |
| `--message='{x}'` is flagged by the single-quote pattern | met | `test_the_single_quote_pattern_reads_the_equals_form` | mutation-after (the base run stopped at the double-quote assertion before this node; the split test observed failing at `:469` with the fix's pattern lines reverted) | mutation run of `e65e96ca7`'s fix, job `fc85b9fb89dd400087a07e81939ee6e1` | `d3ee523ff` |
| a citation in the immediately preceding paragraph passes (holds at `9cd644892`) | met | `test_the_lead_in_carries_a_citation_from_the_immediately_preceding_paragraph` | none (a must-keep-holding clause; no failing output exists by design) | green at `280e6c404` and `9d48fc10b` | `e65e96ca7` |
| the space-separated forms are still flagged (hold at `9cd644892`) | met | `test_the_quoted_placeholder_patterns_keep_the_space_separated_form` | none (must-keep-holding control) | green at `280e6c404` and `9d48fc10b` | `e65e96ca7` |

The Done-when's order is **test-first**: the failing runs were taken at base commit `280e6c404` with the new tests present and the scanner unfixed. `git diff 9cd644892..280e6c404` over the scanner and both contract test modules is empty, so the code under test is byte-identical at the spec's grounding commit and the recorded run. The split of the `=`-form test is the only part observed after the fix, and it is reported as mutation-after rather than folded into the test-first claim.

Three further tests were added in `9d48fc10b` for the boundary cases the review surfaced (`test_a_heading_without_blank_line_boundaries_ends_the_lead_in`, `test_an_empty_heading_ends_the_lead_in`, `test_a_block_clears_the_paragraph_it_interrupts`); their order is `none` (they pin behaviour introduced by review fixes, not a spec clause).

**Per-head test runs:** `module-tests` whole tree at `d3ee523ff` (33,467 tests, exit 0) and at `9d48fc10b` (33,470 tests, exit 0); the scoped `plan-marshall` module run at `d3ee523ff`, and the `phase-6-finalize` contract runs (348, then 349, then a re-run after the three review-fix tests) at their heads.

## Personas and skills

- `persona-implementer` — the scanner change.
- `persona-module-tester` — the new and rewritten tests.
- `persona-code-reviewer` — both self-review rounds and the PR-comment triage.
- Per deliverable: `skills: none named (the spec declares no domain skills)`. No skill was added for surface drift — the change stayed inside the two files the spec's Expected Surface marks OBSERVED.

## Hypotheses

- OBSERVED: `bash_blocks_with_lead_in` built the lead-in from every non-blank line since the previous block — **confirmed** (`_review_contract_scanners.py:48-74` before the change; the first block accumulated the whole document).
- OBSERVED: the two quoted-placeholder patterns used `\s+` only while `FREE_TEXT_ARGUMENT_RE` used `(?:\s+|=)` — **confirmed** (`_review_contract_scanners.py:27,28` vs `:30`).
- OBSERVED: the scanner is used by both contract test modules — **confirmed** (`test_code_review_contract.py:47`, `test_functional_review_contract.py`).
- HYPOTHESIS: the stricter scanner finds a defect in `code-review.md` or `functional-review.md` — **refuted**. After the change both contract modules pass on the real documents; every governed template's citation sits in its immediately preceding paragraph or shares the lead-in of a blank-line-separated run. No document was edited. Refutation does not mean the documents carry no quoting defect: a pre-existing inline `--criterion "{…}" --decision "{…}"` template at `functional-review.md:90` is invisible to the scanner (it scans fenced `bash` blocks and those flags are not in `FREE_TEXT_FLAGS`) — recorded as residue, not a defect the change found.

## Findings

- Self-review round 1: control decoupled from its assertion (fixed `d3ee523ff`); the single-quote half not independently observed (fixed by splitting the test and recording a mutation-after run); "a heading" docstring imprecise (`HEADING_RE` is ATX-only; fixed `d3ee523ff`, later extended to empty headings); whole-tree collection error environmental (resolved, the full run was green on re-run); functional-review Expected-Surface prediction (stated in the PR body); pre-existing `functional-review.md:90` template (residue, out of surface).
- Self-review round 2: verified all round-1 fixes; the only open item was a reporting obligation (one `order` per Done-when, annotated above). No code defect.
- CodeRabbit, 4 findings: inline `inline-1` (fence grammar: `~~~`/four-backtick fences and a nested fence line) — not changed, answered with a stated reason (pre-existing grammar shared with `unhalted_advisory_templates`, no such fence in either guarded document, out of this plan's surface), thread replied and resolved; inline `inline-2` (empty ATX heading) — fixed `9d48fc10b`, replied and resolved; inline `inline-3` (paragraph not cleared when a block starts) — fixed `9d48fc10b`, replied and resolved; `nitpick-1` (heading fixture with no blank-line boundary) — fixed `9d48fc10b`.
- Sourcery: no findings (see Reviewers).

## Reviewers

| Reviewer | Kind | Result | Head | History |
|---|---|---|---|---|
| coderabbit | required | reviewed, then findings handled | d3ee523ff (qualifying: `final_review_risk_coverage` marker, `kind=reviewed`, sourceCommitId = coveredCommitId = d3ee523ff) | triggered once at `15:20Z`; 4 findings raised at `15:27Z`; all fixed or answered by `9d48fc10b`; `review_complete_after_handling`, so no re-trigger on the later head |
| sourcery | optional | approved | 9d48fc10b | first trigger refused on quota ("another review in 8 hours 35 minutes") at `15:21Z`; it reviewed the later head and approved at `17:11:55Z`; optional, non-gating |

**Standing review authorization:** applied to coderabbit (quota-limited and `review_complete_after_handling`). Its one qualifying review covers `d3ee523ff`; every finding from it is fixed or answered; every thread is resolved; the remaining gate conditions hold on the merge head `9d48fc10b`.

## Operator questions

none asked. No free-text operator messages were received.

## Rule check

- Guard: present. The guard log `.plan/temp/guard.log` holds no line for this run's session tree — its entries belong to earlier sessions. The run issued no shell file operation (reads and searches went through the file tools), no `sleep`, no direct build wrapper, no CI CLI call and no inline Python. Every build went through the resolved `build` canonical.
- `executor-skew`: `not_applicable` — a source checkout, where the executor maps this checkout's own scripts; recorded, never asked about.
- Spec read: `spec_source = ledger_worktree`; `spec_differ` was not reported, so the two copies do not disagree.
- Reruns and restarts: none. Two self-review sub-agent dispatches, both completed; no killed sub-agent.
- One build command was refused by the CLI surface (`--log-file` unknown on `parse`, `--body-file` unknown on `pr reply`, `--body-file` on `thread-reply` before the body slot existed) and each was reissued in the documented shape; no source was changed to silence one.

## Build server

Setup preflight: `ready` (project enrolled, daemon version 1). Every build ran with the default routing and resolved `daemon_longpoll`; `in_process_fallback: 0`.

- Builds: 21 dispatches — 3 failing diagnostic runs (2 test-first, 1 mutation), 8 green scoped test runs, 3 whole-tree runs (2 green, 1 environmental collection error that did not recur), 5 `quality-gate` dispatches (one self-fixing its own formatting and re-run), 1 `verify` (bound expiry) and 1 aborted first targeted run.
- Fallbacks: none. One bound expiry: the routed `verify` at `d3ee523ff` returned `timeout` with `timeout_used_seconds 1242`, `timeout_source explicit`; the split form (`quality-gate`, then `module-tests`) was run instead and both were green.
- Killed jobs: none.
- `runtime_stamp_reason`: not present — every stamp fact was measurable.

## Residue

- `functional-review.md:90` carries an inline `--criterion "{…}" --decision "{…}"` template that the scanner cannot see (fenced-block scan; those flags are not in `FREE_TEXT_FLAGS`). Pre-existing, outside this plan's declared surface.
- `ANY_FENCE_RE` still accepts only backtick fences of exactly three and treats a ```` ```bash ```` line inside a block as a closing fence. Pre-existing grammar shared with `unhalted_advisory_templates`; no guarded document uses another fence form.
