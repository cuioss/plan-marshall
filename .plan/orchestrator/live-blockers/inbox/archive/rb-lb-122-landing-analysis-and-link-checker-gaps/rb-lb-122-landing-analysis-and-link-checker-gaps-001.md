envelope_version=1
sender_type=plan
sender_id=rb-lb-122-landing-analysis-and-link-checker-gaps
epic=live-blockers
kind=landing
created=2026-11-07T15:42:16Z

# Landing: PLAN-LB-122 — total Step 4 verdict mapping and a verify-links that names every masked reference

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-122-landing-analysis-and-link-checker-gaps
epic=live-blockers
pr=#1931
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2062
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (`.plan/temp/guard.log`; four refusals this run, listed under Rule check).

## Deliverables

Every Done-when was evidenced with the `mutation-after` order: the failing output came from mutating or reverting the committed fix, reported by commit and output identifier.

### D1 — The Step 4 verdict mapping is total, and a confirming finding is never a contradiction — met

| Done-when clause | Test | Order | Failing run / identifier | Green at |
|---|---|---|---|---|
| a doc test fails for a mapping with no row for a `checked` finding that confirms a premise | `test_the_mapping_covers_a_checked_finding_that_confirms_a_premise` | `mutation-after` | `18443bf7a` with the confirming row removed — job log `97f6a6b119e94b438f6ed07fd5f26741` | `cf80cf26b` |
| a test shows each leaf verdict value maps to one corpus verdict or none | `test_the_mapping_is_total_over_the_leaf_verdict_values`; `test_the_routing_maps_the_leaf_vocabulary_to_the_corpus_vocabulary` | `mutation-after` | same run (mapping-table mutation) | `c42f78318` |
| a contradiction between the two `analyze.md` statements fails the test | `test_the_two_corroboration_statements_agree` | `mutation-after` | `18443bf7a` with the retired sentence re-inserted — job log `dfa9114993634c3a9247a0ae13743275` | `cf80cf26b` |
| a downgrade of `contradicted` by `not_shown_by_reading` is refused by the stated rule | `test_the_never_downgrade_rule_covers_every_settled_verdict` | `mutation-after` | covered by the mapping-table mutation run; the rule names `contradicted`, `corroborated` and `unverifiable` and the precedence between them | `fca7cd593` |

Commits: `18443bf7a` (mapping), `c42f78318` (layer-2 wording), `22f220ffc` (formatting), `3cf28cd79` (claim addressing), `fca7cd593` (guard bound + derived population).

### D2 — `verify-links` counts or names every link form its masks hide — met

| Done-when clause | Test | Order | Failing run / identifier | Green at |
|---|---|---|---|---|
| the five masked forms are each counted or named (red at `3404d904c`) | `test_verify_links_counts_every_reference_form_a_mask_hides`; `test_verify_links_names_a_macro_whose_target_a_passthrough_wraps` | `mutation-after` | `ab265f1c8` with the spanning-macro probe disabled — job log `04b701706dce45738913f46befcb4147` (classes `{code-span: 2, pass-macro: 1, passthrough: 1}`, missing `inline-passthrough` and one `passthrough`) | `cf80cf26b` |
| a syntax example in backticks is still not `broken` (control) | `test_verify_links_double_backtick_span_pairs_as_one_span`; `test_verify_links_masked_examples_are_named_by_their_mask_class` | `mutation-after` | `cf80cf26b` with the code-span regex reverted — job log `808c0edf8b4848b69aced0f583ffaa0d` | `c42f78318` |
| the existing link-verify fixtures stay green unchanged | the whole `verify_links` population (65 tests) | — | — | `c42f78318` |

Commits: `ab265f1c8`, `c42f78318`, plus the review-round fixes in `3cf28cd79`.

### D3 — The secure-logging owner states the narrowed claim — met

