# Run report — 300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/operator-report-evidence-surface-qv6kyn (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress (plan split; D0 done, D1–D3 pending)_

## Plan split (operator decision)

Mid-run, the operator reversed the plan's original "no split" and directed a split. The seam was cut at
its safest joint:

- **This plan (300)** is narrowed to **Phase 1 — the space**: D0 (gate, done), D1 (banded allocation
  contract with reserved gaps + "reads X"/"destroys X" ordering keys), D2 (resolve the order-9
  collision), D3 (collision check). It reserves the terminal slot the follow-up needs.
- **New plan (302)** — `doc/plans/truthful-signals/302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains.md`
  — owns **Phases 2 & 3 (the emission + the payload)**, former D4–D8: the dedicated terminal step, its
  orchestrator-only composition, the report↔inbox delta, the machine-readable facts, and the
  drain-completeness check. 302 serializes after 300 (it needs 300's reserved slot).

Rationale for the seam: the space is a genuinely separable foundation, whereas the emission and its
facts payload were kept together in 302 — a terminal step emitting prose at the right time, or facts at
the wrong time, is exactly the half-fix the original "no split" rationale warned against. 300's plan.md
was narrowed (title, Goal, Deliverables, Out-of-scope, Expected surface, Claim labels, Verification,
Notes) and 302 authored in the same plan shape.

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — read from bundle path
- `pm-plugin-development:plugin-script-architecture` (always) — read from bundle path
- `plan-marshall:ref-workflow-architecture` (workflow docs / dispatch topology) — read from bundle path
- `plan-marshall:persona-implementer` (production code work identity) — read from bundle path
- `pm-dev-python:python-core` (Python production code) — read from bundle path
- `pm-dev-python:pytest-testing` (Python tests) — read from bundle path
- `pm-plugin-development:plugin-architecture`, `pm-documents:ref-asciidoc` — loaded on-demand during implementation

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Deliverables

### D0 — GATE: derive population + semantics (from composer source)

**Status: derived (mutates nothing).** All facts re-derived from the composer source, not
inherited from the plan text.

**The composer / ordering machinery (source, not output):**

- `manage-execution-manifest/scripts/_manifest_validation.py::_sort_steps_by_frontmatter_order` is the
  single sort choke-point. `manage-config/scripts/_cmd_steps_sort.py` and the compose entry
  (`manage-execution-manifest.py::cmd_compose`, line ~2044) both reuse it.
- The authoritative `order` for a step lives in **that step doc's own frontmatter**, read by
  `_read_frontmatter_order` / `_resolve_step_order`. `_manifest_core.DEFAULT_PHASE_6_STEPS` and the
  SKILL.md "Built-in Step Dispatch Table" are restatements pinned in lock-step by
  `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py`.
- Discovery is `extension_discovery.find_implementors(ext_point)` — the SOLE discovery path. It
  filters by `implements: {ext_point}` and returns records sorted by `(order, name)`.

**Semantics answer 1 — is the space per-phase or global? → PER-PHASE, and the ext-point IS the phase
discriminator.** `_sort_steps_by_frontmatter_order` / `check_emitted_steps_ascending_order` are
applied to `phase_6.steps` ONLY; phase-5 `verification_steps` is explicitly NOT sorted by frontmatter
order (`_cmd_steps_sort.py` `_TARGET_PHASE = 'phase-6-finalize'`, and the note "phase-5-execute is out
of scope … carries no per-step frontmatter-order doc"). `find_implementors(FINALIZE_STEP_EXT_POINT)`
returns finalize steps only — a phase-5 doc declaring the *verify* ext-point is scanned but filtered
out. So the order space a collision check must police is exactly the finalize-step implementor set;
two orders in different ext-points never meet.

**Semantics answer 2 — tie-break for equal orders → LIST POSITION (Python stable sort).**
`_sort_steps_by_frontmatter_order` builds `sortable` in list-position order and `sortable.sort(key=order)`
is stable, so equal-order entries keep their input sequence (defaults: `DEFAULT_PHASE_6_STEPS` order;
marshal.json: on-disk keyed-map order). This tie-break is **not a declared contract** — it is an
emergent property of the stable sort. `check_emitted_steps_ascending_order` treats equal orders as
"non-decreasing" and so does **not** flag a collision — the gap D3 closes.

**Population — the finalize-step `order` declarations (re-derived by enumeration, not sampled):**

| order | step | source |
|---|---|---|
| 3 | finalize-step-sync-baseline | built-in (phase-6 standards) |
| 4 | finalize-step-lessons-housekeeping | project (`.claude/skills`) |
| 5 | pre-push-quality-gate | built-in |
| 6 | finalize-step-plugin-doctor | project |
| 7 | pre-submission-self-review | built-in (workflow) |
| 8 | finalize-step-simplify | built-in |
| **9** | **architecture-refresh** | **built-in — COLLISION** |
| **9** | **finalize-step-security-audit** | **built-in — COLLISION** |
| 10 | push | built-in |
| 20 | create-pr | built-in (workflow) |
| 21 | finalize-step-era-stamp-fill | project |
| 22 | ci-verify | built-in |
| 30 | automatic-review | bundle skill (default_on → built-in) |
| 40 | sonar-roundtrip | built-in (workflow) |
| 62 | adr-propose | built-in (workflow) |
| 70 | branch-cleanup | built-in (merge gate) |
| 81 | finalize-step-deploy-target | project |
| 85 | finalize-step-sync-plugin-cache | project |
| 990 | finalize-step-review-retrospective | project |
| 991 | lessons-capture | built-in (workflow, post_run_review) |
| 992 | finalize-step-preference-emitter | built-in (post_run_review) |
| 995 | plan-retrospective | bundle skill (opt-in) |
| 998 | record-metrics | built-in (post_run_review) |
| 999 | finalize-step-print-phase-breakdown | built-in |
| 1000 | archive-plan | built-in (LAST — moves plan dir) |

**Confirmed by enumeration:**

1. **The only same-phase collision is `order: 9`** — `architecture-refresh` and
   `finalize-step-security-audit`, both `implements: ext-point-finalize-step`, both built-in phase-6
   standards docs. (Plan claim "two of our own steps share it" ✓.) Every other order is distinct.
2. **The terminal region 998→999→1000 is contiguous** — `record-metrics`/`print-phase-breakdown`/`archive-plan`.
   No integer slot exists between the last reporting step and `archive-plan`. A terminal step (D4) needs
   D1 to open one.
3. **The cross-phase duplicate pair that is NOT a collision** = `phase-5-execute/standards/canonical_verify.md`
   (order **10**, declares the *verify* ext-point) and `phase-6-finalize/standards/push.md` (order **10**,
   declares the *finalize* ext-point). They never share a `find_implementors` population → not a
   collision. This is the sole evidence the space is per-phase (the ext-point). (Plan warns: do NOT
   "fix" it ✓.)

**`archive-plan` runs last** (HYPOTHESIS → confirmed from source): `_manifest_core.py` comment lines
276-280 — "`archive-plan` (1000) is ordered last … It runs last because it moves the plan directory
out from under every later reader." ✓

**Compose-time availability of the orchestration signal (D5 dependency):** `cmd_compose`'s argument
surface today is `plan_id / change_type / scope_estimate / track / commit_and_push / phase_{5,6}_steps`
— it has **no** `source_id` / orchestration awareness. The single sanctioned detector is
`_orchestrator_inbox.classify_source_id(source_id)`, which classifies `request.md`'s `source_id`.
`source_id` is written by **phase-1-init** into `request.md`, so it IS available at phase-4 compose
time (the composer runs with a resolvable `plan_id` → plan dir → `request.md`). ⇒ **D5 can be a
compose-time drop** (read `source_id`, classify, exclude the terminal step when not `orchestrated`),
observable in the compose result — not a runtime no-op. The existing finalize steps resolve
orchestration at *runtime* (phase-6 SKILL.md `a0` block); D5 moves the decision earlier for this one
step.

**Consumer-repository declarations (Out-of-scope check):** every project-local `order` declaration
examined lives in THIS tree (`.claude/skills/finalize-step-*`). Whether any *consumer* repo pins an
order is NOT established from this clone (consumer repos not readable here) — recorded, not assumed.

**Naming drift noted:** the plan's "Expected surface" names `marshall-orchestrator/scripts/orchestrator.py`;
the actual path is `plan-orchestrator/…` (plan 120 renamed it). Working against the real path.

### D1 — banded allocation contract with reserved gaps (committed `feba50d`)

**Status: implemented; quality gate green; full test suite verifying.**

- **New contract doc** `extension-api/standards/finalize-step-order-bands.md` — the bands (settle 1–69,
  merge gate 70, post-merge operational 71–899, post-run review 900–999, **reserved terminal-emission
  band 1000–1099**, terminus 1100), their reserved insertion gaps, the ranges reserved for
  project-local/third-party vs the shared bundle, the collision rule (no two same-ext-point steps share
  an order), and the `reads`/`destroys` declared facts. Cites `code-intelligence-substrate` plan 050's
  post-run band contract without restating the P1/P2 discriminator or the mutual-exclusion rule.
- **Reserved terminal slot** (300 Verification requirement) — `archive-plan` moved `1000 → 1100`, opening
  the 1000–1099 band plan 302's terminal step occupies. Existing steps stayed in place (their bands
  already carry free insertion room), so the renumber is the single move the reserved slot requires.
- **`reads`/`destroys` ordering keys** — added to the ext-point frontmatter contract table, with concrete
  declarations: `archive-plan` `destroys: [plan-directory]`, `branch-cleanup` `destroys: [worktree]`.
- **Restatement sweep** — every `archive-plan 1000` reference updated across the composer
  (`_manifest_core.py`, `manage-execution-manifest.py`, `SKILL.md`, `decision-rules.md`), the ext-point
  Current-Implementations table, `terminal-title-architecture.md`, and 7 test files. One was a hard
  assertion (`test_cmd_skill_resolution.py` `== 1000 → 1100`); one was a **pre-existing stale docstring**
  (`test_finalize_step_print_phase_breakdown.py` said `order: 995`/`record-metrics 990` — both already
  wrong) which the sweep also corrected.
- Quality gate: `ruff` all-passed, `mypy` clean (580 files), SPDX passed. Full `./pw verify plan-marshall`
  test run in progress at commit time.

### D2 / D3 — collision fix + check

**Status: pending (next).** The load-bearing order is preserved: D3 (extend
`test_finalize_orchestration_routing.py` with the order-uniqueness check) must be SEEN to fire on the
live `order: 9` collision (`architecture-refresh` / `finalize-step-security-audit`) before D2 resolves
it.

## Build gate

_(pending)_

## Findings

_(pending)_

## Reviewer participation

_(pending)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

- **300 D1–D3 not yet executed in this run.** D0 (the gate) is derived and recorded; D1 (banded
  contract), D2 (collision fix), D3 (collision check) remain. The load-bearing order is preserved: D3
  must be SEEN to fire on the live order-9 collision (`architecture-refresh` / `finalize-step-security-audit`)
  before D2 resolves it.
- **302 authored, not executed.** The follow-up plan is committed to the epic directory as a single
  plan file, ready to be picked up as its own run after 300 lands.
- No PR opened this run — the split restructuring landed on the branch; the 300 deliverables (D1–D3) are
  the next work, and 302 is a separate future run.
