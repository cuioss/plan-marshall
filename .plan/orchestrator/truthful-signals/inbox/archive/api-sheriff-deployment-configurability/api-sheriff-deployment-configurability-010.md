envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=finding
created=2026-09-15T08:26:53Z

component=plan-marshall:phase-6-finalize
category=bug

# emit-landing's `orchestrated` verdict has no persisted carrier: it is resolved inside the lessons-capture gate, carried inline across ~9 steps, and an empty `epic` reads as "not orchestrated"

⛔ **ROUTED FROM API-SHERIFF'S EPIC LEDGER — the defect is plan-marshall's, the cost is paid in a consuming
repo.** Four Open Defects entries from the `deployment-configurability` epic (`cuioss/API-Sheriff`),
recording SIX observations of one channel failing, 2026-09-02 → 2026-09-11. Filed here by operator
direction on 2026-09-15 and retired from that ledger in the same act. Verbatim entries below the
verification block, oldest first.

## What the epic measured (six observations, three distinct modes)

| Plan | Landed | `emit-landing` | Mode |
|---|---|---|---|
| PLAN-02 | 2026-09-02 | `outcome=skipped -- not orchestrated` | (a) ran, wrong verdict |
| PLAN-10 | 2026-09-04 | ✅ delivered | — |
| PLAN-15 | 2026-09-05 | ✅ delivered | — |
| PLAN-03 | 2026-09-07 | `outcome=skipped` | (a) |
| PLAN-07 | 2026-09-08 | **absent from the manifest** (`grep -c 'emit-landing' work.log` = 0) | (b) |
| PLAN-08, PLAN-17 | 2026-09-10/11 | both `outcome=skipped` | (a) |

Channel record: **3 delivered / 5 skipped-at-runtime / 1 absent-from-manifest / 1 correct abstention.**
All four orchestrated plans carry byte-identical `source_id` pointer shapes, and `orchestrator inbox
detect` returns `orchestrated: true` on each — so the pointer, the detector and the persisted metadata
are all innocent. ⛔ **Operational consequence in the consuming repo: an empty inbox drain means
*nothing was sent*, never *nothing happened*.** PLAN-17's landing was invisible for a full day.

## Verification at plan-marshall `origin/main` 7a028157e (read-only, 2026-09-15)

**STILL-VALID, and the cause is upstream of every place the epic looked.**

- **The step never re-detects.** `phase-6-finalize/standards/emit-landing.md:49-52` — it "carries NO
  step-activation logic… driven solely by presence of `emit-landing` in `manifest.phase_6.steps`";
  `:81-83` — "`orchestrated` — bool; true by construction… This step MUST NOT re-issue either
  resolution call".
- **Mode (a)/(c) — the runtime skip fires on an EMPTY INPUT, not on a negative detection.**
  `emit-landing.md:116-134` Step 0 emits `--outcome skipped --display-detail "not orchestrated, no
  landing emitted"` **when the `epic` input is empty**. The only resolution lives at
  `phase-6-finalize/SKILL.md:765` under *"4b. Lessons-capture Signal Gate (run BEFORE dispatching the
  step if step_id == "lessons-capture")"*, with the `request read --section source_id` →
  `orchestrator inbox detect` call nested at `:777-784`; `SKILL.md:883` then says emit-landing "is
  likewise INLINE — carry the same two values into it directly". ⛔ **So the verdict is computed inside
  a DIFFERENT step's gate and carried in-context across ~9 intervening steps with no persisted
  fallback.** If `lessons-capture` is not composed or not dispatched, or the value is simply not
  carried, `epic` is empty and a genuinely orchestrated plan is skipped by the "defensive" guard. That
  is the observed non-determinism, and it needs no code change between runs to flip.