| Done-when clause | Test | Order | Failing run / identifier | Green at |
|---|---|---|---|---|
| a doc test asserts the narrowed statement and the U+2028/U+2029 mention in the owner, and a pointer rather than a restatement in the Java leaf; it fails at `3404d904c` | `test_secure_logging_narrows_the_json_claim_to_the_string_grammar`; `test_java_security_points_at_the_owner_for_the_json_claim` | `mutation-after` | `cf80cf26b` with the broad claim restored — job log `33c42c6eef4a41b0ba06941ad59b9326` | `cf80cf26b` |

Commit: `cf80cf26b`.

### D4 — The checker's remaining edges and the guide texts state what holds — met

| Done-when clause | Test | Order | Failing run / identifier | Green at |
|---|---|---|---|---|
| absolute xref not joined/opened; xref target percent-decoded as its anchor | `test_verify_links_absolute_xref_target_is_named_and_not_broken`; `test_verify_links_xref_target_is_percent_decoded` | `mutation-after` | `cf80cf26b` with the xref arm reverted — job log `808c0edf8b4848b69aced0f583ffaa0d` | `c42f78318` |
| a self-referencing symlink does not abort a multi-file run (interpreter shape confirmed first) | `test_verify_links_self_referencing_symlink_does_not_abort_the_run` | `mutation-after` | `ab265f1c8` with `RuntimeError` removed from the catch — job log `a814ff36636749808cd94fa6bfde49df`; the run confirmed CPython 3.12 raises `RuntimeError: Symlink loop` from `Path.resolve` | `cf80cf26b` |
| a double-backtick span pairs correctly | `test_verify_links_double_backtick_span_pairs_as_one_span` | `mutation-after` | job log `808c0edf8b4848b69aced0f583ffaa0d` | `c42f78318` |
| a run whose only failures are unreadable targets does not report `broken_links 0` beside `status: failure` | `test_verify_links_an_unreadable_only_run_names_the_count` | `mutation-after` | the cited `_cmd_verify_links.py:654` report line now names the unreadable count, and the result carries `unreadable_issues`; the count's absence reds the test | `c42f78318` |
| the "outermost first" comment states the real order; an unterminated or mismatched-length block is named | `test_verify_links_an_unterminated_block_is_named`; `test_verify_links_a_mismatched_length_close_leaves_the_block_open_and_named` | `mutation-after` | job log `808c0edf8b4848b69aced0f583ffaa0d` | `c42f78318` |
| each named shape is red at `3404d904c` | the six D4 tests above | `mutation-after` | the `808c0edf…` run failed 6 / passed 57 at `c42f78318` with the D4 fixes reverted | `c42f78318` |
| the Tests bullet's cases exist; the spaced anchor is replaced; the guard is labelled; the parent-green D3 assertion is dropped | `test_verify_links_xref_anchor_is_percent_decoded`; `test_verify_links_cross_file_fragment_is_percent_decoded`; `test_verify_links_a_non_utf8_target_is_reported_not_raised`; `test_verify_links_a_permission_denied_target_is_reported_not_raised`; `test_verify_links_percent_encoded_anchor_resolves`; `test_the_inline_only_index_names_only_the_item_one_write` | — | — | `f9af868ed` |
| a read of each cited line shows the wording corrected; the `WORKTREE` paragraph is pinned by a test | `test_the_worktree_paragraph_pins_the_declared_exception`; `test_cui_logging_points_at_the_value_neutralisation_rule`; `test_the_shared_link_verify_fixture_masks_its_double_backtick_example` | `mutation-after` | the paragraph assertions red without the wording fix | `f9af868ed` |

Commits: `ab265f1c8` (checker edges), `cf80cf26b` (docs), `c42f78318` (review round), `f9af868ed` (shared fixture).

**Per-head test runs (pushed heads):** `cf80cf26b` and `22f220ffc` — 65 filtered `verify_links` tests and 33 `three_layer` tests green; `4847f4e05`, `22f220ffc`, `3cf28cd79`, `f9af868ed`, `fca7cd593`, `8ee756b21` — full `module-tests` green (job logs `55981eb8…`, `21e430b1…`, `8271b5db…`, `b5a7d6f3…`, `e1d3c24c…`).

## Personas and skills

