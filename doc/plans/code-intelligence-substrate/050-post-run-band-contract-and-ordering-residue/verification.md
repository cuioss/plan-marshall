# Verification — 050-post-run-band-contract-and-ordering-residue

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`; re-verified end to end at
`a90adeb` on the same branch during the adversarial review (see § Adversarial review)
**Landed as:** `0e7f644` — *fix(finalize): post-run band contract + retrospective accumulator + realized-footprint capture (plan 050) (#1175)*
**Overall verdict:** CONFIRMED WITH GAPS

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Derive producer→consumer edges; publish cardinality; state coverage floor | New `test_finalize_edge_ordering.py`; 13 edges over 13 of 24 steps (~54%); floor stated; 6 tests pass | Test present and derivation-driven; 6/6 pass; re-derived **14 edges over 14 of 25 non-gate steps (56%)** today; gate test proven non-vacuous by mutation, and the cardinality test proven to fire as a mutual-exclusion guard. Published cardinality lives only as report prose and has already drifted. **The shipped "consumer side is undeclared" coverage claim is now false**: a later plan added the `reads`/`destroys` vocabulary and the canary meant to force a re-measurement did not fire | CONFIRMED at landing (publication surface weak — G8; coverage claim now stale and its canary half-blind — G10) |
| D2 | Settle the band contract for post-merge-evidence + source-mutating step | Split chosen; recorded in `source-edit-pushability.md` + pointer in `ext-point-finalize-step.md`; no physical split needed | Both documents present and consistent; my own cold read lands unambiguously on **"representable — by a split"** | CONFIRMED |
| D3 | Retrospective reads a closed accumulator | New Step 2.5 in `plan-retrospective/SKILL.md` + pinning test `TestReconcileFloorKeepsPartiality` | Step 2.5 present; test present and non-vacuous (mutation → red). **No production code shipped** — `_reconcile_accumulator_into_phase` and its `cmd_generate` call predate the plan; the fix is a prose workflow instruction that no test pins | PARTIAL (mechanism correct, unenforced — G7) |
| D4 | Capture the footprint while it is true; resolver prefers it | `capture-footprint` verb + shared `_footprint_resolver` (5 tiers) + merge-commit fallback + both consumers recover together; negative control preserved | Verb, resolver, branch-cleanup wiring and both consumers all present and correct. **But** the documented aspect-13 command still passes a `--diff-file` that no step in the tree produces, so the mis-prune consumer's recovery branch is never taken (and today hard-errors) | PARTIAL (G1) |
| D5 | Not self-exercising; name the observation point | Report § D5 states what the run could and could not substantiate | Section present, accurate, and correctly identifies the derivation-level tests as the only in-run evidence | CONFIRMED |

## Per-deliverable detail

### D1 — derive the producer→consumer edges (GATE, mutates nothing)

- **Required (plan):** *"the edge set is derived from step definitions, the cardinality is published,
  and the enumeration mechanism's coverage is stated."*
- **Claimed (report):** 13 edges (7 before-gate, 6 after-gate); coverage a FLOOR at 13 of 24 finalize
  steps (~54%); consumer-side vocabulary pinned empty; 6 tests pass.
- **Found:** `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py:79`
  (`derive_ordering_edges`), `:127` (gate discoverability), `:146` (the GATE assertion), `:167`
  (cardinality pinned to its own derivation, no literal), `:184` (coverage-is-a-floor), `:201`
  (consumer-side markers asserted absent).
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py -o addopts="" -q`
    → `6 passed in 2.36s`.
  - Re-derived the edge set myself by importing `derive_ordering_edges()` against the live tree:
    **gate order 70; 26 discovered finalize steps (25 excluding the gate); 14 edges; 14 marker-carrying
    steps.** Before-gate (`mutates_source`): `finalize-step-sync-baseline` 3,
    `finalize-step-lessons-housekeeping` 4, `finalize-step-simplify` 8, `finalize-step-security-audit` 9,
    `finalize-step-era-stamp-fill` 21, `automatic-review` 30, `sonar-roundtrip` 40. After-gate
    (`post_run_review`): `finalize-step-review-retrospective` 990, `lessons-capture` 991,
    `finalize-step-preference-emitter` 992, `plan-retrospective` 995, `record-metrics` 998,
    `finalize-step-print-phase-breakdown` 999, **`emit-landing` 1000**.
  - **Mutation proof of the GATE.** Snapshotted
    `marketplace/…/phase-6-finalize/standards/record-metrics.md`, changed `order: 998` → `order: 5`,
    re-ran the file: `1 failed, 5 passed` with
    `AssertionError: … ['default:branch-cleanup (order 70) → default:record-metrics (order 5) [post_run_review]']`.
    Restored from the snapshot; `git status --porcelain` clean for that path.
  - Confirmed the drift is benign: `git show 0e7f644:…/standards/emit-landing.md` → *"exists on disk,
    but not in '0e7f644'"*, i.e. `emit-landing` was added after this plan landed and the derivation
    picked it up with no edit — exactly the no-literal design working.
  - **Mutation proof of the mutual-exclusion guard** (the audit originally asserted this without
    testing it). Same snapshot discipline: set `record-metrics` `mutates_source: false → true` so it
    declares both markers; re-ran the file → `2 failed, 4 passed`, the cardinality test reporting
    `Derived edge count (15) disagrees with the marker-carrying step count (14)`. The claim that the
    cardinality test doubles as a mutual-exclusion guard is therefore **proven**, not assumed.
    Restored from the snapshot; `git status --porcelain` clean for that path.
