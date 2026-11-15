envelope_version=1
sender_type=plan
sender_id=rb-lb-138-orchestrator-staging-and-landing-read-hygiene
epic=live-blockers
kind=landing
created=2026-11-10T23:58:51Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-138-orchestrator-staging-and-landing-read-hygiene
epic=live-blockers
pr=#1957
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=6
review_body_findings_handled=6
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (opencode pre-tool-use guard installed for this project)

# PLAN-LB-138 landing — orchestrator staging and landing read hygiene

Merged as PR #1957 (merge commit `27f4e4b96d367d03809869ed8ed6820d642066a2`); the shared ledger worktree
carrying the epic was landed separately (#1958) before the final merge, and `main` fast-forwards to
the merge commit.

## 1. Deliverables

All three deliverables are fully met. `order` is the evidence order the lane defines; the failing run
names the commit and the daemon job whose log carries the failure.

### D1 — a spaced `landing-facts` fence is read

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| `parse_landing_facts` returns the facts dict for a body opening ```` ``` landing-facts ```` | met | test-first | `test_landing_completeness.py::TestSpacedFenceInfoString` (space, tab, complete-block) | `7762f1f45`, job `1b793b701b5b44b1875904447a4595ae` — 3 failures (lines 1693/1700/1705) |
| a doc test asserts `emit-landing.md` carries the exact opening line | met | mutation-after | `TestEmitLandingStatesTheExactOpeningLine` | mutated at `1958423f1`, job `2e3d74370b47402186bc2011d18de118` — literal line removed |
| preserved: `json` / `landing-factsX` not read | met | none | `test_another_info_string_is_still_not_read` | — |
| preserved: an indented fence not read | met | none | `test_an_indented_fence_is_still_not_read` | — |

The reuse question D1 asks is answered in the code: `markdown_fence.fence_marker` is **not** reused,
because it admits up to three spaces of indentation while a landing block must start at column zero.

### D2 — the Done-when / Expected Surface rules, and the dropped bare filename

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| a template test and a decompose test assert the three rules | met | mutation-after | `test_plan_spec_template_contract.py::TestDoneWhenAuthoringRules` | mutated at `fb789b0ce`, job `410702d7f0d9463393ddb7acbfb5f409` — 3 failures |
| the bullet `` `marketplace/x/a.py` and `b.py` `` yields `b.py` in `unresolved` | met | mutation-after | `test_epic_spec_parser.py::test_bare_filename_after_a_rooted_entry_is_reported_unresolved` | mutated at `fb789b0ce`, job `0266229130264890979378ae5a7f993b` (`assert () == ('b.py',)`) |
| preserved: `pyproject.toml` and `test_*.py` still resolve | met | none | `test_a_root_level_file_name_and_a_sibling_glob_still_resolve` | — |
| preserved: `monkeypatch.delitem` stays excluded | met | none | `test_a_dotted_symbol_is_not_read_as_a_bare_filename` | — |

**Outline decision on the lint sub-verb (D2 permits dropping it): it ships.** The size answer is the
live corpus run — 141 specs, 126 carrying a Done-when, **1** finding — so the check earns its keep
without over-firing. Two review rounds then narrowed it: the four-space-indented-block gap is still
open (section 9).

### D3 — the declaration is authored, filled and gated

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| a template test asserts `Skills:` and `Persona:` inside `## Deliverables` | met | mutation-after | `test_the_deliverables_section_requires_the_skills_and_persona_lines` | mutated at `1d25e458d`, job `e370a4475733482984ed65813010d8de` (file:136) |
| the new verb exists | met | mutation-after | `TestCorpusSpecSkills` (module-level handler lookup) | mutated at `1d25e458d`, job `4893cd381ba345d3917327a2ff49e6a6` — `AttributeError: no attribute 'cmd_corpus_spec_skills'` |
| a Python spec yields this repository's Python domain skills | met | none | `test_a_python_spec_yields_the_python_domain_skills` — live `python` domain → `pm-dev-python:python-core`, `plan-marshall:ref-code-quality` | — |
| a Maven spec touching a Java module yields the Java domain skills | met, fixture-configured | none | `test_a_java_path_yields_the_java_domain_skills_when_the_project_configures_one` + the live second rung `test_a_path_no_file_glob_places_falls_back_to_the_modules_domain` | — |
| an unmapped path yields `unmapped` | met | none | `test_an_unmapped_path_is_reported_never_guessed` | — |
| a `next` fixture naming `plan-marshall:does-not-exist` is refused | met | none | `test_a_declared_skill_that_does_not_exist_refuses_the_emission` + `TestNextConsumesTheDeclarationGate` | — |
| preserved: a spec with no `Skills:` line resolves as `none named` in the lane | met | none | `test_runbook_lane.py:1349` (unchanged) | — |

**Two disclosed limitations.** This repository holds no Maven module and configures no `java` domain,
so D3's Java arm is supplied through the same seam the production read uses; and `next` is a workflow
step, not a script verb, so its refusal is the `emit_allowed`/`missing_skills` verdict the step
consumes — proven by test, not by a script exit code.

Per-head test runs (`module-tests plan-marshall`, full bundle) on every pushed head: `1958423f1`,
`f3f802b53`, `1d25e458d`, `0211f8401`, `59dca42c1`, `a15b16f80`, `1c9f9f645`, `765171a11`, `dd2dc7c38`,
`51133025d` — all green.

## 2. Personas and skills

- D1: `persona-implementer` (production parsing code) with `persona-module-tester` for its tests.
- D2: `persona-implementer` for the parser change, `persona-documenter` for the template and workflow
  docs, `persona-module-tester` for the tests.
- D3: `persona-implementer` for the lifted reader and the verb, `persona-documenter` for the template
  and workflow docs, `persona-module-tester` for the tests.
- Self-review rounds and every PR-comment triage: `persona-code-reviewer`.
- `skills: none named` — the spec declares no `Skills:`/`Persona:` lines (it predates the rule it
  introduces), and `runbook_lane resolve` reports `skills_note: none named`.

## 3. Hypotheses

- `script-shared`'s `markdown_fence.fence_marker` can serve `parse_landing_facts` — **refuted as a
  drop-in**: `markdown_fence.py:26-28` admits up to three spaces of indentation, while a landing
  block must start at column zero. Reuse declined; the regex stays local with the reason in its
  comment.
- The architecture data plus `marshal.json` `skill_domains` map a repo-relative path to a module and
  its domain skills through `architecture which-module` — **confirmed and refined**: `which-module`
  maps the path; the persisted module record's `skills_by_profile` is not trustworthy (this
  repository's own `pm-dev-python` record carries another domain's skills), so the verb places the
  path in a configured domain by its file type (falling back to the module's applicable domains) and
  reads `skill_domains.{domain}` through `manage-config skill-domains get`, applying the project's
  `excluded_skills` veto.
- Verify-first clause (D3): the lifted reader lives at `script-shared/scripts/spec_skills.py`, and the
  skill source is the project configuration's domain profiles — recorded here and in the PR.

## 4. Findings

Self-review (3 rounds, 31 findings): every blocking/major defect fixed — the doc/code contradiction on
the skill source, the `excluded_skills` veto bypass, the lint flagging its own correct two-arm shape,
failed reads published as "no module owns the path", and the fence/quote handling. Review rounds 2 and
3 also corrected `Skills: none` conflation and the declaration-gate placement.

PR review (coderabbit, required): 4 inline findings, 1 nitpick, 1 additional — all handled, all
threads resolved. Each disposition is recorded in the progress file as `finding: coderabbit …`.
Sourcery (optional) refused on its own review budget: `refused` — optional, so it does not gate.

## 5. Reviewers

| Reviewer | Required? | Result | Head reviewed | Trigger / wait |
|---|---|---|---|---|
| coderabbit | required, quota-limited | reviewed `1c9f9f645`, then `dd2dc7c38`; the final head `51133025d` was rate-limited (`NEUTRAL skipping`) | `dd2dc7c38` (qualifying review, `coveredCommitId` = head) | triggered on PR open, after each push, and once after the last push (refusal recorded); no 90-minute wait was needed because a qualifying review already existed |
| sourcery | optional | refused (own review budget) | none | triggered on PR open; refusal recorded |

Standing authorization applied: a qualifying review exists on a PR head, every finding from every
review is handled, the reviewer was re-triggered after the last push with the refusal recorded, and
every other gate condition holds on `51133025d`.

## 6. Operator questions

- "Self-review is at the lane's 3-round limit … how should I proceed?" — options: `Proceed to the PR`,
  `Run a 4th review round`. Selected: **Proceed to the PR**.
- No free-text operator messages were received.

## 7. Rule check

- `guard: present` on the opencode harness; no guard refusal was logged for this run's sessions.
- Shell file operations: none — files were read and edited with the file tools; git work through
  `git -C …` only. Builds ran through the resolved build commands; all script calls through the
  executor.
- Routed builds: all builds were submitted with the default routing (`daemon_longpoll`); one job hit
  the daemon's 1800s supervisory bound and was re-run with a raised `--timeout`, not re-submitted at
  the same bound; no launch fault, no `killed` job, no `degraded` fallback.
- Spec read: `spec_source: ledger_worktree` and no `spec_differ` marker on both resolves (setup and
  landing).
- `executor-skew`: `not_applicable` — the lane text is a source checkout whose executor maps its own
  scripts; answered, recorded, never asked about.
- Model: `deepseek-v4.1-flash/high` throughout; no switch.
- Restarts: one server restart mid-run (before the D3 verification run); the lane text was re-read,
  the progress file was resumed at the first step not recorded done, and no completed step was redone.

## 8. Build server

- Setup preflight: `ready` (the worktree is enrolled in the build daemon).
- Builds by mechanism: **`daemon_longpoll`** for every gate and test run; `in_process_fallback` count
  is 0.
- Fallbacks: one entry — `module-tests` hit the daemon's supervisory bound (`timeout_used_seconds:
  1800`, `timeout_source: daemon_default`), which is a bound expiry rather than a red build; it was
  re-run with `--timeout 2800` and finished green. No launch-fault retry.
- `runtime_stamp_reason`: absent — every runtime fact was read.

## 9. Residue

Open and recorded at the self-review round limit (`self-review: budget-exhausted`):

- The Done-when lint does not mask four-space indented code blocks (a fenced block is masked).
- `_BARE_FILE_SUFFIXES` is a closed suffix vocabulary: a bare filename whose suffix is not listed is
  still dropped in silence. The template states the limitation; the authoring rule is the full path.
- Two test-only wrappers remain in `runbook_lane.py` (`_skill_probe_paths`, `_skill_exists`).
- Field-naming preferences: rule-1 rows quote a whole clause in `clause`; the verb's per-deliverable
  `skills` is the spec-wide suggestion while the shared reader's is the declared list.
- A failed `suggest-domains` read still collapses to "no configured domain matches the path" (the
  `which-module` failure is published).
- D3's Maven/Java arm is fixture-configured, as stated in section 1.

Sourcery's review refusal (own budget, next window in about a day) is recorded and does not gate.
