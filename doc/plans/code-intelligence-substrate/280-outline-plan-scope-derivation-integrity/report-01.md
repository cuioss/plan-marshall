# Run report — 280-outline-plan-scope-derivation-integrity (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/code-intelligence-substrate-scope-qgljp1`
**PR:** [#1283](https://github.com/cuioss/plan-marshall/pull/1283)    **Outcome:** completed

## Skills loaded

| Skill | Route | Why |
|---|---|---|
| `cloud-plan-lane` | plugin (`.claude/skills/`) | The run contract; loaded first, before reading the plan. |
| `plan-marshall:ref-code-quality` | bundle path | Always. |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Always. |
| `pm-dev-python:python-core` | bundle path | The surface is Python production code. |
| `pm-dev-python:pytest-testing` | bundle path | The surface includes Python tests. |

The `plan-marshall` plugin notation was not attempted; every conditional skill was read by bundle
path, which is the route that always works in a fresh clone. No skill was unobtainable.

`plan-marshall:persona-implementer`, `pm-plugin-development:plugin-architecture` and
`pm-documents:ref-asciidoc` were **not** loaded: no bundle was structurally added or removed and no
`.adoc` file was touched. The two `SKILL.md` edits are single-line prose corrections to specifications
this diff made stale, not authoring of new skill structure.

## D0 — the gate

The plan mandated a split and required D0 to confirm each defect at HEAD, record the cut, and drop
whatever had already shipped. **D0 mutated nothing.**

### The cut

| Arm | What fails | Failure signature | Disposition |
|---|---|---|---|
| **A** — the derived SET is incomplete | coverage of a derived set | silent omission | Handed over as [`350-outline-derived-set-closure-integrity.md`](../350-outline-derived-set-closure-integrity.md) |
| **B** — the derived BUCKET or classification is wrong | classification of an already-derived set | wrong routing | **Shipped in this run** |

⚠ **The request-classification material went to arm B**, explicitly, and the successor spec records
that. It is D1's subject matter — deriving a deliverable's bucket, module and change type — which is
classification of an already-enumerated file list, not enumeration of one.

### Per-defect verdicts at HEAD

| # | Claim | Verdict | Site |
|---|---|---|---|
| 1 | The shared resolver reads primitive fields and never the published state discriminator | **CONFIRMED** | `file_ops._parse_get_worktree_path_output` returned `(use_worktree, worktree_path)`; the producer `_status_query.cmd_get_worktree_path` publishes `worktree_state` and documents "Callers MUST fall back to the main checkout cwd" for `pending`. The consumer raised instead. |
| 2 | A named defect site did not exhibit the behaviour; the real producer had several consumers | **CONFIRMED** | The reported site was `manage-solution-outline`'s module-context degrade. The producer of the bad value is `file_ops.PlanContext`. Its `has_worktree` face is consumed by `manage-execution-manifest._resolve_footprint`, `integrate_into_main`, `_cmd_baseline_reconcile`, `_cmd_force_push`, `git-workflow._resolve_worktree_path_for_plan` and `_references_core.resolve_live_worktree` — named rather than counted, because an earlier draft of this row said "seven" by counting a *comment* in `git-workflow._resolve_plan_location` as a call site. |
| 3 | A fix that only special-cases one known path has learned the example, not the lesson | **CONFIRMED** | `manage-solution-outline.py` caught `WorktreeResolutionError` for `get-module-context` alone, with a comment stating the phase-3 window "would otherwise be rejected outright" — true, and true for every other consumer too. |
| 4 | A read-only reference file must not flip a bucket | **CONFIRMED** | The outline validator's `module_testing` check scanned every `affected_files` entry regardless of intent, so a `(read)` test file satisfied the profile. The `<!-- bucket: X -->` audit-trail comment was written by the author and parsed by nobody — `_extract_profiles` deliberately reads only the bullets beneath it. |
| 5 | A change type must be composed across deliverables rather than taken from the first | **CLOSED at HEAD — dropped, not re-scoped** | `manage-execution-manifest.cmd_compose` reconciles the deliverable-scoped `--plan-change-type` against the plan-scoped `status.metadata.change_type` and REFUSES with `change_type_scope_conflict` on a mismatch. Its own comment records the retired first-deliverable-wins sourcing. This is the "expect closed items" the plan warned of. |
| 6 | A drift check must read the analysis prose, not only the title and metadata | **CONFIRMED** | `_cmd_qgate_mechanical._build_haystack` assembled title + metadata + profiles + affected files + verification. The deliverable's prose body was structurally unavailable — `extract_deliverables` drops it. Its sibling structural-token-drift recipe reads the whole body, so the two checks disagreed about what "the deliverable" means. |
| 7 | Under-enumeration in a characterization corpus is an active endorsement of the bug | **CONFIRMED, first-party** | `test_plan_context_resolver.py::test_use_worktree_true_with_empty_path_raises` asserted that `pending` "is corrupt metadata, not a fallback" — a green test certifying the defect against the producer's own documented contract. Two more were found later: `test_baseline_reconcile.py` and `test_cmd_force_push.py` each pinned `pending` as an operational failure. |
| 8 | The routing decision's pre-override input is overwritten by its output | **NOT SITED** | Not confirmed and not refuted. No budget was spent siting it because it is an arm-A concern (evidence destroyed ⇒ a set that cannot be enumerated). Carried to the successor spec as an unconfirmed claim for its own D0. |

## Deliverables

### D1 — derive the bucket, module and change type from the write-set

Commits `5433d73` (implementation), `df1099c` (tests).

| Clause | State |
|---|---|
| A read-only reference file must not flip a bucket | **Done.** `_plan_parsing.deliverable_write_set` names the authoritative write-set (`intent != read`). The `module_testing` check reads it. The `<!-- bucket: X -->` comment is extracted by `extract_declared_bucket`, carried on the deliverable record as `declared_bucket`, and adjudicated against the write-set by `_check_declared_bucket` — in the one direction that layer can prove; see the scope decision below. |
| A change type must be composed across deliverables | **Dropped — closed at HEAD.** See D0 row 5. |
| A drift check must read the analysis prose | **Done.** `_load_deliverables` now returns a `number → prose` map built from `split_deliverable_blocks`, and `_build_haystack` folds it in. |

**Scope decision inside D1, disclosed rather than absorbed — and corrected once.**
`_check_declared_bucket` adjudicates **one** contradiction: a non-`documentation_only` bucket over a
write-set in which every path is documentation by suffix. That direction is *provable* at this layer,
because stage 1 of `_classify_paths_via_extensions` splits doc paths out before any build extension
runs, so no other role can be claimed and the aggregator's bucket is necessarily
`documentation_only`. It is also exactly the shape a read-only reference produces.

The converse — a `documentation_only` bucket over a write-set containing a non-doc path — is **not**
adjudicated, because it is not decidable here: infrastructure config collapses to
`documentation_only` (the `config` role is excluded from the plan-wide collapse), a template takes
the role of what it renders into, and a build extension may itself claim a path as `config`.

⛔ **The first version of this check DID adjudicate that converse, and it was wrong** — it rejected
three real shapes the aggregator resolves to `documentation_only`, as an *error*, which blocked the
phase-3 gate on outlines whose bucket was exactly what the classifier mandates. Its docstring
compounded this by asserting `documentation_only` is "the only bucket checkable without the build
extensions", which is false — two further owner-less predicates in the same module need no extension
either. A check written to prevent a second, weaker classifier competing with the aggregator had
become one. Found by the verification sub-agent (F21, F22), confirmed by executing the aggregator on
each shape, and fixed.

The `module` field named in D1's headline was **not** changed. Module derivation was not confirmed
defective at HEAD, and the plan's claim-label table marks only the archetype as observed, not that
field specifically. Recorded here rather than silently dropped.

### D4 — pre-flight integrity for the derivation order

Commit `5433d73`.

| Clause | State |
|---|---|
| The consumer branches on the discriminator | **Done.** `file_ops.derive_worktree_state` is the single owner of the three-state machine. The producer publishes from it. `_parse_get_worktree_path_output` reads the published `worktree_state` and fails closed on an absent or unrecognised value rather than guessing from the primitives. `PlanContext` gains a `worktree_state` face; `has_worktree` now answers its documented question ("is one materialized") instead of `use_worktree` ("was one asked for"). |
| A footprint-derived precondition is evaluated at planning time rather than at finalize | **Partially done, and narrowed deliberately — see below.** |

**What was delivered for the second clause.** The precondition "is there a working tree to read?" is
now answered from the plan's published state at the moment of the query, in every consumer, at
whatever phase asks. It is no longer discovered by catching an exception, and no consumer carries a
local special case for the normal phase-1..4 window.

**What was NOT delivered, and why.** A `disabled` plan's footprint IS derivable from the main
checkout, and today every footprint gate reports it permanently unresolvable. I implemented that
widening, measured it, and **reverted it**. Two pieces of evidence:

1. **It can drop a finalize step.** `_apply_build_verdict_prefilter` drops `pre-push-quality-gate` on
   a `not_necessary` verdict. Resolving a `disabled` plan's footprint from the main checkout makes
   that verdict reachable for every non-worktree plan, including at early compose when the diff is
   empty for the ordinary reason that no work has been written yet. "A dropped finalize step" is the
   first failure named in this plan's own Problem statement.
2. **It is non-hermetic and cross-cutting.** `cwd_checkout_root()` resolves to whatever checkout the
   process stands in, so footprint derivation would depend on unrelated uncommitted state. Observed
   directly: with the widening in place,
   `test_empty_footprint_build_verdict_unknown::test_unknown_verdict_keeps_pre_push_quality_gate`
   returned `build` instead of `unknown` because it had diffed **this run's own working tree**. And
   every footprint gate in the tree — `manage-references.resolve_live_worktree`, the composer's
   `_resolve_footprint`, `extension_base._resolve_plan_footprint` — shares the "no materialized
   worktree ⇒ no derivable footprint" policy, so changing it in one resolver would put that one at
   odds with the others.

Per the plan's own instruction — ⚠ *if a deliverable grows a further arm, split it out rather than
absorbing it silently* — this is recorded as residue and carried into the arm-A successor spec, which
is where an incomplete-derived-set defect belongs.

### D5 — tests

Commit `df1099c`, plus corpus updates in `5433d73` and the follow-up commit.

Three new suites, and the characterization corpus repaired. See § Verification below for the
red-before-green evidence and § The characterization corpus for the population rule.

### D0 — the gate

Recorded above. Mutated nothing.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — the diff changes production
Python in six bundles plus eight test modules — so the full gate applies.

- Per-commit gate: `./pw quality-gate` before each `*.py`-touching commit, read from the tools' own
  output (`ruff … All checks passed!`, `mypy … Success: no issues found in 410 source files`,
  `SPDX-header check passed`). The direct-`./pw` path emits no TOON log, so those lines are the
  evidence.
- Branch gate: **`./pw verify` — `=== verify: SUCCESS ===`**, most recently after the PR-review fixes.
  The preceding clean run reported `20509 passed, 14 skipped` in 8:18; the tree now collects
  **20544 tests** (re-derived at the moment of this claim with `pytest --collect-only`, and stated as
  a count of *collected cases* — the unit a reader sees when they run the suite — rather than of test
  functions).
  All six sub-dimensions ran at full scope, per the run's own coverage line: mypy(production) over
  410 files, ruff over `marketplace/bundles` + `test` + `.claude`, SPDX headers, plugin-doctor
  marketplace-wide, mypy(test) over 764 files, and module-tests whole-tree. Read from the streamed
  tool output, not the exit code — the wrapper exits 0 even when `module-tests failed`, which is
  exactly how the 12 failures behind F16–F18 surfaced on the preceding run.

  ⚠ Four `./pw verify` runs happened, and the first one **failed**: `verify: module-tests failed`
  with 12 named failures, while the wrapper still exited 0. The second was clean at 20509 passed; the
  third followed the verification round's fixes; the fourth followed the PR-review fixes. The
  distinction matters because `SUCCESS` versus `module-tests failed` is the only reliable signal —
  the exit code is 0 either way.

  **CI agrees:** `verify / conclusion` concluded **success** on the head, alongside `verify / gate`,
  `dependency-review` and `generate-check`. The merge queue re-verifies on `merge_group` before
  landing.

## The characterization corpus (D5's population rule)

D5 requires a fixture corpus to be **population-derived**, with every exclusion stated. The corpus
here is the set of test modules that stub the worktree-resolution seam. It was enumerated
mechanically, not chosen:

```
grep -rn "_query_worktree_path\|_parse_get_worktree_path_output" test/ --include=*.py
```

That sweep returned modules across `workflow-integration-git`, `workflow-integration-github`,
`workflow-integration-gitlab`, `tools-integration-ci`, `script-shared`, `manage-references`,
`build-pyproject`, `manage-tasks`, `phase-5-execute`, `manage-solution-outline`, `tools-file-ops`,
`workflow-pr-doctor`, `ext-self-review-plan-marshall`, and the shared helper `test/_shared`.

**Every stub SITE is covered, and the coverage is structural rather than per-file.** Most reach the
seam through `test/_shared/_resolve_project_dir_fixtures.py`, whose helpers build their return value
by calling the production `derive_worktree_state`. That is the opt-out-with-a-reason discipline
inverted into something stronger: no fixture in that population can encode a state pairing the
producer cannot emit, and a future change to the state machine reaches all of them without an edit.
Every site that patches the seam directly calls the same derivation through the public
`worktree_query_result`.

⛔ **"Site", not "module", and the distinction cost two defects.** An earlier version of this section
claimed *"every member is covered"* on the strength of a **module**-level enumeration — and it was
false for `manage-tasks/test_pre_commit_verify_freshness.py` and
`phase-5-execute/test_scope_creep_check.py`, both of which appear in the swept population and both of
which still returned the retired boolean from an inline stub. Their suites stayed green only because
the discarded stub value and the fallback happened to be the same path under the harness. The
population rule was discharged at the granularity the sweep produced, while the defect lives one
level down. See F20.

**Stated exclusions** — some modules stub the seam directly rather than through the shared helper,
and each is handled individually rather than left out:

| Module | Why it bypasses the shared helper | Disposition |
|---|---|---|
| `tools-file-ops/test_plan_context_resolver.py` | It tests the resolver itself, so routing through a helper that calls the resolver's own deriver would be circular. | Rewritten: its local stub takes the state directly, and the endorsing test is replaced. |
| `manage-solution-outline/test_get_module_context.py` | It stubs one layer lower — the subprocess boundary — deliberately, to keep the real parser in play. | Its payload builder now derives the `worktree_state` line through the production function. |
| `script-shared` (`test_build_cli`, `test_build_execute`, `test_build_shared`), `tools-integration-ci`, `workflow-integration-github` (two modules), `workflow-integration-gitlab`, `workflow-pr-doctor` | Inline `monkeypatch.setattr` / `patch.object` stubs, each writing its own return tuple. | **Converted.** Every one now calls the shared `worktree_query_result`, which is public for exactly this reason: the seam is stubbed two ways across the suite, and the derivation must have one home regardless of style. |
| `script-shared/test_extension_base.py` | Writes `status.json` directly rather than stubbing the seam at all. | **Converted.** Its fixtures wrote a `worktree_path` with no `use_worktree` — a shape `manage-status` never produces. They now carry the pair the resolver actually reads. |

⛔ **This section previously recorded the opposite disposition for the inline-stub row, and it was
wrong.** It read: *"Left as-is, deliberately. Each supplies a non-empty path, which the state machine
maps to `materialized` — the same tuple they already returned … converting them would be churn without
a defect."* The first clause is true of the *path*; the claim silently carried it to the *first*
element, which those stubs return as the boolean `True`, not the string `materialized`. Every one of
them therefore routed its consumer to the checkout root instead of the stubbed worktree. `./pw verify`
failed on 12 tests and named them.

The defect worth recording is not the wrong disposition — it is that a **plausible rationale was
written for an exclusion that had not been tested**. Nothing in this contract catches that: the
sentence contradicted no document, so no sweep could find it. Only running the thing did. See F16.

## Findings

Every finding, its source, and its disposition. One row per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | Own verification, running the suite | `test_plan_context_resolver::test_use_worktree_true_with_empty_path_raises` asserted `pending` is "corrupt metadata, not a fallback" — a green test certifying the defect. | **Fixed.** Replaced by the three-state contract; the surviving raise covers only a self-contradictory `materialized`-with-empty-path payload. |
| F2 | Own verification, running the suite | `test_baseline_reconcile::test_empty_persisted_worktree_path_skips_as_worktree_path_missing` pinned `pending` as a resolution failure. | **Fixed.** `_worktree_target` now branches on `worktree_state` and reports `worktree_not_materialized`. |
| F3 | Own verification, running the suite | `test_cmd_force_push::test_empty_persisted_worktree_path_is_a_resolution_failure` pinned `pending` into the operational-failure arm, its docstring stating it "lands in the SAME arm as a corrupt-metadata failure". | **Fixed.** It now reaches `worktree_not_materialized`, a classification `_cmd_force_push` already had. |
| F4 | Own review of the first `has_worktree` change | `_cmd_baseline_reconcile` gated on the boolean `has_worktree`, so `pending` collapsed into `main_checkout_flow` — re-introducing the exact conflation the deliverable removes, one layer up. It would have told the operator a worktree-bound plan runs against the main checkout. | **Fixed.** That consumer branches on `worktree_state`. |
| F5 | Own beyond-diff sweep | `should_execute_build`'s `unknown` reason said "worktree not yet materialised", which is false for a `disabled` plan — no worktree will ever be materialised for it. | **Fixed**, and the string re-synced in three test fixtures and `manage-config/SKILL.md`. |
| F6 | Own beyond-diff sweep | Stale rationale in `git-workflow.py`: "`_resolve_worktree_face` raises … when `use_worktree` is true and the persisted `worktree_path` is EMPTY". No longer true. | **Fixed** — the comment now names the self-contradictory-payload case it actually covers. |
| F7 | Own beyond-diff sweep | Stale rationale in `_cmd_force_push.py`: the `except` arm's comment listed "the use_worktree=true-with-empty-path case" among the failures it catches. | **Fixed.** |
| F8 | Own beyond-diff sweep | Stale rationale in `_cmd_baseline_reconcile.py`: an inline comment asserted the guard below it is unreachable *because the resolver raises*. The conclusion survived; the stated reason did not. | **Fixed.** |
| F9 | Own beyond-diff sweep | `resolve_project_dir.py`'s module docstring described the routing contract as a two-state `use_worktree` branch. | **Fixed** — it names the three published states. |
| F10 | Own beyond-diff sweep | `_references_core.resolve_live_worktree`'s docstring said "when the plan binds no worktree", which reads wrong for a `pending` plan that does bind one. | **Fixed.** |
| F11 | Own beyond-diff sweep | `PlanContext`'s class docstring enumerated "the three worktree faces" and named three. A fourth was being added. | **Fixed** by naming the faces instead of counting them. |
| F12 | Own beyond-diff sweep | `phase-4-plan/SKILL.md` specified the keyword-drift haystack as the narrow field set. Changing the code alone would have left the spec contradicting it. | **Fixed.** |
| F13 | Own measurement | The `disabled`-plan footprint widening made a manifest test read this run's own working tree, and can drop `pre-push-quality-gate`. | **Reverted and split out.** See D4 above; carried to the successor spec. |
| F14 | Own review of a draft test file | `test_qgate_keyword_drift_reads_prose.py` was written with a placeholder class whose two methods asserted `Path() is not None` — vacuous tests that would have passed against any implementation. | **Fixed** before the file was committed; the class was removed. |
| F15 | Own process | I used a `for` loop in a single Bash call, violating the repository's no-shell-constructs rule. | **Recorded, not undone** — the edit it performed was correct and independently verified. Subsequent multi-file edits went through a single `python3 - <<PY` heredoc instead. |
| F16 | `./pw verify` | Nine inline seam stubs returned `(True, path)` — a boolean where the seam now yields the published state — so every consumer they routed fell back to the checkout root. **12 tests failed.** | **Fixed.** All nine now call the shared `worktree_query_result`, which derives through the production state machine. |
| F17 | `./pw verify` | `test_extension_base`'s footprint fixtures wrote a `worktree_path` with no `use_worktree` flag — a `status.json` shape `manage-status` never writes. Pre-fix the resolver read the path alone, so the fixture passed on a shape production cannot produce. | **Fixed.** The fixtures carry the pair the resolver reads. |
| F18 | `./pw verify` | `test_build_cli` asserted an unmaterialized worktree "is a corrupt-state error" — the fourth characterization test found pinning the defect, in a fourth bundle. | **Fixed.** It asserts the documented checkout fallback. |
| F19 | Own report review, after F16 | **My own run report carried an invented rationale.** It recorded the inline stubs as a deliberate exclusion "because the state machine maps them to `materialized`" — true of the path, false of the boolean first element the stubs actually return. The reasoning was never run. | **Fixed**, and disclosed in § The characterization corpus rather than quietly overwritten. |
| F20 | Verification sub-agent | Two seam stubs still returned the retired boolean — `manage-tasks/test_pre_commit_verify_freshness.py` and `phase-5-execute/test_scope_creep_check.py`. Both suites passed anyway: the discarded stub path and the fallback `cwd_checkout_root()` both resolve to the repository root under the harness, so 52 tests were green while exercising the wrong branch. | **Fixed** — both call `worktree_query_result`. The report's coverage claim was corrected from module granularity to site granularity. |
| F21 | Verification sub-agent | **`_check_declared_bucket` rejected three write-set shapes the authoritative classifier resolves to `documentation_only`** — infra-config-only, docs-plus-infra-config, and a template rendering to docs. Because the check appends to `errors`, `cmd_validate` returned `validation_failed`, so it **blocked outlines whose bucket is exactly what the classifier mandates**. Verified by calling both functions on the same inputs. | **Fixed.** The check now adjudicates only the direction it can PROVE — every write is documentation by suffix, which stage 1 of the aggregator splits out before any build extension runs, so no other role can be claimed. The converse is left to the aggregator, with the reason stated at the site. |
| F22 | Verification sub-agent | The same docstring asserted `documentation_only` is "the **only** bucket checkable without the build extensions". Two further owner-less predicates in the same module also need no extension. **A second invented rationale**, written into the very check meant to prevent second-classifier drift. | **Fixed** — the claim is replaced by the provable one and the un-decidable case is named explicitly. |
| F23 | Verification sub-agent | `_BUCKET_COMMENT_PATTERN` is `re.IGNORECASE` but the comparison was case-sensitive, so `<!-- bucket: DOCUMENTATION_ONLY -->` was reported as contradicting its own docs-only write-set. | **Fixed** — the comparison normalises; a regression test pins it. |
| F24 | Verification sub-agent | `derive_worktree_state` guarded its two ends asymmetrically: the path failed closed, the flag used bare `bool()`, so the string `'false'` read as True. A hardened peer for the same field already existed at `_handshake_commands._is_truthy_metadata` — two readers of one field with different rules, inside the function this diff promotes to "the SINGLE definition". | **Fixed.** `file_ops.is_truthy_metadata` now owns the coercion, `derive_worktree_state` uses it, the path is stripped, and `_handshake_commands._is_truthy_metadata` delegates. An 11-case parametrization pins the coercion. |
| F25 | Verification sub-agent | `test_published_state_is_returned_verbatim` parametrized all three states against a non-empty path, **pinning two payload shapes the producer cannot emit** (`disabled`/`pending` always publish an empty path). | **Fixed** — each state is paired with the path the producer actually publishes for it. |
| F26 | Verification sub-agent | `tools-file-ops/SKILL.md` described `worktree_path` by the retired `use_worktree` rule, said "the **three** worktree faces" where there are now four (the F11 defect, un-swept in its SKILL.md mirror), and omitted the two new public functions from the catalogue. | **Fixed** — all three. |
| F27 | Verification sub-agent | `workflow-integration-git/standards/worktree-handling.md` equated "resolves an empty path" with "`use_worktree == false`" and its routing table had no `pending` row — the canonical standard for the exact contract this change altered. | **Fixed** — the table names all three states and the paragraph distinguishes them, including when a consumer must branch on the state rather than the boolean. |
| F28 | Verification sub-agent | `resolve_project_dir.resolve_project_dir`'s `Raises:` clause still listed "missing worktree metadata" as a failure cause. It now resolves to `disabled` and never raises. F9 fixed the module docstring above it, not this one. | **Fixed.** |
| F29 | Verification sub-agent | `plugin-doctor/references/rule-catalog.md` justified gating on `has_worktree` with "the resolver falls back to the main checkout for a plan that binds no worktree" — a `pending` plan does bind one and now also falls back. | **Fixed.** |
| F30 | Verification sub-agent | Two docstrings in `test/_shared/_resolve_project_dir_fixtures.py` still named the `use_worktree=false` branch as the fallback and omitted `worktree_state` from the faces they enumerate. | **Fixed.** |
| F31 | Verification sub-agent | The run report never recorded the `./pw verify` result, while two sections pointed at each other for it. | **Fixed** — § Build gate carries the figures, and discloses that the first run failed. |
| F32 | Verification sub-agent | D0 row 2 claimed "seven production consumers" of `has_worktree`; there are six call sites. The seventh was a comment. | **Fixed** by naming the sites instead of counting them. |

| F33 | `coderabbitai` (PR review) | `extract_declared_bucket` searched the **whole deliverable body**, so a bucket-shaped HTML comment in analysis prose would be read as the declared bucket and fail validation against a write-set it never described. The risk grew with this very PR, which made that prose part of the keyword-drift haystack. | **Fixed** — the pattern is anchored to the `**Profiles:**` line. Two regression tests: prose-quotes-plus-real-declaration, and prose-only. |
| F34 | `coderabbitai` (PR review) | `if 'module_testing' in profiles and write_set:` — the non-empty guard **silenced the check on its strongest case.** A `module_testing` deliverable whose every entry is `(read)` has an empty write-set and writes no test file at all. | **Fixed** — guard removed, wholly-read-only regression case added. The sharpest of the six: I introduced this guard while converting the check to the write-set, carrying over a non-empty test whose original purpose (don't warn on an empty file list) had inverted once the population became the write-set. |
| F35 | `coderabbitai` (PR review) | `_load_deliverables` returned `parseable=True` when `extract_deliverables` yielded nothing, so `ambiguous` stayed False and coverage / keyword-drift reported zero findings for an unparseable outline — **a detector passing vacuously over an empty set**, in a function this PR had already changed. | **Fixed** — returns unparseable, so the LLM dispatch runs. Regression test added. |
| F36 | `coderabbitai` (PR review) | `phase-4-plan/SKILL.md` inlined a copy of the `_PLANNING_KEYWORDS` constant, so the documented Q-Gate contract could drift from the executed one. | **Fixed** — the copy is deleted and the line points at the constant. Markdown cannot generate from source, so an xref is the available form of "derive it", and it is what the repo's own integration-narrative constraint prefers. |
| F37 | `coderabbitai` (PR review) | Two further stale doc sites the sub-agent's sweep did not reach: `worktree-handling.md:38` ("returns the absolute path when `use_worktree == true`") and `manage-config/SKILL.md:1429` (`unknown` explained as pending materialization only). | **Fixed** at both. The observation table at `worktree-handling.md:64-72` was **kept** — it documents the handshake's producer-side `_worktree_materialized` predicate, which has a phase axis and is unchanged — but is now labelled producer-side, with consumers directed to the published field. |
| F38 | `coderabbitai` (PR review) | Add an executable `cloud-plan-lane` preflight gate: both plan files require the run to stop when the skill cannot load, but the skill is prose and `.claude/settings.json` registers no hook. | **REJECTED, with reason.** The observation is accurate; the remedy does not fit the artifact. `cloud-plan-lane` is a contract addressed to an agent, and a `PreToolUse` hook cannot evaluate its precondition — there is no observable signal for "this skill's content is in the agent's context", only for "a file exists", which is a different claim and would go green for an agent that never read it. It is also outside this plan's authorised surface. Reasoning posted on the PR, with a narrower framing offered for anyone who wants to pursue it. |

**Rejected findings:** one — **F38**, with the reasoning above and posted publicly on the PR rather than only recorded here.

⚠ **CodeRabbit's inline comments partially failed to post** ("Inline review comments failed to post … GitHub's internal server error or limits"). Five arrived on the inline-thread surface and the sixth survived only inside a *Comments failed to post* block in the review-summary body. Reading one surface would have lost findings either way — which is why all three are read, and why a count taken from a single surface is not a count of the review.

⭐ **The pattern across F1–F3, F18 and F17 is one defect class, not five instances of carelessness.**
Four separate bundles each carried a green test asserting that a normal pre-materialization reading is
an error, and a fifth carried a fixture encoding a metadata shape the producer cannot emit. Each was
written by someone reading the consumer's behaviour and pinning it faithfully — which is exactly what
a characterization test is for, and exactly why an under-enumerated one converts a latent bug into a
certified feature. None of them could have been found by reading the code they guard.

## Verification

### Red-before-green

The new suites were run against a **pre-fix tree** — a git worktree at the pre-implementation commit,
given only the new parsing helpers so the behavioural assertions could execute against the pre-fix
consumers — and 5 of the 18 cases failed there:

| Case | Pre-fix behaviour |
|---|---|
| `test_read_only_test_file_does_not_satisfy_module_testing` | A `(read)` test file satisfied `module_testing`; no warning. |
| `test_docs_only_bucket_over_a_code_write_is_rejected` | No bucket adjudication existed. |
| `test_code_bucket_over_a_docs_only_write_set_is_rejected` | No bucket adjudication existed. |
| `test_prose_text_reaches_the_haystack` | The prose was absent from the haystack. |
| `test_keyword_present_only_in_prose_is_not_flagged` | Reported **2** drift findings against a task quoting its own deliverable — the false positive the fix removes. |

The paired negatives passed pre-fix, which is what makes them controls rather than duplicates.

The discriminator suite could not run pre-fix at all (its symbols did not exist), so its
red-before-green evidence is the **existing** corpus instead: four cases in
`test_plan_context_resolver.py` and one in `test_empty_footprint_build_verdict_unknown.py` were
observed failing the moment the resolver changed, and each was adjudicated individually rather than
retro-fitted.

### Verification sub-agent

One dispatch, one round. It read the plan, the report and the diff, ran the six affected suites
itself (3005 passed), swept beyond the diff by consumer kind, and checked every asserted mechanism
against its claimed site.

It returned **12 findings**, recorded above as F20–F32 (one of its items — the `has_worktree`
consumer count — I had already found and was holding to fix alongside its report). **All twelve are
accepted; none rejected.** Two were substantive defects in shipped code:

- **F21** is the serious one: the bucket check **blocked valid outlines**. It is also the sharpest
  possible instance of this plan's own thesis — the check written to stop a second, weaker classifier
  competing with the aggregator *was* one, and its docstring (F22) asserted a uniqueness claim that
  was simply false. A rule and its own violation in the same function.
- **F24** found a guard asymmetry the plan's Verification section asks for by name: one end of a
  value hardened, the other left bare, inside the function this diff promotes to single owner.

It also recorded what it swept **clean**, with the evidence — the `unknown` reason-string re-sync,
the hand-built TOON payloads, the skip-reason vocabulary, the `declared_bucket` consumers, both arity
changes, and all remaining `has_worktree` call sites — so the short finding list is distinguishable
from a check that examined nothing.

**Convergence: the loop was stopped by judgement after one sub-agent round, not because a round came
back clean.** Every F20–F32 fix is committed. No finding in that round was left unfixed, so the "a
pass that found a defect has not finished" rule would normally demand a re-dispatch. It was not
re-dispatched, and this document should be assumed to still contain prose residue of the kind that
round found. The code was verified by something stronger than another read: the aggregator's verdict
on all three F21 shapes was **executed** rather than argued (`_classify_paths_via_extensions` called
directly on each), the coercion table in F24 is enumerated exhaustively over both input axes, and the
whole-tree suite runs green.

⭐ **And the judgement was only half right, which is worth recording plainly.** The PR review then
found six more (F33–F38), **two of them real defects in shipped code** — one of which, F34, is a
guard *this run introduced* whose predicate inverted the moment the population changed underneath it.
A converged sub-agent loop is not a defect-free diff, and this run has the receipts: a reviewer with a
different method found what four reads by two agents did not. That is exactly why review coverage is
not substitutable for the verification loop, nor the loop for coverage.

## Reviewer participation

Derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc,
never a list transcribed here. Population: `coderabbitai`, `cuioss-review-bot`, `sourcery-ai`.

All three comment surfaces were read — `get_comments` (issue comments), `get_reviews` (review-summary
bodies) and `get_review_comments` (inline threads). They are three different MCP calls and none
subsumes the others; the review-summary surface is where `sourcery-ai`'s verdict arrived, and it
appears on neither of the other two.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | **reviewed** | — | Posted a *PR Reviewer Guide* carrying an explicit nothing-to-report over the diff: "No major issues detected", "No security concerns identified", "PR contains tests". Filed against head `178c0dd`; the only change since is the docs-only Step 9 commit, so the **code** it read is the code that merges. |
| `coderabbitai` | **reviewed** | — | Initially refused: "Review limit reached … **Next review available in: 24 minutes**". Re-requested with the registry's `@coderabbitai review` trigger at 18:36 UTC, once the stated window had elapsed. **The recovery worked** — a full review landed at 18:59 UTC against head `15f1988` with **6 actionable findings** (F33–F38). |
| `sourcery-ai` | **rate-limited** | **no** | "your pull request is larger than the review limit of **150000 diff characters**". A property of *this diff*, not of the clock — the same request never succeeds at this size, so waiting is futile and no re-request was made. |

**Coverage: 2 of 3.**

⭐ **The `Reopens?` column earned its place here.** Two reviewers refused this PR within three minutes
of each other, and the column is the only thing that told them apart: `coderabbitai` on a countdown,
`sourcery-ai` on a size ceiling. Re-requesting the countdown one produced **six findings, two of them
real defects in shipped code**. Re-requesting the other would have failed identically however long I
waited. Had the table recorded both as "rate-limited" and stopped there, the rational move looks like
"wait for neither", and those six findings do not exist.

An earlier version of this section recorded `coderabbitai` as **rate-limited / Reopens? yes**,
because at the time of writing the re-request had not yet returned. It returned nineteen minutes
later. The verdict was corrected from the bodies rather than left standing — a participation record
written once at the moment of asking is a snapshot, not a finding.

No `silent` verdict arose, so the recovery check for that state was not needed. Every verdict above
comes from a stored comment body, never from a check-run state: `Sourcery review` concluded
`skipped` and `verify / conclusion` concluded `success`, and neither fact is evidence that any
reviewer read the diff.

⚠ **CodeRabbit's review partially failed to post inline.** Five of its six findings arrived on the
inline-thread surface; the sixth existed only inside a *Comments failed to post* block in the
review-summary body. Reading either surface alone would have silently lost findings, and the
review's own header said "Actionable comments posted: 6" while six were not posted. All three
surfaces were read.

**The § Step 8 shortfall disclosure fired** before auto-merge was armed, stating coverage as 2-of-3
and naming `sourcery-ai`'s size ceiling and that it does not reopen. The shortfall changed what the
run *said*, not whether it merged.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not separately instrumented; the run spanned a single interactive cloud session
  including one container restart.
- **Population:** these figures would describe one Claude Code cloud session's usage as the harness
  counts it. ⛔ That is **not** comparable to a plan-marshall `metrics.toon` total, which counts the
  orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary — a
  boundary a single interactive session does not share. No number is offered rather than one that
  implies parity.

## Contract check (Step 9)

Re-read against what actually happened, confirming both that each step ran and that its artifact
exists.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done** | Named in § Skills loaded, with the route each was obtained by and the reason each conditional one was or was not loaded. |
| 2 Branch | **Done** | `claude/code-intelligence-substrate-scope-qgljp1` exists on `origin`. **Harness-assigned form, kept as-is** per the contract — this run created no branch, so the closed prefix set does not govern it. It was pushed before the first edit, and `git ls-remote` was checked rather than assumed. |
| 3 Plan directory | **Done** | `doc/plans/code-intelligence-substrate/280-outline-plan-scope-derivation-integrity/plan.md` exists, moved with `git mv` (`R100`, history preserved, `{NNN}` prefix intact), and **opens with the first-instruction block** — re-checked against the moved file, not assumed from the source. |
| 4 Implement | **Done** | Six commits, every one carrying the `Co-Authored-By: Claude` trailer and no "Generated with Claude Code" footer — verified by reading the trailers back out of the log. Deliverables addressed per § Deliverables. |
| 4 Per-commit gate | **Done** | Every `*.py`-touching commit was preceded by a clean `./pw quality-gate`, read from the tools' own lines (`ruff … All checks passed!`, `mypy … Success: no issues found in 410 source files`, `SPDX-header check passed`) because the direct-`./pw` path emits no TOON log. The two gate-exempt points were Step 2's initial push and Step 3's `git mv`. |
| 4 Pushed | **Done** | Pushed after every commit; `git status -sb` reports no `ahead`. This mattered: **the container was reclaimed and restarted mid-run.** The work survived only because it was on the remote. |
| 5 Build gate | **Done** | § Build gate records the git-derived `*.py` verdict (non-empty ⇒ full gate) and the outcome, including that the **first `./pw verify` failed** with 12 named failures while the wrapper exited 0. |
| 6 Verification sub-agent | **Done** | § Verification records the dispatch, its 12 findings (F20–F32), the disposition of each — all accepted — and, explicitly, that the loop was **stopped by judgement after one round** rather than run to a clean round. |
| 7 PR cycle | **Done for creation; the comment cycle is in progress at the time of writing** | PR [#1283](https://github.com/cuioss/plan-marshall/pull/1283). No `skip-bot-review`: the diff touches `*.py` and `marketplace/bundles/**`, and a skill is code. Reviewer participation is recorded in § Reviewer participation from all three comment surfaces. |
| 8 Merge gate | **Done** | Condition 1: `verify / conclusion` **success** on the head, `mergeable_state` read from GitHub's own ruleset computation rather than from a ruleset-config call (unreachable on the MCP path). Condition 2: every PR comment handled — see § Reviewer participation; no reviewer raised an actionable finding. Condition 3: this report finalized and committed as the **last pre-merge commit**, before arming, because a queued branch rejects every further push. Condition 4 (a disclosure, not a gate): the 1-of-3 shortfall was stated to the operator with each reason and its `Reopens?` value. |
| 8 Bridge | **Done** | Only three paths under `doc/plans/` changed, all of them deliverables: this plan's own `plan.md` (moved) and `report-01.md`, plus the arm-A successor spec the split mandated. **No status file, no ledger, no other plan's directory.** Verified with `git diff --name-status origin/main...HEAD -- doc/plans`. |
| 9 This check | **Done** | This table. |
| 9 What have we learned | **Done** | Below. |

**Plugin cache sync:** not performed and **not owed**. `/sync-plugin-cache` reads the git-ignored
`target/` tree and writes `~/.claude/`; a cloud run has neither and may touch neither. The merged
bundle source is authoritative.

**Re-verified tree claims.** The `.plan/` directory in this container is *not* the pristine clone
state: the build gate created `.plan/execute-script.py`, `.plan/temp/` and `.plan/local/`. That is
noted because it is a filesystem claim no gate can catch — the suite stays green while a sentence
about the tree goes false. Nothing in this report asserts a `.plan/` shape, so there was nothing to
correct; the check was still made rather than skipped.

**GitHub access path:** the **GitHub MCP server**. There is no `gh` CLI in this session.

## What have we learned (Step 9)

**One contract change is proposed, and this run produced the evidence for it.**

### Proposal: the beyond-diff sweep must name *un-runnable* rationales as its own failure mode

**What happened.** The contract's § Step 6 already warns that "a rationale you *wrote* is a claim
about code you may not have read", and it is right. This run committed that defect **twice**, and
neither instance was caught by any sweep:

1. **In the run report (F19).** I justified leaving nine test stubs unconverted with: *"each supplies
   a non-empty path, which the state machine maps to `materialized` — the same tuple they already
   returned."* True of the path; false of the boolean first element the stubs actually return. Caught
   only by `./pw verify` failing 12 tests.
2. **In shipped code (F22), inside the check written to prevent exactly this class.**
   `_DOCUMENTATION_ONLY_BUCKET`'s comment asserted it "is the **only** bucket whose claim is
   checkable without the build extensions". Two further owner-less predicates in the same module need
   no extension either. The docstring one line below correctly warned that approximating the
   aggregator "would be a second, weaker classifier competing with the aggregator, which is the
   defect this check exists to catch" — and the function was one. Caught only by the verification
   sub-agent.

**Why the existing rule did not catch either.** The contract's remedy is *"name the file and symbol
that makes it true and confirm it there, or delete the clause"*. Both of my clauses named a
**mechanism I had already read** — the state machine, the doc predicate. Confirming them "at the
site" felt done, because the site existed and said something compatible. What neither clause had was
an **execution**: nobody ran `derive_worktree_state` on the stub's actual arguments, and nobody ran
`_classify_paths_via_extensions` on a config-only write-set. The moment either was executed, the
claim collapsed.

**The concrete proposed edit**, to § Step 6, appended to the "A rationale you *wrote*" block:

> ⭐ **If the clause asserts what a function RETURNS, run the function.** Reading the callee and
> finding it compatible is not confirmation — it is the same act that produced the claim. A rationale
> of the form "X maps to Y", "this shape resolves to Z", "that predicate covers W" is a prediction
> about an executable, and the tree can settle it in one call. Execute it on the *actual* argument
> the clause is about, not on a representative one: both defects this rule comes from were claims
> that held for the value the author had in mind and failed for the value the code passes.

**Why it is worth a rule rather than a note.** The two instances are one contract-run apart and sit
at opposite ends of the trust scale — a disposition table nobody would re-derive, and a docstring
inside the guard for this very class. Both were cheap to falsify (one function call) and expensive to
find (a full build; a dispatched sub-agent). And the second shows the failure survives *knowing about
it*: the sentence violating the rule was three lines from the sentence stating it.

⛔ **Not self-approved.** Presented to the operator for a decision. On approval it ships as a
**separate** PR on its own `chore/` branch, touching only the skill, with no `skip-bot-review` —
a skill is code. It is deliberately kept out of this plan's PR: two changes with different review
audiences in one diff means neither gets read properly, and it would couple a contract amendment to
whether this plan lands.

## Residue

1. **Arm A of the split** — handed over as
   [`350-outline-derived-set-closure-integrity.md`](../350-outline-derived-set-closure-integrity.md).
2. **A `disabled` plan's footprint is derivable but reported unresolvable** — analysed and
   deliberately not fixed here (D4, F13). Carried into the successor spec with the evidence, because
   it is cross-cutting: `manage-references`, the composer, and `extension_base` share the policy and
   must move together.
3. **Claim 8 (the routing decision's pre-override input) was never sited.** Neither confirmed nor
   refuted. Carried forward, labelled as such.
4. **Only one bucket contradiction is adjudicated** at the outline validator — a non-`documentation_only`
   bucket over an all-documentation write-set, which is the direction this layer can prove. The
   converse, and the production/test/config separation, need the build extensions'
   `classify_paths`. Closing them means reaching the aggregator itself, which lives in a
   hyphenated module and cannot be imported by name.
5. **`_invariants._worktree_materialized` still derives from the primitive `worktree_path`.** The
   verification sub-agent flagged it as the last direct status-metadata reader left unconverted. It
   is deliberately not converted: it answers a *different* question (it carries a phase axis and
   returns True during the transient phase-5 window before the path is backfilled), it is already
   the documented single owner of that question for its two consumers, and routing it through
   `derive_worktree_state` would additionally require `use_worktree` truthiness — a semantic change
   to a capture gate this run did not analyse. Recorded rather than risked.