- **Mode (b) — the compose gate drops the step on every negative, including unobservable ones.**
  `manage-execution-manifest.py:931-987` drops `emit-landing` on any non-orchestrated verdict — an
  `ImportError` explicitly included (`:971-975`, *"orchestration detector unavailable; dropping terminal
  emission (fails toward non-orchestrated)"*), as is an unreadable or absent `request.md`
  (`_read_plan_source_id` → `None`, `:900-929`). The drop is written to the **decision** log at compose
  time, never to the work log — which is exactly why the epic's `grep` over `work.log` found nothing.
- **Not a regression in the 09-05 → 09-07 window.** `git log` over both files in that window shows only
  `de10dfa97` (docs/exit-code) and `c0e945d6a` (autonomy-gate defaults); neither touches the gate.

## Already tracked — and what this adds

`truthful-signals/plans/PLAN-TRUTH-149-the-landing-payload-and-what-the-epic-learns-from-it.md`
(**staged**) carries D1 *"emit-landing verifies its own emission and reports the verdict"*, inherited
from superseded PLAN-TRUTH-106; active lesson `2026-09-09-06-001` is adjacent. ⛔ **Neither names this
cause.** Self-verification would make the failure *visible*; it would not make the verdict *reachable* —
a step that reports "I emitted nothing because `epic` was empty" is still a lost landing. **This is a
plumbing defect: the orchestration verdict needs a persisted carrier** (write it once at compose time,
or let the step re-resolve from the plan's own `source_id`, which `inbox detect` already answers
correctly), and the compose-time drop needs to distinguish *detector unavailable* from *not
orchestrated* rather than failing toward silence.

---

## The retired API-Sheriff ledger entries, verbatim (oldest first)

- ⛔ **`emit-landing` skips orchestrated plans, and the epic learns nothing from the drain.** PLAN-02's
  finalize recorded `emit-landing … skipped -- not orchestrated` while the plan **is** orchestrated —
  archived `source_id` unchanged, `inbox detect` returns `orchestrated: true` /
  `detection: orchestrated`. Same shape as PLAN-01's four bypassed lessons. **Two occurrences, and in
  both the persisted pointer detects correctly**, so the fault is downstream of `inbox detect`, in
  whatever the finalize step actually reads. ⚠ **Operational consequence right now**: no epic landing
  arrives by inbox, so every landing must be pasted or the ledger silently misses it — the inbox
  drain's `count: 0` means "nothing was sent", never "nothing happened". Unowned; a bundle-level fix.
  — source: archived `request.md` read plus `inbox detect` at HEAD `1c7308c`.

- ⛔ **`emit-landing` SKIPPED FOR AN ORCHESTRATED PLAN — THIRD OCCURRENCE, and the two successes did
  NOT mean it was fixed (2026-09-07).** PLAN-03's `work.log:457` records
  `Completed step: emit-landing (outcome=skipped)`, while its archived `request.md:7` carries
  `source_id: .plan/local/orchestrator/deployment-configurability/plans/PLAN-03-upstream-hostname-verification.md`
  and `inbox detect` on that exact value returns `orchestrated: true` / `detection: orchestrated`.
  The inbox is empty and no `upstream-hostname-verification` sender directory exists under
  `inbox/archive/`, so nothing was sent — this landing reached the epic only by operator paste.

  ⛔ **NEW EVIDENCE THAT NARROWS IT — the source_id shape is NOT the discriminator.** All four
  orchestrated plans carry byte-identical pointer shapes (`source: description`, the same
  `.plan/local/orchestrator/deployment-configurability/plans/PLAN-NN-slug.md` form), and **two
  succeeded while two skipped**:

  | Plan | Landed | `emit-landing` |
  |---|---|---|
  | PLAN-02 | 2026-09-02 | ⛔ skipped |
  | PLAN-10 | 2026-09-04 | ✅ delivered |
  | PLAN-15 | 2026-09-05 | ✅ delivered |
  | PLAN-03 | 2026-09-07 | ⛔ skipped |

  So the fault is not the pointer, not `inbox detect`, and not the persisted metadata — **it is
  non-deterministic with respect to everything observable from the plan record**. The
  skip-success-success-skip ordering also admits a **regression between 2026-09-05 and 2026-09-07**
  as readily as intermittency; that window is where to look first, and it is the window in which
  plan-marshall tooling was being upgraded.

  ⛔ **The standing operational rule is now upgraded from caution to fact**: an empty inbox drain
  means *nothing was sent*, never *nothing happened* — **and the channel is demonstrably
  intermittent, so a delivered landing is no evidence the next one will arrive.** Always reconcile an
  empty drain against the plan's own report. Unowned; a bundle-level fix. — source: archived
  `work.log`, `request.md`, `inbox detect`, and `inbox/archive/` enumeration at HEAD `a8c9834`.

- ⛔ **`emit-landing` DID NOT RUN AT ALL for PLAN-07 — a THIRD failure mode, distinct from the two
  already recorded.** `grep -c 'emit-landing'` over the archived `work.log` returns **0**, while
  every neighbouring step logs its `Completed step: … (outcome=…)` line. So the step was **absent
  from the composed manifest**, not merely skipped at runtime — and PLAN-07's `request.md` carries a
  valid orchestrator `source_id`. The channel's record is now: **3 delivered, 3 skipped-at-runtime,
  1 absent-from-manifest, 1 correct abstention.** ⚠ That third mode matters because the existing
  diagnosis ("the fault is downstream of `inbox detect`, in whatever the finalize step reads") cannot
  explain a step that never entered the step list. Unowned; a bundle-level fix. — source: archived
  `work.log` and `request.md` at HEAD `a30fe6f`.

- ⛔ **RECURRENCE 2026-09-11 — OCCURRENCES FOUR AND FIVE, BOTH SKIPPED-AT-RUNTIME.** PLAN-08 and
  PLAN-17 both ran `emit-landing` and both got `outcome=skipped` — verified in each archived
  `logs/work.log` (`2026-09-10T22:50:21Z` and `2026-09-10T21:09:57Z`). Channel record is now
  **3 delivered / 5 skipped-at-runtime / 1 absent-from-manifest / 1 correct abstention**.
  ⛔ **PLAN-08 reported "Finalize steps (19/19)" and the channel still delivered nothing** — the
  epic's own rule that a green step count is not evidence of work, demonstrated on the one step whose
  entire job is evidence. ⛔ **PLAN-17's landing was invisible for a full day as a result**: no inbox
  message and no paste, found only because `analyze` fetched `main` while corroborating PLAN-08.
  **A silent channel plus an unmentioned plan is how a shipped plan goes unrecorded.**
