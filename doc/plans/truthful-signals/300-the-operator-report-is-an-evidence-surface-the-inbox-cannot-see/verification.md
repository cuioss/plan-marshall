# Verification — 300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see

**Verified against:** commit `af417166dd9f64704fe738720d716c38515061be`   **Landed as:** PR #1211, commit `308528d67472c8efaba7abd3ce5d6b696a8c0967`   **Verdict:** fully-implemented

## Method

- Read `plan.md` and `report-01.md` in full; extracted D0–D3, their *Done when:* conditions, the
  Out-of-scope list, the Expected surface, the Claim-labels table, and the four Verification bullets.
- Located the landed squash commit `308528d6` (`git log --oneline --all --grep '#1211'`); read its
  full `--stat` (34 files, +972/−192) and the per-file diffs for `_manifest_core.py`,
  `manage-execution-manifest.py`, `decision-rules.md`, `manage-execution-manifest/SKILL.md`,
  `phase-6-finalize/SKILL.md`, `ext-point-finalize-step.md`, `archive-plan.md`, `branch-cleanup.md`,
  `finalize-step-lessons-housekeeping/SKILL.md`, `finalize-step-preference-emitter.md`,
  `test_finalize_orchestration_routing.py`, `test_steps_sort.py`,
  `test_manage_execution_manifest_validate.py`, `test_session_binding.py`,
  `test_declared_step_contract_regression.py`, `test_extension_discovery.py`.
  The pre-PR branch commits (`feba50d`, `08e8da6`) are **not reachable** — the branch was
  squash-merged and deleted (`git cat-file -t` → "Not a valid object name").
- Opened at HEAD: `extension-api/standards/finalize-step-order-bands.md` (whole file),
  `ext-point-finalize-step.md` § Implementor Frontmatter + § Current Implementations,
  `phase-6-finalize/SKILL.md` § stages, `_manifest_validation.py`
  (`_sort_steps_by_frontmatter_order`, `_check_ascending_order`, `check_emitted_steps_ascending_order`,
  `_resolve_step_order_verdict`), `extension_discovery.py` (`find_implementors`,
  `_build_implementor_record`, `_read_frontmatter_fields`, `_IMPLEMENTOR_FRONTMATTER_KEYS`),
  `_manifest_core.py` (`DEFAULT_PHASE_6_STEPS` + its comment block),
  `test_steps_sort.py`, `test_cmd_quality_phases.py`, `test_manage_execution_manifest_validate.py`,
  `test_finalize_step_print_phase_breakdown.py`, `test_architecture_refresh.py`.
- **Executed** (not read): `find_implementors('…ext-point-finalize-step')` → 26 records, printed with
  order + source; `find_implementors('…ext-point-build-verify-step')` → 1 record (`default:verify`,
  order 10); `_sort_steps_by_frontmatter_order(DEFAULT_PHASE_6_STEPS)` → resolved orders
  `8, 9, 11, 20, 22, 30, 40, 62, 70, 991, 998, 1100`.
- **Test run:** `uv run python -m pytest test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py -o addopts="" -q` → **64 passed** in 0.62 s.
- **Mutation check (D3, the highest-risk guard).** `git diff --quiet` confirmed
  `phase-6-finalize/standards/architecture-refresh.md` was unmodified; saved its bytes to the
  scratchpad, set `order: 10` → `order: 9` to recreate the exact live collision the plan describes,
  re-ran the class → `1 failed, 1 passed` with
  `AssertionError: … Colliding orders: {9: ['default:architecture-refresh', 'default:finalize-step-security-audit']}`
  — byte-identical to the failure the report preserves — while the anti-vacuity
  `test_discovery_is_non_empty` still PASSED. Restored from the saved bytes (not `git checkout`);
  `git diff --quiet` and `git status --porcelain` both clean afterwards.
