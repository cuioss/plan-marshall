envelope_version=1
sender_type=plan
sender_id=rb-lb-156-maven-root-aggregator-test-artifact-ladder
epic=live-blockers
kind=landing
created=2026-11-16T16:04:58Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-156-maven-root-aggregator-test-artifact-ladder
epic=live-blockers
pr=#1998
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2135
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=1
review_body_findings_handled=1
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (the OpenCode pre-tool hook was installed for this project; one refusal recorded, § "Rule check").

# Landing — PLAN-LB-156: the Maven root aggregator's `module-tests` canonical satisfies a member's sibling test artifact

Merged as #1998, merge commit `740fe2fdcafacd5936ac58445f43bbdf9654aa80` (queue merge, base `main`, no base movement at enqueue).

## 1. Deliverables

Spec read from the shared ledger worktree (`.plan/orchestrator/live-blockers/plans/PLAN-LB-156-maven-root-aggregator-test-artifact-ladder.md`), `spec_source: ledger_worktree`, no `spec_differ` marker — the main checkout holds no copy of this spec.

**D1 — `_add_reactor_test_canonicals` emits `package` / `package -DskipTests` when a reactor member consumes a reactor test artifact, `test` / `test-compile` otherwise, reusing the ladder's detection. Met.**

| Done-when clause | Verdict | Evidence |
|---|---|---|
| `package` / `package -DskipTests` when a member consumes | met | `test_discover_reactor_root_switches_to_package_for_a_classifier_consumer`, `..._for_a_test_jar_consumer`, `test_discover_reactor_aggregator_takes_the_package_ladder_when_a_member_consumes` |
| keeps `test` / `test-compile` otherwise | met | `test_discover_reactor_root_keeps_the_test_ladder_without_a_consuming_member` (control) + the pre-existing `test_discover_reactor_aggregator_carries_the_whole_reactor_test_canonicals` unchanged and green |
| reuses the same detection, so the two cannot disagree | met | `_reactor_consumes_test_artifact` reads `metadata.reactor_test_artifacts`, the field `_build_module` derives from the single `_reactor_test_artifacts` powers the per-module ladder from; the classifier test also pins the member's own `package -pl consumer -am`, so agreement is asserted, not implied |
| order | `mutation-after` | failing run at `7507f90c1` with the switch reverted to the base behaviour: `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-11-16-113429.log` — 4 failed / 28952 passed, the four failures being the new package-row tests. Green at the same head's tree in job `e35ad39aef094d9ab9ab7733b7edd373` (28956 tests) |

Commit `c2175e458` (script + `SKILL.md` + `standards/maven-impl.md`), doc follow-ups `bd8962d6d`, `2c12cd2b0`, `f5531c6fa`.

**D2 — tests cover the five reactor shapes; the `test-jar` question is settled. Met.**

| Case | Verdict | Test |
|---|---|---|
| no consuming member → still `test` | met | `test_discover_reactor_root_keeps_the_test_ladder_without_a_consuming_member` |
| one member consuming a classified sibling artifact → `package` | met | `test_discover_reactor_root_switches_to_package_for_a_classifier_consumer` |
| one consuming a `test-jar`-type dependency | met | `test_discover_reactor_root_switches_to_package_for_a_test_jar_consumer` |
| nested aggregator unchanged | met | `test_discover_nested_aggregator_keeps_no_canonical_beside_a_consuming_member` |
| single-module root unchanged | met | `test_discover_single_module_root_keeps_the_test_ladder_with_a_classifier_dependency` |
| order | `mutation-after` | same run and log identifier as D1: the four failures are these tests |

Commit `7507f90c1` (six new tests plus the fixture-root test; 257 added lines, nothing removed or relaxed).

**Settled `test-jar` question.** § "Test ladder for reactor test artifacts" already carries the measurement (Maven 3.9.16, `standards/maven-impl.md`): `<type>test-jar</type>` resolves at `test-compile` through the sibling's `target/test-classes`; only a custom classifier falls back to `target/classes` and fails. So the `test-jar` form does **not** need `package` on its own. The root still switches on it because D1 requires the ladder's own detection, which includes that form deliberately (a false positive costs one `package` phase, a false negative is a broken build). Both the test docstring and the standard state that reasoning.

**Per-head test runs** (project publishes `verify` = compile + lint + test):

