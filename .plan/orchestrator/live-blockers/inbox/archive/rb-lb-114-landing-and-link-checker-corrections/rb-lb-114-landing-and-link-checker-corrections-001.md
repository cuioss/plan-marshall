envelope_version=1
sender_type=plan
sender_id=rb-lb-114-landing-and-link-checker-corrections
epic=live-blockers
kind=landing
created=2026-11-06T02:31:36Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-114-landing-and-link-checker-corrections
epic=live-blockers
pr=#1915
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
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

guard: present on this harness; two refusals, both the run's own (see Rule check).

# Landing: PLAN-LB-114 — landing template, link checker and secure-logging corrections

Merged as PR #1915 into `main`, merge commit `3404d904c8500c9ef0a6f2f301bff33a64fc3152`.

## Deliverables

All three deliverables were graded against the spec's Done-when clauses, sentence by sentence.

| D | Done-when (condensed) | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|---|
| 1 | three-value slots at layers 1 and 2 in the template | met | `test_the_layer_one_and_two_summary_slots_offer_not_shown_by_reading`, `…verdict_slots…` | test-first | `7d4182f46`, `plan-marshall/python-2026-11-05-122159.log` | `9fc13b670` |
| 1 | Step 4 names one report write and no second one | met | `test_step_four_hands_the_analysis_to_the_single_report_write` | test-first | same | `9fc13b670` |
| 1 | verdict mapping and its layer scope | met | `test_the_routing_maps_the_leaf_vocabulary_to_the_corpus_vocabulary` | test-first | same | `9fc13b670` |
| 1 | two-valued Dispatch line | met | `test_the_dispatch_line_offers_the_inline_fallback` (anchored to the line since `ebe34622d`) | test-first | same | `9fc13b670`, `ebe34622d` |
| 1 | single `conformance[M]` spelling in analyze.md, leaf doc and tests | met | `test_the_conformance_shape_is_spelled_once_across_the_contract` | test-first | same | `9fc13b670` |
| 1 | cross-repo prompt field | met | `test_the_leaf_doc_gives_a_cross_repo_prompt_field_besides_worktree` | test-first | same | `9fc13b670`, `cb70a319c`, `cf13884ee` |
| 1 | leaf's no-fetch rule | met | `test_the_leaf_doc_forbids_fetching_third_party_text` | test-first | same | `9fc13b670` |
| 2 | absolute target not `broken` and named | met | `test_verify_links_absolute_target_is_named_and_not_broken` | test-first | `7d4182f46`, `pm-documents/python-2026-11-05-122941.log` | `58f66fdad` |
| 2 | `link:#{x}[y]` is `attribute-reference` | met | `…attribute_reference_after_a_hash_is_classed` | test-first | same | `58f66fdad` |
| 2 | code span and `++…++` counted under their class | met | `…masked_examples_are_named_by_their_mask_class` | test-first | same | `58f66fdad` |
| 2 | unreadable `.adoc` fragment target yields an issue, run completes | met | `…unreadable_adoc_target_completes_the_run` (+ `…target_too_long_to_stat…`) | test-first | same | `58f66fdad`, `cb70a319c`, `cf13884ee` |
| 2 | nested longer block hides its inner `----` | met | `…nested_longer_delimiter_hides_its_inner_content` | test-first | `7d4182f46`, `pm-documents/python-2026-11-05-123024.log` | `58f66fdad` |
| 2 | `%`-encoded anchor not `broken` | met | `…percent_encoded_anchor_resolves` | test-first | `python-2026-11-05-122941.log` | `58f66fdad` |
| 2 | existing link-verify fixtures stay green unchanged | met | the 38 pre-existing link-verify tests | test-first | none (they passed before and after) | `58f66fdad` |
| 3 | escaping example | met | `test_java_security_neutralise_escapes_a_control_character_instead_of_dropping_it` | test-first | `7d4182f46`, `pm-dev-java/python-2026-11-05-131937.log` | `8fa4c9f37`, `cb70a319c` |
| 3 | narrowed JSON statement | met | `…json_statement_names_only_what_json_escapes` | test-first | same | `8fa4c9f37` |
| 3 | single code home with its pointer | met | `…java_security_skill_points_at_the_code_home_and_the_persona_standard` | test-first | same | `8fa4c9f37` |
| 3 | U+2028/U+2029 and the flag scope in `secure-logging.md` | met | `…secure_logging_owns_u2028_u2029_and_scopes_the_cntrl_note` | test-first | same | `8fa4c9f37`, `c3464f31a` |
| 3 | one owner in `logging-standards.md` | met | `…cui_logging_names_one_owner_for_the_value_neutralisation_principle` | test-first | same | `8fa4c9f37` |
| 3 | body-ordering clause in the javadoc rule | met | `…javadoc_ordering_rule_covers_the_method_body_as_well_as_the_caller` | test-first | same | `8fa4c9f37`, `cb70a319c` |
| 3 | release qualifier in `java-17-features.md` | met | `…java_17_switch_guidance_names_the_release_and_qualifies_the_enum_claim` | test-first | same | `8fa4c9f37` |
| 3 | anchored pointer assertion | met | same test as the code-home row | test-first | same | `8fa4c9f37` |

