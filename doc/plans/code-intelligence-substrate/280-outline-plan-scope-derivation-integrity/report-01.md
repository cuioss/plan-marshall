# Run report — 280-outline-plan-scope-derivation-integrity (run 01)

**Date (UTC):** 2026-08-17    **Branch:** `claude/code-intelligence-substrate-scope-qgljp1`
**PR:** _pending_    **Outcome:** completed

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
| 2 | A named defect site did not exhibit the behaviour; the real producer had several consumers | **CONFIRMED** | The reported site was `manage-solution-outline`'s module-context degrade. The producer of the bad value is `file_ops.PlanContext`. Its `has_worktree` face has **seven** production consumers: `manage-execution-manifest._resolve_footprint`, `integrate_into_main`, `_cmd_baseline_reconcile`, `_cmd_force_push`, `git-workflow` (two sites), `_references_core.resolve_live_worktree`. |
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
| A read-only reference file must not flip a bucket | **Done.** `_plan_parsing.deliverable_write_set` names the authoritative write-set (`intent != read`). The `module_testing` check reads it. The `<!-- bucket: X -->` comment is extracted by `extract_declared_bucket`, carried on the deliverable record as `declared_bucket`, and adjudicated against the write-set in **both** directions by `_check_declared_bucket`. |
| A change type must be composed across deliverables | **Dropped — closed at HEAD.** See D0 row 5. |
| A drift check must read the analysis prose | **Done.** `_load_deliverables` now returns a `number → prose` map built from `split_deliverable_blocks`, and `_build_haystack` folds it in. |

**Scope decision inside D1, disclosed rather than absorbed.** `_check_declared_bucket` adjudicates
the **documentation axis only** — `documentation_only` versus everything else. The remaining five
buckets separate production from test from config, which is a build-system-owned judgement
(`BuildExtensionBase.classify_paths`) and not adjudicable from paths alone at this layer. Approximating
it here would install a second, weaker classifier competing with the aggregator — the defect the check
exists to catch. The documentation axis is the one the read-only-reference flip actually bites on, and
it is owner-less (`_manifest_core._is_documentation_path`), which is why it is delegated rather than
restated.

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
- Branch gate: `./pw verify` — result recorded below.

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

**Every member is covered, and the coverage is structural rather than per-file.** The great majority
reach the seam through `test/_shared/_resolve_project_dir_fixtures.py`, whose helpers now build their
return value by calling the production `derive_worktree_state`. That is the opt-out-with-a-reason
discipline inverted into something stronger: no fixture in that population can encode a state pairing
the producer cannot emit, and a future change to the state machine reaches all of them without an
edit.

**Stated exclusions** — three modules stub the seam directly rather than through the shared helper,
and each is handled individually rather than left out:

| Module | Why it bypasses the shared helper | Disposition |
|---|---|---|
| `tools-file-ops/test_plan_context_resolver.py` | It tests the resolver itself, so routing through a helper that calls the resolver's own deriver would be circular. | Rewritten: its local stub takes the state directly, and the endorsing test is replaced. |
| `manage-solution-outline/test_get_module_context.py` | It stubs one layer lower — the subprocess boundary — deliberately, to keep the real parser in play. | Its payload builder now derives the `worktree_state` line through the production function. |
| `tools-integration-ci`, `workflow-integration-github`, `workflow-integration-gitlab`, `script-shared/test_build_execute.py` | Inline `lambda _pid: (True, '/tmp/…')` stubs. | **Left as-is, deliberately.** Each supplies a non-empty path, which the state machine maps to `materialized` — the same tuple they already returned in the old shape's truthy position. They are not misleading and they are not stale; converting them would be churn without a defect. This is an exclusion with a reason, which is what D5 requires — not an unstated omission. |

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

**Rejected findings:** none. No finding surfaced in this run was dismissed.

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

Recorded below, after the build gate result.

## Reviewer participation

Derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc.
Population: `coderabbitai`, `cuioss-review-bot`, `sourcery-ai`.

_To be completed from the PR's three comment surfaces before the merge gate._

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

_To be completed as the final pre-merge commit._

## What have we learned (Step 9)

_To be completed as the final pre-merge commit._

## Residue

1. **Arm A of the split** — handed over as
   [`350-outline-derived-set-closure-integrity.md`](../350-outline-derived-set-closure-integrity.md).
2. **A `disabled` plan's footprint is derivable but reported unresolvable** — analysed and
   deliberately not fixed here (D4, F13). Carried into the successor spec with the evidence, because
   it is cross-cutting: `manage-references`, the composer, and `extension_base` share the policy and
   must move together.
3. **Claim 8 (the routing decision's pre-override input) was never sited.** Neither confirmed nor
   refuted. Carried forward, labelled as such.
4. **The five non-documentation buckets remain unadjudicated** at the outline validator. Closing that
   needs the build extensions' `classify_paths`, which is a heavier coupling than this deliverable
   warranted.
