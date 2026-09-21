# Landing Analysis: PLAN-08 — Permission skills through the registry

epic: multiplattform
workstream: WS-01
pr: #1393 (https://github.com/cuioss/plan-marshall/pull/1393)

> Landing record for one shipped plan. Lives at `landings/PLAN-08.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Drained from the inbox, not from a paste.** The source was
`inbox/permission-skills-through-the-registry-001.md` (`kind: landing`, `lifecycle: live`,
`revision: 0`, envelope v1, valid). This is the **second** end-to-end OpenCode-lane inbox
landing, after PLAN-05.

## Deliverable Fidelity vs Spec

Every verdict below was re-derived from the merged tree at `7b0ad0850`, not read off the
message or the PR body.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — crossing inventory, written into **the PR body and the inbox message** before any code change | **shipped-modified** | The enumeration exists and is substantive (9 direct imports, 6 DSL render + 4 parse sites, each with an intent phrase), and it IS in the PR body. But it was **committed as a repo-root file `CROSSING-INVENTORY.md`**, and the **inbox message carries none of it** — the message is a bare `landing-facts` block. Half of the stated done-condition is unmet, and an undeclared artifact landed on `main`. |
| **D2** — semantic vocabulary; no DSL string in any op argument or return | **shipped-modified (disclosed)** | `runtime_base.py` +142, `_claude_runtime_impl.py` +185, `opencode_runtime.py` +102, `platform_runtime.py` +62, `contract.md` +30. The PR body self-discloses a **sixth intent kind, `skill`, added beyond the five approved** in the spec, for `ensure-steps` return fidelity. Disclosed rather than smuggled — recorded here as a scope extension, not a defect. |
| **D3** — skills resolve runtime through the registry; no `claude_runtime` import | **shipped-as-specified** | Re-derived on `main`: a `claude_runtime` search over `permission_common.py`, `permission_doctor.py` and `permission_fix.py` returns **one hit, a docstring line** (`permission_common.py:16`) that asserts the absence. The `sys.path` parent-walk is gone. `ensure_default_permissions` now takes `settings`/`settings_path` and returns semantic ids, with grammar rendered inside the runtime — the settings *mapping* no longer crosses. |
| **D4** — re-run each coupling-inventory row's detection, report verdicts in **the PR body and the inbox message** | **shipped-modified** | The PR body carries a D4 section reporting both §B rows as "no Claude-runtime import". The **inbox message carries no D4 rows at all**, so the same half of the done-condition is unmet as in D1. The orchestrator re-derived independently rather than accepting the report — see Reconciliation Actions. |

**The `deliverables_done=4` claim is upheld in substance and qualified in form**: all four
deliverables produced their work product, but D1 and D4 each satisfied only the PR-body half
of a two-place done-condition. The inbox half was specified precisely so the orchestrator
could reconcile without reading the PR, and it did not arrive.

### Claims settled by the run

Both of the spec's HYPOTHESIS claims stood at `unverifiable | checked_at: 2cd1a19c`. The
run settles the first and leaves the second unaddressed:

- *"Every intent behind a rendered DSL string in `permission_fix.py` is recoverable by
  reading the code."* — **corroborated.** D1 stated an intent phrase for every site and the
  plan did not hit its HALT condition. This was the plan's own premise, and it held.
- *"No general skill script outside the three named binds `claude_runtime` for permission
  work."* — **still unverified.** No evidence in the PR body or the report that the
  classification sweep was re-run. Carried forward as a Watch.

No verdict was stamped onto the spec: PLAN-08 is terminal, so its verdict field gates
nothing, and the settlement is recorded here instead.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown` — the expected OpenCode-lane gap
  (`record-metrics` has no analogue in this lane). `inbox landing-check` therefore returned
  `complete: false, missing_keys: [total_tokens]`, which is the honest encoding, not a defect.
- **Duration:** not reported by the lane. Message filed `2026-09-03T22:16:32Z`.
- **Steps** (parsed by last-colon split; all six elements are bare, so no element
  discriminates the split direction here): `step-4-implement:done`, `step-5-build-gate:done`,
  `step-6-verifier:clear`, `step-7-pr:done`, `step-8-merge:done`, `step-9-self-check:done`.
- **Anomaly — the run report contradicts its own landing.**
  `.plan/local/oc-plans/multiplattform/080-permission-skills-through-the-registry/report.md`
  still reads `D2 — NOT STARTED`, `D4 — NOT STARTED`, `D1 — DONE, not committed`, Step 8
  "in progress", Step 10 "pending", and a Residue section listing work that demonstrably
  shipped. The report was never finalized past its mid-run snapshot even though
  `step-9-self-check` reports `done`. The **merged tree is authoritative** and the report is
  stale; nothing in this record rests on it.

## Routing and Merge Behavior

- **Review:** CodeRabbit (6 findings) and cuioss-review-bot (1 inline) — all 7 threads
  resolved before merge. Sourcery is optional per the standing operator policy. The
  cuioss-review-bot finding was substantive: `add`/`ensure` mishandled multi-rule intents
  (a `bundle` intent expands to both `Skill(x:*)` and `SlashCommand(/x:*)`), fixed to append
  only missing rules with two guard tests.