- **Verdict:** CONFIRMED **as of landing**. Caveats: (a) the plan's first sentence asks *"which
  artifacts it reads and which it writes"*; the shipped derivation covers only the **gate-relative**
  edges expressible in the vocabulary that existed then, and declared the artifact-level consumer side
  to be below the floor (`test_finalize_edge_ordering.py:201`). That satisfied the literal *Done when*
  and was stated, not hidden. (b) The "published cardinality" has no self-refreshing surface — see G8.
  (c) **That coverage declaration has since become false, and the mechanism D1 shipped to detect the
  change did not fire.** `ext-point-finalize-step.md` now defines `reads` and `destroys` as consumer-side
  data-edge fields, with the ordering obligation spelled out in `finalize-step-order-bands.md:76-99`
  (*"a step that `reads: [worktree]` is mis-ordered if it runs after the gate"*), and two steps already
  declare `destroys`. The canary's own docstring promises *"If a future plan adds a `reads`/`consumes`
  marker, this test fails and the floor is re-measured"* — that plan arrived (`308528d`, #1211,
  2026-08-13, one day after this plan landed) and the test stayed green, because
  `_ABSENT_CONSUMER_MARKERS` watches only the four read-side spellings and not `destroys`, the half
  actually declared. See G10.

### D2 — settle the band contract

- **Required (plan):** one of {sanctioned exception with a push path, split, explicit
  "unrepresentable"} implemented, *"and the reasoning is recorded in the contract document, not only in
  the run report."*