| head | run | result |
|---|---|---|
| `bd8962d6d` | `module-tests` job `389fc051ad9d4094a7b4ce28b538b6a8` | success, 28956 tests (798s) |
| `bd8962d6d` | `verify` job `6a86ffd415cb428d9f3c488a430ce596` | success, compile+lint+test, 28956 tests |
| `2c12cd2b0` | `verify` job `c1d6adf9c58043c0987e3ba082a8d8c8` | success, 28956 tests |
| `f5531c6fa` (merge head) | `verify` job `3ba5d1179ce04095b9926215b42de25e` | success, compile+lint+test, 28956 tests |

`7507f90c1`: the `module-tests` job submitted for that head (`d039b9f4b9b347c58099fcd4b616ce7f`) came back green, but it was already queued when the round-1 doc commit started editing the worktree, so it is **not** reported as that head's evidence; the same tree content was green in `e35ad39a` before the push, and every later head was re-run.

## 2. Personas and skills

| Step | Persona |
|---|---|
| D1 (production code) | `persona-implementer` |
| D2 (unit tests) | `persona-module-tester` |
| self-review rounds 1–2 | `persona-code-reviewer` |
| PR-comment triage | `persona-code-reviewer` |

Skills per deliverable: `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `pm-plugin-development:plugin-architecture` — declared by the spec for both deliverables and loaded as standards before the work. No skill was added for surface drift: the two extra files touched (`skills/build-maven/SKILL.md`, `skills/build-maven/standards/maven-impl.md`) belong to the same build-maven module the Expected Surface already names, and both state the contract D1 changes — leaving them stale would have been a doc defect the self-review would have raised.

## 3. Hypotheses

| Claim | Verdict |
|---|---|
| Root `pom` aggregator gets `test` / `test-compile` with no test-artifact check | **confirmed** — `_maven_cmd_discover.py:454-482` at the base head |
| Per-module ladder uses `package` when `has_tests and consumes_reactor_test_artifact and not is_root_module` | **confirmed** — `_maven_cmd_discover.py:1254-1259` at the base head |
| `_reactor_test_artifacts` is applied per module only; the root is not checked | **confirmed** — the only call site was `_build_module` (`:575`) |
| HYPOTHESIS: a `<type>test-jar</type>` dependency resolves at the `test` phase via `target/test-classes`, and only the classifier form needs `package` | **confirmed as Maven behaviour** by the measured record the codebase already carries (`standards/maven-impl.md:95-96`, Maven 3.9.16). It does not change the outcome: the shared detection includes the form by design, and D1 forbids the root and the member diverging. Nothing in the repo was run against a real consumer (Standing Constraint) |

## 4. Findings

| Finding | Disposition |
|---|---|
| self-review round 1, F1 (must-fix): the new prose claimed a `test-jar` artifact is "attached only from `package` on", which the same standard measures as false | fixed — `bd8962d6d` scopes the causal claim to the classifier form, states the `test-jar` inclusion as the deliberate safe-side choice, and adds the `pom`-member case and the row's cost |
| round 1, N1 (pom-packaging member over-grants one `package` phase) | fixed as documentation (`maven-impl.md:76`) rather than a code change — the over-grant is the safe direction and the ladder's rule is deliberately about the POM's declared dependencies |
| round 1, N2 (root row had no cost statement) | fixed in `bd8962d6d` |
| round 1, N3 (non-sequitur in the helper docstring) | fixed in `bd8962d6d` |
| round 2 (CodeRabbit, PR inline `coderabbit inline inline-1`, Major): the `package` row bypasses the empty-reactor zero-test guard; carry the `module-tests` intent into the executor | answered and tracked — verified in `_maven_execute.py` (a `package` run with no summary and no fresh report keeps its green); behaviour unchanged here because the fix alters the guard's contract for every `package` canonical including the shipped per-module ladder the spec says must stay untouched. The two further claims it raised in its reply (the `_parse_module_entries` docstring, and `verify` as a backstop) were both correct and are fixed in `f5531c6fa`; the follow-up is filed as **issue #2000**. Disposition: `coderabbit inline inline-1 — f5531c6fa` |
| CodeRabbit re-review of `f5531c6fa` | no new inline findings |
| Sourcery | refused on quota (250k diff characters / 7 days) — optional reviewer, recorded, not a gate |

## 5. Reviewers

| Reviewer | Required | Outcome | Head | History |
|---|---|---|---|---|
| coderabbit | yes | reviewed (marker `kind=reviewed`, `coveredCommitId=bd8962d6d`), 1 finding, handled in `f5531c6fa` | reviewed `bd8962d6d`; re-reviewed the changed files at `f5531c6fa`; merge head `f5531c6fa` | triggered once at 13:38 (`@coderabbitai review`); `review_complete_after_handling` per the resolve row, so no re-trigger was owed for later heads; `review-gate` answered `merge_allowed: true`, `all_handled` |
| sourcery | no | refused on quota | — | triggered once at 13:38 (`@sourcery-ai review`); refusal recorded with its reset window; optional, no merge obligation |

Standing review authorization was not needed: `review-gate` reported `all_handled` on the merge head with the required reviewer's qualifying review on record.

## 6. Operator questions

None asked. No free-text operator messages were received; the run proceeded under the standing merge authorization.

## 7. Rule check

- **Guard**: `guard: present`. `{guard_log}` (`.plan/temp/guard.log`) carries **one** refusal attributable to this run — 2026-11-16T10:54:46Z, `tool=shell`, `rule=R1`, session `ses_e1c01b84cffel8WhSLPBkEtEpp`, call `call_00_RnUfDsGV0Rdj9M3sw9dB1885`, command `ls … | sort … | tail …`. That was mine: a shell file listing with pipes while looking for the spec, refused; replaced with the `glob`/`read` tools and `resolve`. Every other line in that log for 2026-11-16 belongs to another session tree (10:54:24 same-second peer and the 11:14–11:15 `lb-155` session), not to this run.
- **Counts taken from the run's own actions** (not only the log): 13 routed builds (all `daemon_longpoll`, none `in_process`), 1 shell-file-operation attempt (the one refusal above), 0 operator messages, 0 model switches.
- **My own errors, recorded rather than hidden**: `glob` cannot see gitignored paths, so the ledger-worktree spec looked absent until `resolve` named it at the same path; one mistyped executor notation (`plan-marshall:tests:noop`, unknown notation, exit 1, no side effect); one `ci pr resolve-thread` call with `--plan-id` after the verb (argparse rejection, re-issued with the flag before the verb). None was a rule breach; none changed state.
- **Spec read**: `spec_source: ledger_worktree`, `spec_differ` absent (the main checkout holds no copy).
- **`executor-skew`**: `not_applicable` — a source checkout whose lane text is the text this run executed (executor `0.1.2135`); answered, recorded, not asked about.
- No sub-agent rule break was reported beyond the ones above; the two review rounds used file tools and the three read-only git commands they were allowed.

## 8. Build server

- Setup preflight: `ready` (project registered, version 1) on the worktree.
- **13 builds, every one routed**: `mechanism=daemon_longpoll` ×13, `in_process_fallback` ×0, no `degraded` result, no launch fault, no retry for one, no `killed` job.
- **One bound expiry**: job `1488a381cc5a437d90e3233d6f1c32d9` (module-tests at `bd8962d6d`) hit the daemon's learned supervisory bound of 775 s and came back `timeout`, `timeout_source: learned` — not a red build. The split form does not shorten a single-part gate here, so the run was re-issued with the resolved budget (`--timeout 1275`) and passed in 798 s (job `389fc051ad9d4094a7b4ce28b538b6a8`); the next builds took the default routing again.
- Two genuinely red builds are in the record and are mine, not the server's: the first `module-tests` (two of my new assertions assumed a member keeps a test ladder without test sources) and the first `quality-gate` (ruff `format --check` rewrote the file in place, so the next run was clean).
- `runtime_stamp_reason` was not returned by `resolve`.

## 9. Residue

- **Issue #2000** — "build-maven: hold a package-phase module-tests run to the zero-test guard". The `package`-phase `module-tests` canonical (root row and the per-module ladder) is not held to "something executed"; an `activeByDefault` profile Maven switches off at run time can therefore let that canonical report green with nothing run. Documented as a limit in `standards/maven-impl.md` and the `_parse_module_entries` docstring; the code change is out of this spec's scope.
- CodeRabbit's non-blocking nits left unfixed: the cost paragraph repeats the member section's list instead of cross-referencing it, and "every whole-tree run" would read better as "every whole-tree `module-tests` / `test-compile` run".
- The "Test ladder for reactor test artifacts" section's lead sentence ("a classified or `test-jar` artifact is attached from `package` on") is qualified two lines later by the measurement; the subsection is now more precise than its own lead. Pre-existing, not introduced here.
- `_maven_cmd_discover.py`'s cross-reference near the ladder still cites line numbers of the pre-change file where a docstring cites them; no citation was broken by this change (none named a moved line).
