# Run report — 300-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/operator-report-evidence-surface-qv6kyn (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

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

_(pending)_