- **Claimed (report):** the split; recorded in `source-edit-pushability.md` plus a pointer in
  `ext-point-finalize-step.md`; `lessons-housekeeping` documented as the worked case that does not need
  a physical split.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/source-edit-pushability.md:42`
    — § *"The both-sides need is representable — by a split, not by one step"*, with the classify/apply
    split at `:50-58`, the **cross-run seam** statement at `:60-67`, the distinction from the
    discover-after-merge rule at `:69-74`, the `lessons-housekeeping` worked case at `:76-84`, and the
    authoring-checklist entry at `:155-157`.
  - `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:47` —
    the `post_run_review` row now says the exclusion *"is **not a dead-end** … the need is representable
    by a **split**"* and cross-references the section above.
- **Checks run:** my own cold read of both documents without reading the report first. Neither
  document supports an "explicitly refused" reading: the single-step refusal ("No step may declare
  both", `source-edit-pushability.md:31-34`) is paired in both files with a **titled affirmation** of
  representability. `post_run_source_guard.py` is untouched by this plan and needs no change under the
  split outcome.
- **Verdict:** CONFIRMED.

### D3 — the retrospective reads a closed accumulator

- **Required (plan):** *"the retrospective's reading of the largest phase is non-zero on a run where
  that phase did work, and the partiality machinery still marks a genuinely-absent row."* Explicitly:
  close the accumulator, do not merely re-order the reader; leave the partiality labelling intact.
- **Claimed (report):** new Step 2.5 in `plan-retrospective/SKILL.md` regenerates `metrics.md` before
  aspect 4 reads it, folding the durable accumulator floor without stamping `end_time`;
  `record-metrics`' later close is assign-cumulative so no double-count; pinning test asserts fold +
  partiality together.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:129` — § *"Step 2.5: Reconcile
    the phase accumulators into `metrics.md` (live modes only)"*, with the `manage-metrics generate`
    call at `:145-148` and the "does not stamp an `end_time`" / assign-cumulative argument at `:150-158`.
  - `test/plan-marshall/manage-metrics/test_manage_metrics.py:1301`
    (`TestReconcileFloorKeepsPartiality`), asserting `total_tokens == 54321` on the folded row **and**
    `'6-finalize' in result['phases_missing_end_time']`.
- **Checks run:**
  - Verified the no-double-count argument in the code rather than taking the report's word:
    `manage-metrics.py:778` (`_resolve_token_field` → provenance `'accumulator'` when no explicit flag),
    `:813` (`_apply_provenance` — `'flag'` adds, anything else **assigns**), `:1234-1253`
    (`_close_phase_accumulating` resolves `duration_ms` / `total_tokens` / `tool_uses` through that
    path), and `phase-6-finalize/standards/record-metrics.md:43-46` — the documented `end-phase`
    invocation passes **no** token flags, so every field resolves as `'accumulator'` and is assigned,
    overwriting the retrospective's floor. The claim holds; `agent_duration_ms` is assigned on the same
    provenance, so it does not double-count either.
  - `_reconcile_accumulator_into_phase` (`manage-metrics.py:1138`) is backfill-only (`:1161`, `:1165`,
    `:1169` all guard on the field being absent), so a closed row is left byte-identical.
  - **Mutation proof.** Snapshotted `manage-metrics.py` (from a verified-clean state), replaced the
    `cmd_generate` reconcile call at `:1426` with `pass  # MUTATED-050`, ran
    `pytest test/plan-marshall/manage-metrics/test_manage_metrics.py -k ReconcileFloor -o addopts=""` →
    `1 failed` with `KeyError: 'total_tokens'`; the same call verified still mutated (`grep -c` → `1`)
    at run time. Restored from the snapshot; `git status --porcelain` clean.
    *(Note: a first attempt at this mutation was silently reverted by a concurrent process in the shared
    checkout; the result reported here is from the re-run whose mutation was confirmed present.)*
- **Verdict:** PARTIAL. The mechanism is correct and the pinning test is non-vacuous **about the
  mechanism**, but two things fall short of the deliverable's spirit:
  1. **No production code shipped for D3.** `git show 0e7f644 --stat` lists
     `test/plan-marshall/manage-metrics/test_manage_metrics.py` but **not**
     `manage-metrics/scripts/manage-metrics.py`; `git show 0e7f644^:…/manage-metrics.py | grep -c
     _reconcile_accumulator_into_phase` → `2`, so the fold already existed. The delivered change is the
     SKILL.md prose step.
  2. **Nothing pins the invocation.** Deleting Step 2.5 from `plan-retrospective/SKILL.md` leaves every
     test green — the pinning test exercises `manage-metrics generate` directly, not the retrospective's
     call to it. See G7.

### D4 — capture the footprint while it is true

- **Required (plan):** persist the realized footprint as a deterministic side effect of
  branch-cleanup/push and make the resolver prefer it; never `base..HEAD`; evaluate the merge-commit
  tier; design the SHA-recovery seam; *"feed the same resolved list to the routing-decisions check so
  both consumers recover together."* *Done when:* a post-merge retrospective resolves the footprint and
  reports a measurable recall instead of `inconclusive`; the negative control still yields
  `inconclusive`.