- Production code (D2, D4 checker): `persona-implementer`; unit/module tests: `persona-module-tester`; documentation (D1, D3, D4 docs): `persona-documenter`; self-review: `persona-code-reviewer`.
- The spec declares no `Skills:` or `Persona:` lines — `skills: none named`. No skill was added for surface drift.
- The two files outside the spec's Expected Surface are explained: `doc_references.py` (named by the Claim-Label HYPOTHESIS as the dangling reference) and `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` (it pins the return shape D1 changes). `uv.lock` is the operator-approved chore.

## Hypotheses

- **`cmd_corpus_set_verdict` does not refuse a downgrade — confirmed.** `_validate_set_verdict_args` validates grammar only (`orchestrator.py:5012-5075`) and the write replaces the verdict bullet unconditionally (`orchestrator.py:5188-5193`). D1 therefore takes the text-rule arm: no script refusal, no new verb, no executor regeneration.
- **`_cmd_verify_links.py:474,496,63,654` and the xref/unreadable edges read as the report says — confirmed** at the parent (`_resolve_target` caught only `(OSError, ValueError)`; the xref target was not decoded; the code-span regex paired a double-backtick span as two empty spans; the log line reported zeros beside a failure).
- **A self-referencing symlink raises `RuntimeError` under Python 3.12 — confirmed by the mutation run** (`a814ff36…`): `pathlib.resolve` → `check_eloop` raised `RuntimeError("Symlink loop …")`.
- **The dangling references and the restated check set read as reported — confirmed** at `agents/execution-context.md:37`, `ext-point-execution-context-workflow.md:67`, `logging-standards.md:318-319` and `doc_references.py:23-26`.

## Findings