Review-driven tests added after round 1 (masking nesting, the `C++` boundary, the anchor mask, the `valid_links` filter) were shown red by mutating the committed fix back: `69aa8a586bc246af861c5ceabaae8e6c.log` (three failures) and `f669522046c3495a854ec2e2fdeb2f28.log` (one).

Per-head test runs against pushed heads: `pm-documents` 176 passed and `pm-dev-java` 84 passed and `plan-marshall` three-layer 29 passed at `e0055ff57`/`cb70a319c`; full `verify` 32,672 tests exit 0 at `8fa4c9f37`, `389e17be1` and `c009ac1b5`, and CI's own `verify / verify` green at `e0055ff57`.

## Personas and skills

- Personas applied as standards: `persona-implementer` (the checker), `persona-module-tester` (test authoring), `persona-documenter` (the D1 and D3 document corrections), `persona-code-reviewer` (all four self-review rounds and every PR-comment triage).
- Skills: the spec declared none (`skills: none named`).
- Skills added for surface drift: none. Surface additions, recorded in the PR body and here: `extension-api/standards/ext-point-execution-context-workflow.md` and `agents/execution-context.md` (the `WORKTREE`/`OTHER_REPO_PATH` contract had to be reconciled for the cross-repo field to be dispatchable), and `runbook-lane/SKILL.md` arrived only as a base-branch merge.

## Hypotheses

- `conformance[N]` in `analyze.md` vs `[M]` in the leaf doc — **confirmed** (`workflow/analyze.md:61,175`, `standards/three-layer-analysis.md:40`; tests pinned `[N]` at `test_analyze_three_layer_contract.py:257,359`).
- `WORKTREE` repo-relative leaves no field for another repo — **confirmed** (`extension-api/standards/ext-point-execution-context-workflow.md:82`, `three-layer-analysis.md:14`).
- `java-security/SKILL.md` repeats the patterns doc — **confirmed** (`SKILL.md:88-105` vs `java-security-patterns.md:47-63`; `SKILL.md:12` states no duplication).
- `logging-standards.md` names two owners — **confirmed** (`logging-standards.md:316` `pm-dev-java:java-security`, `:318` `persona-security-expert`).
- `javadoc/SKILL.md` covers only the caller — **confirmed** (`SKILL.md:154` vs `javadoc-method-documentation.md:53`).
- `test_domain_content_rules.py:267` passed on a link the skill already had — **confirmed** (`SKILL.md:78` already named `secure-logging.md`).
- `%00` raises from `Path.resolve()` — **confirmed** (`ValueError: lstat: embedded null character in path`, `python-2026-11-05-122941.log`); the case is kept.

## Findings

- Self-review round 1: 8 findings (doc falsity in the logging set, ext-point drift, pass-macro/passthrough regexes, `valid_links` arithmetic, a dead fixture, an uncommitteed ruff chunk, anchor masks, evidence hygiene). F1–F7 fixed in `c3464f31a`; F8 recorded in the PR body.
- Self-review round 2: 10 findings (four missing falsifying tests, the out-of-surface ext-point edit and its field-economy contradiction, a dangling antecedent, a third spelling of the field, an unsatisfiable inline arm, a stranded clause). All fixed in `04aa7e5fc`; the four tests were given mutation red runs.
- Self-review round 3: 4 findings (surface record, wrong cross-reference direction, a section-wide test, an overclaiming sentence). Three fixed in `ebe34622d`; the surface record carried to the PR body.
- Self-review round 4 (operator-authorized): `open: 0`.
- CodeRabbit reviewed three heads and posted 13 findings: 6 on `389e17be1` (all fixed in `cb70a319c`), 3 + 1 outside-diff on `cb70a319c` (all fixed in `cf13884ee`), 3 + 1 outside-diff on `c009ac1b5` (all fixed in `e0055ff57`). Every thread is resolved. Its post-fix remark that the workflow rule is not enforced by `cmd_corpus_set_verdict` was answered with a reason: the rule is procedural (this producer makes no downgrade call), and a script guard is a behaviour change outside this corrections-only plan, recorded as residue below.
- CI: `verify / verify` failed once at `389e17be1` with a collection error in `test_target_tree_foundational_skill_freshness.py` (shared fixture: target-tree precondition generation failed for the `claude` target). The module passed in isolation (7 tests), and the full verify passed on re-run — an xdist/ordering flake, not a change of this branch.