- Completeness sweeps (`grep -rn` over `marketplace/`, `.claude/`, `test/`, excluding `doc/plans/`):
  `archive-plan` × `1000`/`order`; `architecture-refresh` × `order`; `push` × `\b10\b`/`order < 10`;
  `^order:` frontmatter across all bundles and project skills; `destroys`; `^reads:`;
  `post_run_review`/`mutates_source` frontmatter of every 900–1100 band member.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive population + semantics from the composer's source | Population derived; per-phase-vs-global and tie-break answered from the composer | Yes (mutates nothing) | Yes | Yes | Yes | Population re-derived by executing `find_implementors` → 26 steps, all orders distinct; the report's 25-row table matches exactly once `default:emit-landing` (added later by plan 302, PR #1215) is excluded. Per-phase: `extension_discovery.py:1383` sorts one ext-point population; the phase-5 verify population is a separate list of 1 (`default:verify`, order 10) that today shares order 10 with `default:architecture-refresh` and does **not** trip the collision test — a live proof of the per-phase claim. Tie-break: `_manifest_validation.py:399-409` builds `sortable` in list order and calls `sortable.sort(key=lambda pair: pair[0])` — stable, so list position wins; `_check_ascending_order` (`:443`) uses `order < max_order`, so equal orders are *not* flagged. `archive-plan runs last` confirmed at `_manifest_core.py:289-294`. |
| D1 | Banded allocation contract with reserved gaps + `reads`/`destroys` keys | Contract documented with insertion room in every band; ordering key can express `reads`/`destroys` | Yes | Yes | Mostly — see below | Mostly — see below | New `marketplace/bundles/plan-marshall/skills/extension-api/standards/finalize-step-order-bands.md` (108 lines): six bands, owners, reserved gaps, collision rule, `reads`/`destroys`. `ext-point-finalize-step.md:49-50` adds both keys to the frontmatter contract table; `:262` cross-links the band doc. `archive-plan.md:7-10` → `order: 1100` + `destroys: [plan-directory]`; `branch-cleanup.md:7-9` → `destroys: [worktree]`. Terminal slot 1000–1099 was empty at landing and is now occupied by `emit-landing` (order 1000, PR #1215) — the reservation worked. Cross-epic citation present (`finalize-step-order-bands.md:11-18` links `source-edit-pushability.md` and `ext-point-finalize-step.md` § Implementor Frontmatter). |
| D2 | Resolve the live same-phase collision, intended order established first | Two steps have distinct orders and the intended order was established first | Yes | Yes | Yes | Yes | `finalize-step-security-audit.md:9` → `order: 9`; `architecture-refresh.md:7` → `order: 10`; `push.md:7` → `order: 11`. The intended order is **pre-existing documentation**, not invented: the pre-change `phase-6-finalize/SKILL.md` line already read "`architecture-refresh` (9, derived-state — sorts LAST in the settle band …)" (visible in the `308528d6` diff `-` side), and `find_implementors` sorts `(order, name)` (`extension_discovery.py:1383`), so at equal order 9 `architecture-refresh` sorted *before* `security-audit` — the documented intent inverted. Executed sort at HEAD confirms `security-audit (9) → architecture-refresh (10) → push (11)`; architecture-refresh is the highest order below `push`, i.e. last in the settle band. |
| D3 | A collision check that FAILS, seen to fire on the live collision before D2 | Verified to fire on the live collision BEFORE D2 fixed it | Yes | Yes | Yes | Yes | `test_finalize_orchestration_routing.py:847` `TestNoTwoFinalizeStepsShareAnOrder` — extends the existing step-discovery file (no competing checker), derives its population from `find_implementors(_EXT_POINT)`, carries an anti-vacuity `test_discovery_is_non_empty`. 64 passed at HEAD. **Mutation-reproduced**: restoring `architecture-refresh` to order 9 makes it fail with the exact message the report preserves. |

**D1 — the one soft spot.** The contract's *Settle* band (1–69) is stated to have "guaranteed insertion
room … in the major-step gaps above it" (`finalize-step-order-bands.md:37`), and the reserved-gaps
bullet (`:48-52`) names those gaps as 12–19, 23–29, 31–39, 41–61, 63–69 — **every one of which is above
`push` (11)**. A new *pre-push* step (the sub-region that actually carries the `mutates_source`
settle-before-push contract) therefore has only the two unoccupied integers 1–2, and the doc's own
remedy sentence — "a new pre-push step that cannot fit is what the reserved major-step gaps … are for"
— points at ranges that structurally cannot hold a pre-push step. D1's literal done-when ("insertion
room inside every band") holds for the six named bands, but the sub-band the plan's own § C is about
still has no guaranteed gap. Recorded as G2, not as a D1 failure.

**D1 — `reads` is a capability nothing exercises.** `grep -rn '^reads:'` over `marketplace/` and
`.claude/` returns **zero** declarations tree-wide, and no code path anywhere reads either key:
`_IMPLEMENTOR_FRONTMATTER_KEYS` (`extension_discovery.py:889-897`) does not include `reads`/`destroys`,
so they never enter an implementor record, and no test asserts the two canonical `destroys`
declarations the contract anchors its vocabulary on. Plan 300 explicitly assigns *application* of the
keys to plan 302 ("this plan adds the … ordering keys § D calls for; 302 applies them"), so this is
not a D1 failure — but 302 landed (PR #1215) without applying them, so the seam is still open.
Recorded as G1 and G3.

## Report accuracy

Checked against the tree: every order value in the D0 population table; the collision pair; the
contiguity of 998→999→1000; the cross-phase pair; the `archive-plan runs last` source citation; the
D1 file list and the `destroys` declarations; the D2 intended-order claim and its "collision was
masking a real ordering bug" analysis; every row of the 11-stale-restatement disposition table; both
"correctly excluded" fixtures; both residue items; and the ext-point Current-Implementations table.

One contradiction found:

- **"11 stale order restatements" is not what the report's own table enumerates.** § Findings →
  Pre-PR verification sub-agent states "11 stale order restatements survived" and "Disposition — all
  11 fixed", but the eight-row table beneath it enumerates **13** statements once its own
  multiplicities are summed (`×2 + ×2 + 1 + 1 + 1 + ×4 + 1 + 1`). The 13 fixes are all real and all
  present in the landed diff — the count is wrong, not the work. Recorded as G5.

Everything else checks out. Specifically confirmed rather than assumed:

- The D0 table's 25 rows equal today's 26-row live population minus `default:emit-landing`, which
  `git log -- …/emit-landing.md` shows was added by PR #1215 (plan 302) — **superseded-by-later-plan,
  not drift**.
- The report's note that the D0 cross-phase order-10 pair (`canonical_verify` / `push`) no longer
  holds after D2 is literally true; a *different* cross-phase order-10 coincidence
  (`canonical_verify` / `architecture-refresh`) took its place and correctly does not trip the
  collision check.
- The two "correctly excluded" exclusions are justified: `test_cmd_quality_phases.py:337,345,379,386`
  is a `monkeypatch.setattr(_discover_steps_for_phase, …)` literal whose other values are already
  synthetic (`lessons-capture` 50, `record-metrics` 990); `test_steps_sort.py:33-38` `_FAKE_ORDER` is
  a table feeding a monkeypatched `_resolve_step_order` (`ci-verify` 30, `archive-plan` 50).
- The `test_finalize_step_print_phase_breakdown.py` pre-existing-stale-docstring fix landed and is
  correct at HEAD (`:97-103`, now naming 998 / 1000-1099 / 1100).
- `19459 passed, 14 skipped` and the "green CI on head `83d422b`" claim were **not** re-derived (see
  below).

## Out-of-scope compliance

Clean. The landed diff's 34 files are all inside the declared Expected surface or a direct consequence
of the two renumbers:

- The four out-of-scope boundaries were respected — no terminal-emission step, no facts payload, no
  totals-sampling change, no consumer-repository renumber. `emit-landing.md` entered the tree only at
  PR #1215.
- The "not established whether any consumer pins an order" boundary was honoured as a recorded
  non-finding rather than an assumption, exactly as the Claim-labels table demanded.
- No undeclared collateral: the two files outside the named surface —
  `test/plan-marshall/platform-runtime/test_session_binding.py` (`order: 1000` → `1100` in a
  docstring) and `manage-terminal-title/standards/terminal-title-architecture.md` (3 lines) — are
  both pure consequences of the `archive-plan` renumber.
- The plan-file move (`300-….md` → `300-…/plan.md`) and the addition of
  `302-….md` are the operator-directed split the report declares up front.

## Residue carried forward

| Residue in report-01.md | Status in today's tree |
|---|---|
| **Landing delegated** — auto-merge armed, merge queue to land PR #1211 | **Closed.** `308528d6` is on `main`. |
| **302 authored, not executed** | **Closed.** `doc/plans/truthful-signals/302-…/` is a plan directory and its work landed as PR #1215 (`emit-landing.md`, order 1000, occupying the reserved band). |
| **Two pre-existing stale fixture comments** in `test_manage_execution_manifest_validate.py` `_ORDER_RESOLVABLE_CANDIDATES` | **Still open.** `:431` `'architecture-refresh',  # order 25` (real 10) and `:432` `'finalize-step-preference-emitter',  # order 61` (real 992). Confirmed pre-existing: the `308528d6` diff touches only the `push` and `archive-plan` lines of that list. Recorded as G6, together with a third instance of the same class found during the sweep. |
| **Local plugin-cache sync neither performed nor owed** | Correct per CLAUDE.md's standalone-lane carve-out; nothing to check in the tree. |

## What could NOT be verified

- **The D3-fired-before-D2 *ordering*.** The pre-squash branch commits `feba50d` and `08e8da6` are
  unreachable (`git cat-file -t` → not a valid object name) and the branch
  `claude/operator-report-evidence-surface-qv6kyn` is gone, so the historical sequence cannot be
  replayed. The *substance* of the claim was re-established equivalently: recreating the live
  collision by mutation makes the shipped check fail with the identical assertion text the report
  preserves, so the fixture and the check are demonstrably matched.
- **`19459 passed, 14 skipped` and the CI-green claim on head `83d422b`.** Not re-derived — a
  whole-tree `./pw verify` was out of proportion for this check, and the PR's check runs are not
  readable from the tree. The one test file the plan added was run and passes.
- **The plan's mandated cold read of the contract.** The Verification section required the Step 6
  sub-agent to be handed the new contract with no other context and asked where a third-party step
  running after the merge but before the archive should be numbered; report-01.md's § Pre-PR
  verification sub-agent does not record that question or its answer. I answered it myself against
  the doc alone — `finalize-step-order-bands.md:39` (Post-merge operational, 71–899,
  project-local/third-party) for an acting step, `:40` (Post-run review, 900–999) for a
  backward-looking one — so the bands *are* usable and the outcome is a pass; only the evidence that
  the mandated cold read happened is missing. Not raised as a gap, because no change follows from it.
- **Whether any consumer repository pins an order D1 would break.** Unreadable from this clone, as the
  plan and the report both state. Left explicitly unresolved rather than assumed either way.