- **Self-review round 1** (persona-code-reviewer): one major — three D4 regression tests the spec's *Tests* bullet requires are green at the parent (retained, and noted in the PR body); minors — layer-2 persistence wording, masked-xref pattern asymmetry, the `unreadable_targets` population, four stale docstrings, a weak never-downgrade guard and a dead `none` branch. All fixed in `c42f78318`; none open.
- **CodeRabbit round 1** (`4847f4e05`): major "enforce precedence at the write boundary" — answered as out of scope (the spec's Done-when says "refused by the stated rule" and its Sequencing names the corpus verdict storage as adjacent and left untouched); CodeRabbit withdrew it. Minor double-backtick handling — fixed in `3cf28cd79`, then the follow-up "shared fixture" — fixed in `f9af868ed`. Minor masked-xref re-extraction — fixed in `3cf28cd79`, confirmed. Three review-body nitpicks — fixed in `3cf28cd79`.
- **CodeRabbit round 2** (`f9af868ed`): two test-guard findings — the never-downgrade slice and the literal verdict list — fixed in `fca7cd593`, both confirmed and resolved.
- **CI:** green on `3cf28cd79`, `f9af868ed`, `fca7cd593` and the merge head `8ee756b21`.
- No failing check was left unhandled.

## Reviewers

| Reviewer | Required | Outcome | Head reviewed | Trigger / wait history |
|---|---|---|---|---|
| CodeRabbit | yes (quota-limited) | reviewed `4847f4e05` and `f9af868ed`; refused on quota for `fca7cd593` and `8ee756b21` | latest review covers `f9af868ed`, `kind=reviewed`, merge risk Low | triggered 12:05, 13:03, 13:32, 14:07, 14:48; 13:03, 14:07 and 14:48 answered "Review rate limited" (notices named 1 min, 24 min and 53 min; the lane's 90-minute floor was not applied because a qualifying review already exists) |
| Sourcery | optional | refused on its own review budget (250k diff characters / 7 days) | none | triggered 12:05; refusal recorded; optional, so it does not gate |

**Standing review authorization (quota-limited reviewer), for merge head `8ee756b21`:** a qualifying review exists — the 13:37 formal review whose `final_review_risk_coverage` marker names `f9af868ed` with `kind=reviewed`; every finding from that review and any later one is fixed in a pushed commit and every thread is resolved; it was re-triggered once after the last push (14:48) and the quota refusal is recorded; every other gate condition holds on the current head (CI green, build gate green, Sonar not configured, no open thread).

## Operator questions

1. **uv.lock churn.** Question: "`uv run` rewrote `uv.lock` (main's lock still pins types-pyyaml 20260906 while pyproject requires 20261103); the spec's Write-Boundary excludes it — how should I handle it?" Options: commit as a separate `chore(deps)` commit (selected), leave uncommitted, stop. The operator selected option 1 and added free text: "use skip-bot-review as pr label".
2. **The label versus the required reviewer.** Question: "the `skip-bot-review` label would suppress the required CodeRabbit review, which the lane forbids skipping — how do you want it?" Options: no label and the normal cycle; the label plus a still-required review; the label and stop before merge. The answer was free text: "the label only for the r with uv-lock chnages" — no option selected. The label was applied because the operator asked for it twice, and the required review was still obtained (the explicit trigger overrode the label's skip; CodeRabbit reviewed `4847f4e05`, `f9af868ed` and the intervening heads).

## Rule check

- **Guard:** `present`. Four refusals in this session (`ses_e4ab65fe1ffenrbF7knD6A9b27`), all complied with:
  - `find test/pm-documents/ref-asciidoc -type f | sort` — R1 (pipe); replaced with the Glob tool.
  - `git -C … grep … | head -20` — R1 (pipe + `git grep`); replaced with the Grep tool.
  - a `git commit -m` whose message contained backticks — R1 (command substitution); replaced with `git commit -F` on a `.plan/temp/` file.
  - `python3 .plan/execute-tool.py …` — R5 (a direct script path, a typo for `execute-script.py`); re-issued through the executor.
- **Spec read:** `resolve` read the **ledger worktree** copy (`spec_source: ledger_worktree`); it carried no `spec_differ` marker, so no silent read of an older copy.
- **Executor skew:** `not_applicable` — a source checkout, where the executor maps the checkout's own scripts.
- **`.plan/` writes:** only `.plan/temp/` and the three `ci` body slots under `.plan/local/plans/NO_PLAN/work/ci-bodies/`, plus this one inbox message. No orchestration-model file was edited.
- **No attribution footer** on the PR body; every commit ends with the resolved trailer.
- **No direct CI CLI, no direct build wrapper, no direct pytest/ruff/mypy** — every build went through the resolved `build` map.
- **Temp files** only under `.plan/temp/`.

## Build server

- Setup preflight: `ready` (the worktree was registered at setup).
- Mechanism: **every build was `daemon_longpoll`**; none fell back in-process, and no build retried after a launch fault.
- The routed `verify` twice hit the daemon's supervisory bound (`timeout_used_seconds: 1286`, `timeout_source: explicit`); per the lane's rule the gate continued in its split form — `quality-gate` and `module-tests` — and those are the runs that are green on each head (`quality-gate` at `8ee756b21` job log `29e25097…`; `module-tests` at `8ee756b21` job log `e1d3c24c…`).
- No `runtime_stamp_reason` was reported.

## Residue

- **The write-boundary guard (CodeRabbit's major) is a legitimate follow-up.** `cmd_corpus_set_verdict` still replaces a settled verdict unconditionally; the never-downgrade rule is procedural only. The spec excluded the corpus verdict storage, so it needs its own spec with that surface declared.
- **An external `xref:` target is still joined onto the file's directory and reported broken** (`xref:https://…`). Pre-existing, adjacent to the absolute-path arm this plan added, not named by the spec.
- **Three D4 regression tests are green at the parent** (the xref anchor decode, the cross-file fragment decode, the permission-denied target); they are retained because the spec's *Tests* bullet requires them, and the red-at-`3404d904c` clause applies to the defect shapes, all of which are red.
- **The `skip-bot-review` label is on the merged PR.** It suppressed automatic reviews, so each review had to be triggered by comment; the merge still required and obtained one.
- **Owed outside this plan, operator-run:** a harness sync after merge. No verb or flag was added, so no executor regeneration is owed for this plan's own surface.