## Reviewers

- **coderabbit** (required, `quota_limited`): reviewed `389e17be1` (22:28:27Z), `cb70a319c` (23:39:37Z), `c009ac1b5` (01:06:38Z). Quota refusals at 15:32:28Z, 17:04:38Z, 18:45:16Z, 20:47:10Z (escalated trigger), 00:02:29Z, 01:27:32Z (after the `e0055ff57` push); each re-trigger respected the 90-minute rule, with the 90-minute waits held by `ci pr wait-for-comments`. **Standing authorization applied for the merge head `e0055ff57`**: a qualifying review exists (the `final_review_risk_coverage` marker with `kind=reviewed` naming `c009ac1b5`, read from the summary comment), every one of its findings is fixed and every thread resolved, it was re-triggered after the last push with the refusal recorded, and every other gate condition held on that head.
- **sourcery** (optional, `quota_limited`): quota-refused 15:32:24Z (six-day budget); reviewed `389e17be1`, `cb70a319c`, `c009ac1b5` and `e0055ff57` (01:54:20Z), all APPROVED.

## Operator questions

1. "D2 needs an unreadable `.adoc` target … the guard refuses shell deletion … how should I proceed?" — options: delete it and use `tmp_path` / add an `is_file()` guard to all three commands / abort. Selected: delete it, use `tmp_path`.
2. Same question again with evidence (the directory was still present; `stats_console` failed on it) — options: run the exact `rm -rf` / add the `is_file()` guard / abort. Selected: "I'll run that rm now" (the operator executed it).
3. "The self-review has reached its 3-round limit … round 4?" — options: continue with a round 4 / proceed and report `budget-exhausted`. Selected: round 4.
4. "CI operations now fail with `Not authenticated` … how should I proceed?" — options: restore `gh auth` and continue / stop with an open landing. Selected: restore and continue.
Free-text operator messages: "give me the rm command" (I supplied the exact path), "done, con tinue" (confirming the directory was removed).

## Rule check

- **Guard refusals, both the run's own**: `R1` at 12:10:07Z (`ls .plan/orchestrator 2>&1 | head -40` — shell chaining) and `R2` at 12:36:27Z (`rm -r …/edge-cases/unreadable.adoc` — shell file mutation). No workaround followed either refusal; the deletion was handed to the operator. Read from `{guard_log}` (`.plan/temp/guard.log`), the run's session `ses_e54625cc1ffe3pEcOjkai0hWm3`.
- **A build-serialization rule break by the run**: two daemon-routed builds overlapped once (pm-dev-java and plan-marshall at ~15:05Z), against the one-at-a-time rule; both were re-run serially afterwards and the repeat results are the ones reported.
- Shell file operations: one `ls` (refused, R1); no other `cat`/`ls`/`grep`/`find`/`head`/`sed` was issued. Reads and searches used the file tools.
- Spec read: `spec_source: ledger_worktree` at the first resolve (the main checkout held no copy then, so no `spec_differ` marker); the base merges later carried the spec into `main`.
- Executor skew: `not_applicable` at the start (a source checkout; the executor maps this checkout's own scripts) — answered, recorded, never asked about. Executor version moved from `0.1.2025` to `0.1.2062` through base merges.
- Build logs read: the build client's own `log_file` paths under `/home/oliver/.plan-marshall/marshalld/job-logs/` — read only to obtain the test summaries, as the client instructs.
- No restarts, no killed sub-agents; four self-review sub-agent dispatches (rounds 1–4), each with a fresh context.

## Build server

- Setup preflight: `down`, reason `unreachable` (project registered).
- Every build before ~13:12Z fell back in-process with `mechanism=in_process_fallback` and reason `unreachable`; every build from 13:12Z onward was routed (`mechanism=daemon_longpoll`). The exact per-mechanism count was not tallied; the split above is from the run's own build calls.
- One launch fault: none. No `killed` job. No `runtime_stamp_reason` was carried by either resolve.
- The daemon's fallback notice named the machine-global single-lane serialization while it was unreachable; plan-less builds ran unserialized.

## Residue

1. `cmd_corpus_set_verdict` does not itself refuse a downgrade of a corroborated verdict; the workflow rule is procedural. A value-comparison guard plus a regression test is a follow-up (CodeRabbit raised it; answered with the scope reason above).
2. `verify-links` does not examine `link:` macros inside listing/literal blocks, which can re-enable macro substitution (`[subs="+macros"]`) and render; the SKILL now tells the reader to check them by hand. A checker-side class is a follow-up.
3. The `WORKTREE`/`OTHER_REPO_PATH` paragraph in the extension-point standard is unpinned by any test; a doc-contract test for it is a follow-up.