- **Claimed (report):** all of the above delivered; negative control preserved
  (`test_tier5_unresolvable_negative_control`, `test_mis_prune_skipped_when_footprint_unresolvable`).
- **Found:**
  - `marketplace/…/manage-references/scripts/_cmd_compute_footprint.py:90` (`cmd_capture_footprint`) —
    computes through `cmd_compute_footprint` and writes `refs['realized_footprint']` at `:121`;
    propagates the compute error verbatim and writes nothing on failure (`:112-117`).
  - `marketplace/…/plan-retrospective/scripts/_footprint_resolver.py:204` (`resolve_footprint`) — five
    tiers in the documented order; tier 2 preferred at `:223`; merge-commit tier at `:165` using
    `git -C {plan_dir} diff --name-only {sha}^1 {sha}` (`:192`) — **not** a `base..HEAD` range; sentinel
    at `:57` and the `footprint_resolved` predicate at `:114`.
  - `marketplace/…/phase-6-finalize/standards/branch-cleanup.md:1418-1438` — the capture before worktree
    removal, explicitly non-fatal on error; `:1498-1524` — the SHA-recovery seam (`git rev-parse HEAD`
    after `switch-and-pull`, recorded via `manage-references set --field merge_commit_sha`), with the
    non-squash / Branch-F case stated.
  - Consumers: `check-artifact-consistency.py:516` and `:852` (recall + exact-match, both through
    `_resolve_footprint` → the shared chain), `check-routing-decisions.py:750-767` (mis-prune, recovers
    when `--diff-file` is absent, `footprint_source` reported).
- **Checks run:**
  - Read `_footprint_resolver.py` end to end. Tier 1 reports UNRESOLVABLE on `CalledProcessError`
    (`:220-221`) rather than falling through — correct and deliberate; `analyze-logs.py:262-296` keeps
    the opposite policy and composes the per-tier helpers instead, matching the report's residue note.
  - Negative controls exist and are behavioural, not tautological:
    `test/plan-marshall/plan-retrospective/test_footprint_resolver.py:204`
    (`test_tier5_unresolvable_negative_control`) and `:218`, plus the routing-decisions
    `footprint_source == 'unresolved'` assertion at `test_check_routing_decisions.py:197`.
  - The true-merge tier test at `test_footprint_resolver.py:146` builds a real repo with a sibling
    commit on `main` and asserts the sibling is **excluded** — the sibling-contamination prohibition is
    tested, not just asserted in prose.
  - Capture-verb coverage: `test/plan-marshall/manage-references/test_manage_references_compute_footprint.py:357`
    (persists), `:382` (matches `compute-footprint`), `:401` (idempotent), `:418` (error propagates
    without writing).
