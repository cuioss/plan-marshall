# Gaps — 050-post-run-band-contract-and-ordering-residue

Plan 050 landed all five deliverables, and the parts that shipped as code (the derived edge gate, the
five-tier footprint resolver, the `capture-footprint` side effect, the merge-commit fallback, the recall
consumer) are correct, non-vacuously tested, and honestly documented. What remains falls into three
clusters. **First**, the footprint the plan learned how to capture is still not reaching three of its
consumers: the mis-prune aspect's documented invocation passes a `--diff-file` that no step in the
repository produces (and which now hard-errors), the manifest cross-check was never migrated to the
shared resolver at all, and the archived-plan auditor plus the lessons-housekeeping step still read the
retired `references.modified_files` key. **Second**, two documentation claims the plan itself authored are
false against the tree — one naming a consumer that does not consume, one resting on the retired key.
**Third**, D3's entire shipped change is a prose workflow step that no test pins; D1's "published
cardinality" lives only as report prose that has already drifted (13/24 → 14/25); and D1's coverage
canary — the guard that was supposed to force a re-measurement the moment a consumer-side marker
appeared — did not fire when exactly that happened, because it watches `reads` and is blind to the
`destroys` half that was actually declared. Ten gaps, one per instance.

## G1 — Stop passing a phantom `--diff-file` to the routing-decisions aspect

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:275` (aspect 13
  invocation); raise site `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_footprint_resolver.py:60-111`
  (`resolve_diff_file_path`; the operative relative-path raise is `:107-111`); consumer branch
  `…/scripts/check-routing-decisions.py:750-767`
- **Evidence:** SKILL.md:275 reads
  `run --plan-id {plan_id} --mode {live|archived} --diff-file work/footprint.txt > work/fragment-routing-decisions.toon`.
  A full-repo search for `footprint.txt` (excluding `.git`, `__pycache__`, `doc/plans`) returns 14 hits,
  every one inside `plan-retrospective`'s own docs, scripts and tests — **no step writes the file**.
  `resolve_diff_file_path` raises `ValueError: Diff file does not exist: work/footprint.txt — a relative
  --diff-file is resolved against the plan directory first and the cwd second; tried: …`, and `safe_main`
  (`tools-file-ops/scripts/file_ops.py:1688-1698`) converts that into `status: error / internal_error`,
  exit 1. The recovery branch at `check-routing-decisions.py:758` (`supplied_footprint is None`) is
  therefore never taken. At plan 050's landing the same missing file returned `[]` and fell through to
  the resolver — confirmed at the source: `git show 0e7f644^:…/check-routing-decisions.py` shows
  `load_diff_files` returning `[]` for a non-existent path, and `git show 0e7f644:…` shows `cmd_run`
  branching on `if footprint:` (truthiness), so the empty list fell through. Commit `eb0124c` (#1288)
  introduced both the raise and the `is not None` branch that no longer absorbs it.
- **Confirmed by execution, not by reading.** Building a plan directory with the test module's own
  `_build_plan` helper, writing `references.realized_footprint`, and calling `cmd_run` twice:
  with `--diff-file work/footprint.txt` (the documented form) it raises
  `ValueError: Diff file does not exist: work/footprint.txt — … tried: {plan_dir}/work/footprint.txt,
  {cwd}/work/footprint.txt`; with `--diff-file` omitted, the same plan returns
  `status: success, footprint_source: resolved`. The recovery D4 built works; the documented command is
  what prevents it running.
- **Why it matters:** D4's stated outcome — *"one footprint resolution, two consumers … recover
  together"* — does not happen. The mis-prune half errors out on every run that follows the documented
  command, so the `realized_footprint` capture plan 050 built is consumed by exactly one consumer, and the
  aspect that re-evaluates prune predicates produces an error fragment instead of a verdict.
- **Action:** Drop `--diff-file work/footprint.txt` from the aspect-13 command at SKILL.md:275 (and the
  matching prose at `:271` and `:495`) so the resolver recovery runs, **or** add a producer step that
  writes `work/footprint.txt` from `manage-references compute-footprint` before the aspect runs. Prefer
  the first: the shared resolver already answers the same question and the capture is the primary tier.
- **Done when:** Running the documented aspect-13 command against a plan directory with no
  `work/footprint.txt` returns `status: success` with `footprint_source` ∈ {`resolved`, `unresolved`}, and
  an integration test asserts that (currently no test exercises the SKILL.md invocation form).
- **Effort:** S
- **Risk if fixed:** A live plan that genuinely relied on a saved end-of-execute diff would switch to the
  live-worktree tier; both name the same set, so the risk is limited to plans whose worktree diff and saved
  diff disagree.

## G2 — Migrate `check-manifest-consistency` onto the shared footprint resolver

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py:166-222`
  (`load_diff_files`), invocation at `…/plan-retrospective/SKILL.md:262-263`
