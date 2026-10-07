# Landing Analysis: PLAN-15 — Repo scoping design

epic: multiplattform
workstream: WS-02
pr: #1420 (https://github.com/cuioss/plan-marshall/pull/1420)

> Landing record for one shipped plan. Lives at `landings/PLAN-15.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/repo-scoping-design-001.md`. **This is the first plan in this epic to have
run CONCURRENTLY with a sibling epic's plan** (`test-quality` PLAN-110), and the concurrency
verdict deserves its own scrutiny below.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — the repo-scope ADR | **shipped-as-specified** | `doc/adr/..._tree_declares_itself_at_the_reference_site.adoc`, +262 lines — ADR-020. Its title states the conclusion: the tree declares itself at the reference site. |
| **D2 / D3** — reference-site declarations | **shipped** | Six files carry the declarations: `_manifest_decide.py`, `_preference_admissibility.py`, `manage-metrics/standards/data-format.md`, `finalize-step-preference-emitter.md`, `plan-retrospective/scripts/analyze-logs.py`, `frontmatter-standards.md`. |

`deliverables_done=3/3` is upheld. The work landed.

## ⛔ The declared surface was WRONG, and this is the finding that matters

PLAN-15's `## Expected Surface` declared exactly **two** entries — `doc/adr/` and
`marketplace/targets/component_targets.py`. The landing touched **seven** files, of which
**six are undeclared**, and it did **not** touch `component_targets.py` at all:

| Touched file | Declared? |
|---|:--:|
| `doc/adr/…tree_declares_itself….adoc` | ✅ |
| `manage-execution-manifest/scripts/_manifest_decide.py` | ❌ |
| `manage-execution-manifest/scripts/_preference_admissibility.py` | ❌ |
| `manage-metrics/standards/data-format.md` | ❌ |
| `…/standards/finalize-step-preference-emitter.md` | ❌ |
| `plan-retrospective/scripts/analyze-logs.py` | ❌ |
| `plugin-architecture/references/frontmatter-standards.md` | ❌ |
| `marketplace/targets/component_targets.py` | declared, **untouched** |

**This directly undercuts the reasoning that selected PLAN-15 for emission.** It was chosen
precisely *because* its declared surface was two paths that no running plan touched — the one
candidate that survived the by-hand containment sweep. That verdict was sound **given its
inputs** and wrong **in fact**, because the declaration under-described the plan by a factor of
three.

⚠️ **The epic already recorded this exact class and it has now recurred.** The PLAN-04 landing
established that *"the declared surface is still a spec-authored quantity, so the gate is only
as honest as the declarations… the parser is no longer the weak link; **under-declaration
is.**"* PLAN-04 touched one undeclared file. PLAN-15 touched six. The lesson was recorded and
did not prevent the repeat.

### The concurrency was safe — but by luck, not by the gate

Checked after the fact against both plans that were live during the run:

- **`test-quality` PLAN-110** — test-only plus `test/README.md`. None of the six undeclared
  files is a test file. **No collision.**
- **`unreviewed-merge-gate-holes`** — its `references.json` `affected_files` was read directly:
  none of the six appears. **No collision.** ⚠️ It was close: that plan collides with PLAN-12 on
  `manage-metrics/SKILL.md`, and PLAN-15 edited `manage-metrics/standards/data-format.md` —
  the same skill, a different file.

⛔ **Neither clean result was predicted by the gate**, because the gate never saw the six paths.
A one-file difference inside `manage-metrics/` separated this landing from a real concurrent
collision.

### The order-inversion obligation is now BINDING, not moot

The anchor set the test: *did PLAN-15 run past D1?* It did. Two of the six undeclared files are
the contested ones the sequencing note named:

- **`manage-metrics/standards/data-format.md`** — **PLAN-12's D3**, and a three-way contested
  file (PLAN-15 / PLAN-12 / PLAN-07).
- **`plugin-architecture/references/frontmatter-standards.md`** — **PLAN-06's**, named in the
  spec's own "Overlaps with PLAN-06 … if D3 lands there. Sequence." It landed there.

So PLAN-07, PLAN-12 **and PLAN-06** must re-derive over these files rather than trust their hit
lists. That is one plan more than the inversion note anticipated.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown` → `complete: false`. **Fifth consecutive**
  landing. The message's own Residue section states the reasoning correctly (routed to
  `unknown`, never `n/a`), which is the honest encoding.
- **A per-commit gate deviation was self-disclosed** for `e169cae6e` and recorded in the run
  report. Disclosed rather than buried — the right handling.

## Routing and Merge Behavior

- **Review:** CodeRabbit — 3 findings, all handled (2 fixed, 1 rejected with reason, escalated
  to follow-up issue **#1421**: a machine-checkable lock-step check for the dispatch-boundary
  contract). Sourcery rate-limited (optional, disclosed) — fifth consecutive honest handling.
- **CI/merge:** squash-merged as `713f9017`, corroborated via the CI abstraction and against
  `origin/main`. Branch `chore/repo-scoping-design` — canonical prefix, correct for an
  ADR-and-declarations change.
- **Two RUNBOOK contract edits applied directly** (`--timeout 1800` guidance for `verify`; the
  worktree executor-provisioning note). ✅ Correct call: the runbook is host-local and
  git-ignored, so there is no tracked file to PR against. ⚠️ It also means these two
  improvements exist on **one machine only** — the same standing exposure as the unrecorded
  reviewer-policy change.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` → `#1420`; `landing` → `landings/PLAN-15.md`;
      `plan_marshall_plan_id` → `n/a`
- [x] New Open Defect: PLAN-15's declared surface under-described the plan 2-vs-7 (below)
- [x] Queue annotation extended — the re-derive obligation now binds **PLAN-06** as well as
      PLAN-07 and PLAN-12, and names the two specific contested files that were actually edited
- [x] PLAN-11's design gate re-read (below)
- [x] START-HERE and Ordered Queue blocks regenerated; `resume_anchor` updated
- [x] Message archived to `inbox/archive/repo-scoping-design/`

## Follow-Ups

- ⛔ **Under-declaration is now a measured, repeating pattern, not an anecdote** — PLAN-04 (1
  undeclared file), PLAN-15 (6). Both landed safely; neither safety was predicted. → **Open
  Defect**. The fix is not another warning in the ledger: the epic already carries one and it
  did not bind. It needs a mechanical check — comparing a landing's realized footprint against
  its declared surface at drain time, which `manage-references` already computes as a
  three-way reconciliation.
- ⭐ **PLAN-11's design gate is DISCHARGED.** PLAN-15's spec said it "blocks PLAN-11
  conditionally — if D1 concludes repo-scope needs its own axis, PLAN-11's design changes."
  ADR-020's title states the conclusion reached: *the tree declares itself at the reference
  site* — a reference-site declaration pattern, **not** a new scoping axis. So PLAN-11's D1
  design stands as staged and needs no rework, and it no longer has to record the
  "target-scoping only" assumption its spec required if it ran first.
  ⚠️ PLAN-11 remains blocked on `test/marketplace/targets/**` ⊂ PLAN-110's `test/marketplace/`
  for as long as PLAN-110 runs — a different blocker, unaffected by this discharge.
- **Follow-up issue #1421 is outside this epic** and is not folded into any plan here.