- **Verdict:** PARTIAL. The capture, the resolver, the merge-commit tier and the recall consumer are
  all correct and covered. The "two consumers recover together" half is **wired in the script but dead
  in the shipped workflow**: `plan-retrospective/SKILL.md:275` still invokes aspect 13 with
  `--diff-file work/footprint.txt`, and a full-repo search finds **no producer of that file anywhere**
  (14 hits, all inside `plan-retrospective` docs/scripts/tests). At plan 050's landing that degraded
  benignly (a missing file returned `[]`, so `cmd_run` fell through to the resolver); a later change
  (`eb0124c`, #1288) made `resolve_diff_file_path` **raise** on an unresolvable supplied path, so the
  documented invocation now takes the raise branch and never reaches the recovery. See G1.

### D5 — not self-exercising

- **Required (plan):** *"a derivation-level test exists that is observable from inside the run, and the
  run report states plainly which evidence its own execution could and could not provide."*
- **Found:** `report-01.md:90-104`. It names `test_finalize_edge_ordering.py`,
  `TestReconcileFloorKeepsPartiality` and `test_footprint_resolver.py` as the in-run evidence, and
  states plainly that no end-to-end finalize ran, that a cloud-lane run does not execute phase-6-finalize
  at all, and that even under the plan-marshall lifecycle a green finalize would execute the OLD order.
  `test_finalize_edge_ordering.py:31-34` carries the same D5 note in the module docstring.
- **Verdict:** CONFIRMED. This is the most accurate section of the report.

## Correctness review

I read `_footprint_resolver.py` (all 235 lines), `_cmd_compute_footprint.py:40-132`,
`manage-metrics.py:778-824` / `:1138-1281` / `:1403-1440`, `check-routing-decisions.py:379-413` and
`:740-800`, `check-artifact-consistency.py:490-600` and `:820-880`, `check-manifest-consistency.py:166-222`
and `:570-666`, `analyze-logs.py:220-300`, plus the four contract documents. Findings:

1. **The aspect-13 footprint recovery is unreachable under the documented invocation.**
   `plan-retrospective/SKILL.md:275` passes `--diff-file work/footprint.txt`; nothing in the repository
   writes that file. `check-routing-decisions.py:750` → `load_diff_files` → `resolve_diff_file_path`
   (`_footprint_resolver.py:98-111`) raises `ValueError`, which `safe_main`
   (`tools-file-ops/scripts/file_ops.py:1688-1698`) converts into `status: error / internal_error` with
   exit 1. Consequence: the mis-prune aspect errors out instead of recovering through the resolver D4
   built for it. (Attribution: the raise came from `eb0124c` (#1288); the phantom path predates plan
   050 — `git show 0e7f644^:…/SKILL.md | grep footprint.txt` finds it at line 235. Plan 050 wired the
   fallback but left the caller pointing at a file that does not exist.) → **G1**

2. **A third footprint consumer was never migrated.** `check-manifest-consistency.py:166-222` re-derives
   its own `git diff {base}...HEAD --name-only` in the process cwd and does not touch
   `_footprint_resolver.resolve_footprint`. Its documented invocation
   (`plan-retrospective/SKILL.md:262-263`) passes neither `--diff-file` nor `--base-ref`, so post-merge
   `base_label == 'unknown'`, `evidence_available == False`, and `_withhold_on_absent_evidence`
   (`:581-605`) downgrades every diff-fed rule **that would otherwise report a clean `pass`** to
   `indeterminate` (a `fail` and a `skip` are explicitly left untouched — `:589-590`). That is honest —
   no graded zero — but it is a permanently blind check that the shipped capture could feed. → **G2**

3. **`references.modified_files` is read by live consumers although it is no longer written.**
   `_footprint_resolver.py:156-162` declares the key a `SHIM(B)` for pre-ledger archives and states
   *"the current writer no longer emits the key"*; `_references_core.py:25-45` (`ReferencesData`) has no
   `modified_files` member. Yet
   `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:88-90` still reads it as its Step 1
   outcome input (and `:98` / `:318` name it in the fallback), and
   `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:1266` / `:1329` / `:1571` /
   `:1810` / `:3061` / `:4178` read it for `modified_files_count`. For every plan created after the
   ledger removal these read nothing.
   ⚠ **The blast radius is narrower than it first appears, and the audit's first pass overstated it.**
   Re-derived per consumer: `:1810` (scope-estimate), `:3061` (token-economics `files`, which is what
   `tokens_per_file` and `big_spend_tiny_footprint` are computed from) and `:4178`
   (sequence-and-build-minimality) all read `modified_files_count or affected_files_count` — they
   **fall back** to the *declared* set rather than reading zero. `_plan_shipped` (`:1329`) is
   `bool(plan_pr_number(...)) or modified_files_count > 0` — two independent sufficient criteria, so a
   plan carrying a PR record still classifies as shipping. The only consumer that genuinely reports a
   hard zero is the execution-context-manifest `modified` column (`:1571`). The defect that remains is
   real but is a **silent substitution of the declared footprint for the realized one** — precisely the
   conflation this plan's R3 exists to name — plus one zeroed column. → **G4**, **G5**

4. **A false claim landed in shipped documentation.**
   `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md:424` — added by this plan
   (`git log -S` → `0e7f644`) — lists `audit-archived-plan-retrospectives` as reading
   `realized_footprint` / `merge_commit_sha` *"via the shared footprint resolver"*. A grep over
   `.claude/skills/audit-archived-plan-retrospectives/` finds **zero** occurrences of
   `realized_footprint`, `merge_commit_sha`, `_footprint_resolver`, `check-artifact-consistency` or
   `check-routing-decisions`. → **G3**

5. **A second stale claim in a document this plan authored.**
   `source-edit-pushability.md:81` states `lessons-housekeeping` *"proceeds on `request.md` +
   `modified_files` alone"* — i.e. the D2 contract's worked case rests on the retired key. → **G6**

6. **Duplicated resolution.** `check-artifact-consistency.py` resolves the footprint twice per run
   (`:516` inside the recall check and `:852` for the exact-match peer). On a live plan each call
   re-runs `compute_plan_branch_diff`, i.e. two `git diff` subprocesses for one value. No behavioural
   defect — both calls take the same tiers — but the comment at `:840-844` asserting the two "must
   agree on the source of truth" would be structurally guaranteed by one call. → **G9**

No fail-open branch, unfireable guard, off-by-one, unguarded `None`, or stale-surface read was found in
the code this plan actually shipped. The two places I specifically hunted for a fail-open — the
`FOOTPRINT_UNRESOLVED` sentinel vs. empty-set distinction (`_footprint_resolver.py:135-148`, `:114-120`)
and the `_apply_provenance` add-vs-assign split (`manage-metrics.py:813-823`) — are both correct and
both covered by behavioural tests.

## Test adequacy

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D1 | `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py` (6 tests) | **Non-vacuous — proven twice.** Mutating `record-metrics` `order: 998 → 5` turns the GATE red with the offending edge named. Mutating it to declare **both** markers turns the cardinality test red (`15` edges vs `14` marker-carrying steps), so the mutual-exclusion guard is proven rather than assumed. **But `test_consumer_side_data_edges_are_undeclared_below_the_floor` is a canary that no longer guards what it names**: it watches `('reads', 'consumes', 'reads_artifacts', 'consumes_artifacts')` and is blind to `destroys`, which `default:branch-cleanup` and `default:archive-plan` now declare. It passes today because the vocabulary was widened on the half it does not watch — the opposite of "passes trivially, which is its intent". → G10 |
| D2 | none | No test — correct, this is a documentation deliverable. The plan's own verification asks for a **cold read**, which the report records and which I reproduced independently. |
| D3 | `test_manage_metrics.py:1301` `TestReconcileFloorKeepsPartiality` | **Non-vacuous about the mechanism on BOTH halves — proven.** Removing the `cmd_generate` reconcile turns it red (`KeyError: 'total_tokens'`), and — the check the audit originally omitted — making `_reconcile_accumulator_into_phase` stamp an `end_time` also turns it red (`assert False is True` on `any_phase_missing_end_time`), so the "leave the partiality labelling intact" half of D3's *Done when* is genuinely guarded, not merely asserted. **Vacuous about the deliverable**: it never touches `plan-retrospective/SKILL.md`, so deleting Step 2.5 — the entire shipped change — leaves the suite green (measured: **1420 passed** across `test/plan-marshall/plan-retrospective` + `test/plan-marshall/manage-metrics` with the section removed). → G7 |
| D4 | `test_footprint_resolver.py` (14 tests: tiers 2/3/4/5, precedence, resolved-empty vs unresolvable), `test_manage_references_compute_footprint.py:348-437` (capture verb), `test_check_routing_decisions.py:175-214` (`footprint_source` ∈ {resolved, unresolved, diff_file}) | Strong at the unit level, including a real-git true-merge fixture (`test_footprint_resolver.py:145`) that builds a sibling commit on `main` and proves it is excluded. **Negative control proven non-vacuous by mutation** (the audit had only shown the tests exist): replacing the resolver's terminal `return FOOTPRINT_UNRESOLVED` with `return set()` — the exact graded-zero defect D4 forbids — turns **4 tests red** across two files, including `assert 'pass' == 'skip'` on the mis-prune check, i.e. a fabricated empty footprint would have graded a verdict instead of skipping. **Gap:** nothing tests the documented SKILL.md invocation end to end, which is why the phantom `--diff-file` survived (G1). |
| D5 | n/a | Discharged by the report. |

## Report accuracy

Claims checked one by one against the tree now:

- **"Published cardinality … 13 edges … 13 of 24 finalize steps (≈54%)"** — now **14 edges over 14 of 25
  non-gate steps (56%)**, because `emit-landing` (order 1000, `post_run_review: true`) was added after
  this plan landed (`git show 0e7f644:…/emit-landing.md` → not in that commit). The number was true when
  written; a run report is an explicitly dated record under the lane's documentation carve-out, so this
  is drift rather than a false claim — but it is evidence that a prose-only publication surface does not
  hold (G8).
- **"Merge gate `default:branch-cleanup` at order 70"** — re-derived: **70**. True.
- **"all 6 tests pass"** (D1) — re-run: `6 passed in 2.36s`. True.
- **"no step was physically split"** — true; `git show 0e7f644 --name-status` touches no step frontmatter
  and no `.claude/skills/finalize-step-lessons-housekeeping/` file.
- **"record-metrics' `end-phase` reads the accumulator with source `accumulator` → `_apply_provenance`
  ASSIGNS"** — verified in code (`manage-metrics.py:800-803`, `:813-823`) *and* in the documented
  invocation (`record-metrics.md:43-46` passes no token flags). True.
- **"`{sha}^1 {sha}` … exact for squash and true-merge, no sibling contamination, never `base..HEAD`"** —
  verified in `_footprint_resolver.py:192` and by the real-repo test at `test_footprint_resolver.py:146`.
  True.
- **"`check-routing-decisions` recovers via the resolver when `--diff-file` is absent"** — true of the
  **script** (`:758-767`). **Misleading about the system**: the only documented invocation always supplies
  `--diff-file`, so the recovery does not run in practice. The report's stronger framing — *"One footprint
  resolution, two consumers (recall + mis-prune) recover together"* — is **overstated** against the shipped
  workflow.
- **"`analyze-logs.resolve_footprint` keeps its own diff-failure fall-through policy"** — verified at
  `analyze-logs.py:262-296`. True.
- **"A final marketplace-wide grep confirms no stale 2-tier resolver claim remains"** — re-derived with a
  fresh grep for `three-tier|two-tier|3-tier|2-tier` across `marketplace/`, `test/`, `doc/`: 19 hits, none
  about the footprint resolver (bypass-actor resolution, executor logging, manifest source model, effort
  presets, chat-history degradation, etc.). True.
- **"16001 passed, 1 skipped"**, the per-commit `quality-gate` runs, the PR/CI/review-thread observations,
  and the seven branch commit SHAs (`5e589b4`, `3c8f400`, `d2dabf7`, `a4b7f25`, `52366d0`, `603568f`,
  `5382861`) — **UNVERIFIABLE.** `git cat-file -t` reports *"Not a valid object name"* for all seven: the
  PR was squash-merged and the branch is gone. I did not re-run `./pw verify` (out of scope per brief).
- **New false claim shipped alongside the report** —
  `manage-references/SKILL.md:424` names `audit-archived-plan-retrospectives` as a shared-resolver
  consumer; it is not one (G3). This is in shipped documentation, not the report, so it is a
  higher-severity finding than a stale report number.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| Merge-commit tier records `merge_commit_sha` only on the synchronous landing path; the enqueued-not-yet-landed path (Branch F) relies on the pre-removal `realized_footprint` capture plus re-entry | **Open, by design, and documented as claimed** | `branch-cleanup.md:1520-1524` states exactly this; `_footprint_resolver.py:182-184` repeats it in the resolver docstring; `_references_core.py:41-45` in the schema comment. Accurate. |
| `analyze-logs.resolve_footprint` keeps its own diff-failure fall-through policy, composing the per-tier helpers rather than the whole-chain resolver | **Open, intentional, documented** | `analyze-logs.py:262-266` (the divergence stated in the docstring) and `:284-289` (`except subprocess.CalledProcessError: pass  # fall through`), vs. `_footprint_resolver.py:220-221` (fail-closed). Accurate; no consolidation has since flipped it. |

Neither residue item was closed by a later plan, and neither has become moot.

## Out-of-scope and collateral

Checked each exclusion against `git show 0e7f644 --name-status` (26 files):

- **Partiality labelling** — respected. No change to `phases_missing_end_time` /
  `any_phase_missing_end_time`; `manage-metrics/scripts/manage-metrics.py` is not in the commit at all,
  and the D3 test explicitly asserts the labelling survives.
- **Corpus-resolution half / both epics editing the band contract** — respected. No
  `.claude/skills/finalize-step-lessons-housekeeping/` file was touched; the single
  `ext-point-finalize-step.md` edit is a one-line pointer, which is this plan's own half of the split
  ownership.
- **A second reader obligation for absent inputs** — respected. `check-artifact-consistency.py:540-551`
  and `:593-600` keep the pre-existing `inconclusive` sentinel behaviour; the plan's REFUTED claim label
  was honoured rather than re-scoped.
- **The declared-file-set side of the footprint** — respected. `affected_files` is untouched; the new key
  is `realized_footprint`, kept distinct in `ReferencesData` (`_references_core.py:34`, `:39`).
- **Collateral beyond the deliverables:** the seven-plus stale-doc fixes the report describes (2-tier →
  5-tier prose across `check-artifact-consistency.py`, `check-routing-decisions.py`,
  `artifact-consistency.md`, `routing-decision-verification.md`, `logging-gap-analysis.md`,
  `plan-retrospective/SKILL.md`, and test docstrings) are all present in the landed diff and are declared
  in the report. No undeclared change found.

## Method and coverage

**What I did.** Read `plan.md` and `report-01.md` in full, then the four expected-surface documents, the
shipped resolver and both consumers, the capture verb, the branch-cleanup wiring, the metrics
accumulator arithmetic, and every test file named in the report. Re-derived the D1 edge set by importing
the test module's own derivation against the live tree. Ran two targeted pytest files. Performed two
mutation experiments (D1 gate, D3 fold), each with a byte snapshot taken by me under
`$TMPDIR/…/verify-050-mutsweep/` and restored from that snapshot, with `git status --porcelain` verified
clean afterwards for both paths — never `git checkout`/`restore`/`stash`. Ran a full-repo search for
`footprint.txt` producers and a marketplace-wide search for stale tier-count prose, in both cases first
confirming the pattern finds the hits I already knew about.

**What I could not check.**

- The report's build-gate figures (`16001 passed, 1 skipped`), the per-commit `quality-gate` results, the
  PR-review surface (`0 inline threads`, reviewer verdicts) and the seven branch commit SHAs — the branch
  was squash-merged and deleted, and re-running `./pw verify` is outside this audit's brief.
- **D4's literal *Done when*** — *"a post-merge retrospective resolves the footprint and reports a
  measurable recall instead of `inconclusive`"* — is UNVERIFIABLE from a fresh clone: it needs a real
  archived plan directory carrying `references.realized_footprint`, which lives under the git-ignored
  `.plan/` tree. The unit-level tiers are verified; the end-to-end assertion is not, which is precisely
  what D5 says the run itself could not substantiate either.
- **D3's literal *Done when*** — the retrospective reading a non-zero largest phase **on a real run** —
  is likewise unverifiable here; what is verified is that the mechanism it calls produces that result.

**Shared-checkout caveat.** This audit ran alongside other verification agents in the same working tree.
One of my mutation runs was invalidated by a concurrent process restoring the file mid-run; I detected it
by diffing my snapshot against the tree, discarded that snapshot (it had captured another agent's
mutation), re-snapshotted from a `git status`-clean state, and re-ran. Every mutation result reported
above was confirmed to have the mutation present at run time.