- **Evidence:** `load_diff_files` re-derives `git diff {base_ref}...HEAD --name-only` in the process cwd
  and never imports `resolve_footprint` (only `resolve_diff_file_path` is imported, at `:42`). The
  documented aspect-12 command passes neither `--diff-file` nor `--base-ref`, so `base_ref` is falsy →
  `return [], 'unknown', False` (`:207-208`) → `_withhold_on_absent_evidence` (`:581-605`) downgrades
  every diff-fed check **that would otherwise report a clean `pass`** to `indeterminate`. A `fail` and a
  `skip` are deliberately left untouched (`:589-590`), so the effect is "no diff-fed rule can be
  substantiated as passing", not "every rule reads `indeterminate`".
- **Why it matters:** The manifest cross-check is the third consumer of the realized footprint and the one
  the retrospective forwards `affected_files_exact_match` warnings to
  (`check-artifact-consistency.py:857-877`). Post-merge it is permanently blind, so the aspect it defers to
  cannot answer either. The capture plan 050 shipped would resolve it.
- **Action:** Have `check-manifest-consistency.cmd_run` fall back to
  `_footprint_resolver.resolve_footprint(plan_dir, live_plan_id)` when neither `--diff-file` nor
  `--base-ref` yields a diff, setting `evidence_available=True` only on a resolved footprint and keeping
  the `indeterminate` withholding for the still-unresolvable case.
- **Done when:** With `references.realized_footprint` present and no `--diff-file`/`--base-ref`,
  `check-manifest-consistency run` reports its diff-fed rules as `pass`/`fail` rather than
  `indeterminate`, and a test pins the unresolvable case still yielding `indeterminate`.
- **Effort:** M
- **Risk if fixed:** Rules that have been silently `indeterminate` post-merge will start emitting real
  verdicts, which may surface a backlog of manifest-drift findings on the next few runs.

## G3 — Correct the false consumer claim in `manage-references/SKILL.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md:424`
- **Evidence:** The row reads
  `| plan-retrospective, audit-archived-plan-retrospectives | (reads realized_footprint / merge_commit_sha via the shared footprint resolver) | Resolve the realized footprint for recall and mis-prune checks post-merge |`.
  `git log -S` attributes the line to `0e7f644` (this plan). A grep over
  `.claude/skills/audit-archived-plan-retrospectives/` finds zero occurrences of `realized_footprint`,
  `merge_commit_sha`, `_footprint_resolver`, `check-artifact-consistency` or `check-routing-decisions`;
  the skill reads `references.json::modified_files` instead (`scripts/audit.py:1265-1266`).
- **Why it matters:** The consumer table is the surface a maintainer consults before changing a
  `references.json` key. It currently asserts a coupling that does not exist, which both hides G4 and
  invites someone to "safely" change the resolver believing the auditor tracks it.
- **Action:** Remove `audit-archived-plan-retrospectives` from that row (leaving `plan-retrospective`), or
  fix G4 first and then the row becomes true.
- **Done when:** Every skill named in the `manage-references` consumer table can be shown to reference the
  key or resolver the row claims, by grep.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

## G4 — Make the archived-plan auditor read the realized footprint, not the retired key