- **CI/merge:** `verify` green on the merged head; merged via `7b0ad0850`, `state: merged`,
  `merge_commit_sha` corroborated against `main` through the CI abstraction and `git log`.
- **No surface collision materialized.** PLAN-08 ran solo under `parallelization_scope: 1`.
  The ledger's pre-measured overlaps with PLAN-09 (6 paths) and PLAN-14 (3 paths) were never
  exercised and remain live predictions for the WS-01 chain.
- **Declared-surface fidelity:** the landing touched `_claude_runtime_impl.py`, which the
  ordered-queue Surface cell omits but the **spec declares** (`## Expected Surface`, the D2
  Claude-side row) — an abbreviation in the rendered cell, not an under-declaration.
  Three declared paths went **untouched**: `tools-permission-doctor/SKILL.md`,
  `tools-permission-fix/scripts/permission_fix.py`, and
  `test/plan-marshall/tools-permission-fix/**`. Over-declaration is the safe direction for
  the gate and needs no correction.
  The one genuine under-declaration is `CROSSING-INVENTORY.md` at the repository root.

## Reconciliation Actions

- [x] row `status` → `landed` — `orchestrator queue --transition PLAN-08 --status landed`
  (this epic's terminal vocabulary; the other eight terminal rows all read `landed`)
- [x] row `pr` stamped `#1393` — `orchestrator queue --set-row`
- [x] row `landing` stamped `landings/PLAN-08.md` — `orchestrator queue --set-row`
- [x] row `plan_marshall_plan_id` stamped `n/a` — OpenCode lane, no plan-marshall plan id,
  consistent with PLAN-04/05/13/16/19
- [x] **Coupling-inventory §B row retired on re-derivation, not on the plan's say-so** — the
  `permission_common.py` / `permission_fix.py` direct-binding row. Detection re-run by the
  orchestrator over the merged tree: no direct `claude_runtime` import in either file, and
  the settings-mapping parameter no longer crosses. Retired.
  ⚠️ **One half of that row was stale before the plan ever ran**: it named
  `permission_fix.py` as bound by direct import, and a check of the pre-merge parent
  (`7b0ad0850^1`) shows that file had **no** `claude_runtime` import already. The retirement
  is still correct — the test is what the tree shows now — but the row was over-claiming.
- [x] **Coupling-inventory §B DSL-rendering row KEPT, unnarrowed** — the `permission_fix.py`
  render/parse residue row. Its detection still finds **every symbol it names**:
  `EXECUTOR_PERMISSION` (:66), `OVERLY_BROAD_PYTHON` (:67), `TIMESTAMP_PATTERN` (:82),
  `DATE_PATTERN` (:83), `normalize_path_perm` (:91), `is_individual_script_permission`, and
  the `Skill(…)` / `SlashCommand(…)` wildcard generators (:494, :496, :780, :789, :798).
  ⛔ **`permission_fix.py` was not touched by this landing at all** — it is absent from the
  merge diff. A row is retired because the coupling is gone from the tree, never because a
  plan claiming it merged; this one is entirely intact and is not narrowed.
- [x] epic.md narrative reconciled; Open Defects and Watches updated below
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] `resume_anchor` updated

## Follow-Ups

- **`CROSSING-INVENTORY.md` sits at the repository root on `main`** (4,493 bytes, tracked).
  It is a plan working artifact — its own first line reads "Crossing Inventory — PLAN-08" —
  and the spec asked for it in the PR body and the inbox message, not in the tree. It is
  undeclared in `## Expected Surface`. → **Open Defect** (see `epic.md`). Not folded into any
  staged plan: no staged spec declares the repository root, and this is a one-file removal
  rather than a deliverable.
- **The inbox half of D1 and D4 was skipped.** The landing message is a bare facts block. →
  **Open Defect**, because it is a *lane contract* gap rather than a one-off: RUNBOOK Step 10
  produces the facts block, and nothing in the lane carries a spec's "report X in the inbox
  message" obligation into that step. The next spec that asks for a reported enumeration will
  lose it the same way.
- **`orchestrator queue --transition` accepts an arbitrary status token.** Observed directly:
  a transition to `bogus` was accepted with `status: success` and had to be corrected by a
  second call. The vocabulary may be open by design (`resume-summary` renders a residual line
  for unrecognised statuses), but nothing rejects an obvious typo, and a mistyped status
  silently removes a plan from both the live queue and the terminal set. → **Open Defect**,
  out of this epic's scope — it belongs to the same `plan-orchestrator/scripts/orchestrator.py`
  territory as the recorded `set-verdict` off-by-one, and must not be folded into a plan here.
- **The unclassified-sweep hypothesis** (no other general skill script binds `claude_runtime`
  for permission work) was never re-derived. → **Watch**.
- **The run report is stale against its own landing.** Not an epic deliverable and outside the
  ledger write-boundary; recorded here so the next reader does not trust it. The generalizable
  point is the one PLAN-19 already taught: a stale record propagates into whatever reads it next.