- **Kind:** bug
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:1266`
  (`modified_files_count`), `:1329` (`_plan_shipped`), `:1571` (execution-context-manifest `modified`
  column), `:1810` (scope-estimate), `:3061` (token-economics `files`), `:4178`
  (sequence-and-build-minimality); documented in `checks/token-economics.md:116`,
  `checks/scope-estimate-accuracy.md:14-15`, `checks/execution-context-manifest.md:59-60`,
  `checks/sequence-and-build-minimality.md:74`
- **Evidence:** `inputs.modified_files_count = len(refs.get("modified_files") or [])` (`:1266`).
  `_footprint_resolver.py:156-162` declares `modified_files` a `SHIM(B)` and states *"the current writer no
  longer emits the key"*; `_references_core.py:25-45` (`ReferencesData`) has no `modified_files` member;
  `_invariants.py:740-749` records that the key was *"intentionally dropped"*; and a grep for a writer
  across `marketplace/bundles/` finds none.
- **Why it matters:** For every plan created after the ledger removal, `modified_files_count` is 0. The
  consequence differs per consumer and is **not** uniform blindness — re-derived at each call site:
  - `:1810` (scope-estimate), `:3061` (token-economics `files`, the divisor behind `tokens_per_file` and
    the `big_spend_tiny_footprint` flag) and `:4178` (sequence-and-build-minimality) each read
    `modified_files_count or affected_files_count`, so they silently **substitute the declared footprint
    for the realized one**. They do not read zero — they read the wrong set, unlabelled. That is exactly
    the declared-vs-realized conflation this plan's R3 names, and it is harder to notice than a zero.
  - `:1571` (the execution-context-manifest `modified` column) has **no** fallback and reports a hard 0.
  - `:1329` (`_plan_shipped`) is `bool(plan_pr_number(...)) or modified_files_count > 0` — two
    independent sufficient criteria, so a plan carrying a PR record is still classified as shipping. The
    shipping partition is **not** meaningfully at risk; only a plan with no PR record at all would flip.
- **Action:** Resolve the footprint through the same tier order the shared resolver uses —
  `realized_footprint` → `merge_commit_sha` → `modified_files` — inside `audit.py`, and update the four
  check documents to name the resolved source rather than the raw key.
- **Done when:** An archived plan carrying only `references.realized_footprint` (no `modified_files`)
  reports a non-zero `modified` count at `:1571`, and `:1810` / `:3061` / `:4178` resolve the **realized**
  set rather than falling back to `affected_files` — asserted by a test that gives a fixture plan a
  `realized_footprint` disjoint from its `affected_files` and pins that the realized set is the one used.
- **Effort:** M
- **Risk if fixed:** Every cross-plan aggregate the auditor computes shifts, because three checks that
  have silently been grading against the declared file set will start grading against the realized one.

## G5 — Make `finalize-step-lessons-housekeeping` read a footprint key that still exists

- **Kind:** bug
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:88-91` (Step 1 read), `:55`
  (classification input), `:98` and `:318` (Error Handling fallback row)
- **Evidence:** Step 1 runs
  `manage-references get --plan-id {plan_id} --field modified_files`; `:55` says the Step 3
  classification *"reasons about what the plan changed from `modified_files`"*; `:98` and `:318` name
  `request.md` + `modified_files` as the fallback when the quality-verification report is absent — which,
  per the D2 contract, is the normal case at this step's settle-band order.
  ⚠ **The read does not return an empty list — it returns an error payload.** `_references_crud.cmd_get`
  (`:81-89`) returns `{'status': 'error', 'error': 'field_not_found', 'message': "Field 'modified_files'
  not found"}` when the key is absent, and `manage-references.py:133-143` emits that TOON and **exits 0**
  by design (*"Callers branch on the TOON `status` field, never on the process exit code"*). So the step
  receives a `status: error` document as its Step 1 outcome input, and **no row in its Error Handling
  table covers `field_not_found`** — the table's only `modified_files` row (`:318`) is about a missing
  retrospective report and names the dead key as the remedy.
- **Why it matters:** Both of this step's outcome inputs are unusable for a current plan: the
  retrospective report is normally absent at order 4, and the `modified_files` read errors. The step
  classifies lessons against `request.md` alone, with an unhandled error payload in place of a footprint.
  Plan 050's R3 rationale names exactly this consequence — *"Every finalize step that scopes itself from
  the declared file set inherits that miss"* — but scoped its fix to two retrospective consumers.
- **Action:** Change Step 1 to read the realized footprint (`--field realized_footprint`, falling back to
  `affected_files` pre-merge, since this step runs at order 4 before the capture exists), and update `:55`
  and `:318` to name the key actually read. Note the capture happens at branch-cleanup (order 70), so a
  same-run read must use the live worktree diff via `manage-references compute-footprint` rather than the
  capture.
- **Done when:** The step's Step 1 command returns `status: success` (not `field_not_found`) on a plan
  created after the ledger removal, and the fallback text at `:98` and the Error Handling row at `:318`
  name that same source.
- **Effort:** M
- **Risk if fixed:** Lesson classification will see a real file set for the first time in a while, which
  may change retain/remove decisions on the next few runs.

## G6 — Correct the `modified_files` claim in the D2 contract document

- **Kind:** doc-defect
- **Severity:** medium *(raised from low in adversarial review: the calibration puts "a false claim in
  shipped documentation" at medium, and this is the same class as G3, which is rated medium. It is not a
  cosmetic inconsistency — it is the load-bearing premise of D2's worked case.)*
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md:76-84`
  (specifically `:81`)
- **Evidence:** *"its Step 1 read of the retrospective's `quality-verification-report.md` is **best-effort
  and non-fatal** (the report is normally absent at its settle-band order, and it proceeds on `request.md`
  + `modified_files` alone), so it does **not** itself require the post-merge classify half"*. The
  `modified_files` key is no longer written (see G4/G5), so the fallback the argument rests on is empty.
- **Why it matters:** This paragraph is the worked case that justifies D2's conclusion that no step needed
  a physical split. If the fallback is in fact empty, the premise ("it proceeds fine without the
  post-merge evidence") is weaker than stated, and a later reader deciding whether their own step needs the
  split will be reasoning from a false example.
- **Action:** Once G5 is fixed, update `:81` to name the key the step actually reads. Until then, at
  minimum drop the `modified_files` half of the parenthetical so the document does not assert a live input
  that is dead.
- **Done when:** The paragraph names only inputs a grep can show the step still obtains.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

## G7 — Pin the retrospective's Step 2.5 reconcile so D3's fix cannot silently vanish

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:129-163` (Step 2.5);
  existing test `test/plan-marshall/manage-metrics/test_manage_metrics.py:1301`
- **Evidence:** `git show 0e7f644 --stat` lists `test/plan-marshall/manage-metrics/test_manage_metrics.py`
  but **not** `manage-metrics/scripts/manage-metrics.py`, and
  `git show 0e7f644^:…/manage-metrics.py | grep -c _reconcile_accumulator_into_phase` → `2`: the fold
  already existed. D3's entire shipped change is the SKILL.md prose step. `TestReconcileFloorKeepsPartiality`
  exercises `cmd_generate` directly and never reads the SKILL document, so deleting Step 2.5 leaves the
  whole suite green.
- **Why it matters:** The defect D3 fixed (retrospective reads a zero for the largest finalize phase) is
  invisible in tests and only observable on a real run — the exact condition that let it survive
  unnoticed in the first place. An unpinned prose step in a 500-line SKILL.md is one refactor away from
  being dropped.
- **Action:** Add a document-contract test (in `test/plan-marshall/plan-retrospective/`) asserting that
  `plan-retrospective/SKILL.md` contains a `manage-metrics … generate` invocation positioned before the
  aspect that reads `metrics.md`, and that the surrounding prose still states the no-`end_time` /
  live-modes-only conditions.
- **Done when:** Removing the `manage-metrics generate` call from Step 2.5 turns a named test red.
- **Effort:** S
- **Risk if fixed:** A prose-shape test can become brittle if the SKILL is restructured; anchor it on the
  command string and the aspect ordering rather than on headings.

## G8 — Give D1's edge cardinality a self-refreshing publication surface

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py:79-124`;
  the only publication is prose in
  `doc/plans/code-intelligence-substrate/050-post-run-band-contract-and-ordering-residue/report-01.md:30-40`
- **Evidence:** The report publishes *"13 edges … 13 of 24 finalize steps (≈54%)"*. Re-deriving with the
  module's own `derive_ordering_edges()` against the current tree gives **14 edges over 14 of 25 non-gate
  steps (56%)**, because `emit-landing` (order 1000, `post_run_review: true`) was added afterwards
  (`git show 0e7f644:…/standards/emit-landing.md` → not present in that commit). The test deliberately
  asserts no literal, so nothing in the tree states the current figure.
- **Why it matters:** D1's *Done when* requires the cardinality to be **published**. A number published
  only as prose in a dated report drifts within weeks, and the plan's own Verification section warns that
  *"a count presented without its coverage is the defect this plan exists to fix, reproduced."*
- **Action:** Have the derivation emit its figures where a reader will meet them — e.g. a
  `--report`-style entry point on the module, or a generated line in
  `extension-api/standards/ext-point-finalize-step.md` refreshed by a test that fails when the document
  and the derivation disagree.
- **Done when:** A reader can obtain the current edge count and coverage percentage from the tree without
  running a test file by hand, and adding a marker-carrying step updates that surface or fails a test.
- **Effort:** S
- **Risk if fixed:** A generated-doc check adds one more thing that must be regenerated when a finalize
  step is added.

## G9 — Resolve the footprint once per `check-artifact-consistency` run

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py:516`
  (inside `check_affected_files_recall`) and `:852` (for `check_affected_files_exact_match`)
- **Evidence:** Both call sites invoke `_resolve_footprint(plan_dir, plan_id)` independently; the comment
  at `:840-844` asserts the two checks *"must agree on the source of truth"* but enforces that by
  convention rather than by structure. On a live plan each call re-runs `compute_plan_branch_diff`, i.e.
  two `git diff` subprocess invocations for one value.
- **Why it matters:** No behavioural defect today — both calls take the same tiers — but the invariant the
  comment states is unenforced, and a future tier with any nondeterminism (a live worktree mutating between
  the two calls) would let the recall and exact-match checks grade against different footprints while
  reporting as one measurement.
- **Action:** Resolve once in `cmd_run` and pass the resolved value into `check_affected_files_recall`
  alongside the existing arguments, as is already done for `check_affected_files_exact_match`.
- **Done when:** `_resolve_footprint` is called exactly once per `cmd_run`, and a test asserts both checks
  receive the same object.
- **Effort:** S
- **Risk if fixed:** `check_affected_files_recall`'s signature changes; its existing tests patch the
  resolver and would need retargeting.

## G10 — Make D1's coverage canary watch `destroys`, and re-measure the floor it declares

- **Kind:** bug
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py:58`
  (`_ABSENT_CONSUMER_MARKERS`), `:18-23` (module-docstring coverage claim), `:201-221`
  (`test_consumer_side_data_edges_are_undeclared_below_the_floor`)
- **Evidence:** The module asserts, in prose at `:18-23` and as a test at `:201-221`, that *"the CONSUMER
  side of an artifact-level data edge — WHICH artifact a step READS — has **no** frontmatter marker at
  all"*. That is false against the current tree. `extension-api/standards/ext-point-finalize-step.md` now
  defines both `reads` and `destroys` as optional consumer-side fields, and
  `extension-api/standards/finalize-step-order-bands.md:76-99` states the ordering obligation they carry
  (*"a step that `reads: [worktree]` is mis-ordered if it runs after the gate"*). Two steps already
  declare the vocabulary: `phase-6-finalize/standards/branch-cleanup.md:9` → `destroys: [worktree]` and
  `phase-6-finalize/standards/archive-plan.md:9` → `destroys: [plan-directory]`. Running the module's own
  `_finalize_records()` with `destroys` added to the probe set finds both declarers; running it as
  shipped finds none, because `_ABSENT_CONSUMER_MARKERS` (`:58`) lists only `reads`, `consumes`,
  `reads_artifacts`, `consumes_artifacts`. The canary's docstring promises *"If a future plan adds a
  `reads`/`consumes` marker, this test fails and the floor is re-measured"*; that plan arrived
  (`308528d`, #1211, 2026-08-13 — one day after plan 050 landed) and the suite stayed green.
- **Why it matters:** D1's deliverable was *"the enumeration mechanism's coverage is stated"*, and the
  canary is the mechanism that keeps that statement true as the vocabulary moves. It failed at its first
  real test, so the tree now carries a confidently-worded coverage claim that is false, guarded by a test
  that reports green. This is the plan's own stated defect — *"a count presented without its coverage is
  the defect this plan exists to fix"* — reproduced one level up, in the coverage rather than the count.
- **Action:** Add `destroys` to `_ABSENT_CONSUMER_MARKERS` (which makes the canary fail immediately, as
  intended), then discharge the failure by re-measuring: rewrite `:18-23` and the test to state that the
  consumer-side vocabulary **exists but is not yet derived into edges**, and either extend
  `derive_ordering_edges()` to emit `reads`→producer and `reads`-after-`destroys` edges, or declare
  those edges out of the current derivation's scope **and pin that policy with its own contract test** —
  one that enumerates the step docs declaring `reads`/`destroys` today and goes red when a new
  declaration appears, so an out-of-scope declaration is still caught rather than absorbed silently.
  Prefer extending the derivation: `destroys` is declared and its ordering obligation is documented, so
  a real edge class is currently underived. Whichever branch is taken, the canary must not simply be
  widened to *accept* the vocabulary — that would satisfy the rewrite while leaving the next declaration
  green and unrepresented, which is the failure this gap records.
- **Done when:** Adding a `reads:` **or** a `destroys:` declaration to any finalize step doc either
  produces a derived edge that the GATE assertion checks, or turns a named test red — and no statement in
  the module claims the consumer-side vocabulary is empty while `ext-point-finalize-step.md` defines it.
- **Effort:** M
- **Risk if fixed:** Deriving `reads`/`destroys` edges may surface existing ordering violations that the
  gate-relative derivation never checked; those are real findings but will need triage before the gate
  can go green.
