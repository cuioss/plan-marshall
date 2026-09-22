# PLAN-46: Terminal-Title Repaint Is Delivered On A Channel That Cannot Land

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced 2026-07-22 by the operator (stale `2.1.217` pyprojectx tab title on a
> plan already in phase-5, "sometimes it works, sometimes not"). **RE-GROUNDED and materially
> re-scoped 2026-07-22** after a second operator report — the orchestrator's own title never
> repaints either — which was traced to a different and more fundamental root cause than this
> spec's original dispatch hypothesis. Ground truth at `main` @ `287c3c86d`.

## Objective

The terminal title has **two** delivery channels: a hook-written `terminalSequence` envelope
(PRIMARY — Claude Code itself writes the bytes, so it needs no tty) and a direct `/dev/tty` write
(documented FALLBACK). The primary channel is **plan-scoped only**: it resolves the session's bound
*plan* and returns empty when there is none. Orchestrator epics have no path into it at all, so an
orchestrator title can only ever attempt the `/dev/tty` fallback — which does not work in this
runtime. Make orchestrator titles reach the terminal on the channel that actually lands, and make
non-delivery readable instead of silent.

## ⚠ Mechanism — RE-GROUNDED at `287c3c86d`

The original spec's mechanism is **superseded**. Recorded here in full because the correction is
the finding.

- **REFUTED (this spec's own prior claim):** "only the main orchestrator context holds the
  controlling tty, so a repaint computed in a subagent must be delivered by the main context."
  **False.** The main context holds no controlling tty either. Refuting observation, captured live
  2026-07-22: the `resume` verb's Step-1 repaint, fired **inline in main context**, returned
  `pushed: false, reason: no_controlling_tty, delivery: dev_tty_fallback`. The old D3 — "persist a
  pending title-state that the main context drains and repaints" — would therefore have shipped a
  fix that **cannot work**, because it routes to a context with no tty. Dispatch-vs-inline was
  never the discriminator.
- **OBSERVED — `/dev/tty` is the documented fallback, not the primary channel.**
  `manage-terminal-title/standards/terminal-title-architecture.md`:22-26 — "the hook-mode
  `terminalSequence` envelope is the **PRIMARY** delivery channel: Claude Code itself writes those
  bytes to the terminal, so it needs no tty ownership"; :291-293 names the `/dev/tty` push the
  FALLBACK, existing only for "the blocking windows no hook event spans".
- **OBSERVED — the primary channel is plan-scoped and has no orchestrator branch.**
  `platform-runtime/scripts/_claude_runtime_impl.py` `session render-title`: Step 1 reads
  `$CLAUDE_CODE_SESSION_ID` (:318); Step 2 resolves it via
  `claude_runtime._read_active_plan(session_id)` and **returns `""` when no plan is bound**
  (:323-325); Step 3 resolves title state via `claude_runtime._read_title_state(plan_id)` (:330),
  which reads a *plan* `status.json` (live → worktree → archived, `claude_runtime.py`:962-1008).
  There is no `kind=orchestrator` path anywhere in the render flow.
- **OBSERVED — the orchestrator state reader exists but is wired only to the dead channel.**
  `claude_runtime._read_orchestrator_title_state` (`claude_runtime.py`:1011) resolves the epic's
  `status.json` through `get_store_dir('orchestrator', slug)` and is called from exactly one place:
  `push-title-token` (`_claude_runtime_impl.py`:496) — whose only delivery is the `/dev/tty` write
  at :515. So orchestrator title state is computed correctly and then handed to a channel that
  structurally cannot deliver it.
- **OBSERVED — the hook is installed and firing.** `.claude/settings.local.json` wires
  `session render-title` on `SessionStart` (matcher-less and `clear`), `UserPromptSubmit`,
  `Notification`, `Stop`, and `Pre`/`PostToolUse` for `Bash` and `AskUserQuestion`. The primary
  channel ran dozens of times during the session that produced this finding. Invoked directly,
  `session render-title --statusline` emits **empty output** — the Step-2 early return — which is
  why the tab keeps whatever a build subprocess last painted (`2.1.217`).
- **OBSERVED — the repaint contract this makes vacuous.**
  `persona-marshall-orchestrator/standards/orchestration-model.md` § Terminal-Title Repaint
  Contract requires **all nine** orchestrator verbs to repaint at entry, and declares the seam
  "best-effort: when the terminal-title surface is not configured … the seam is a silent no-op".
  In this runtime the no-op is not the exceptional case, it is **every** case: the contract
  mandates a push that can never land, and its best-effort framing hides that. This is
  simultaneously a `vacuous-guard` instance (the obligation's predicate never fires) and a
  `confident-signal-hides-a-caveat` instance (`status: success` on a push that delivered nothing).
- **HYPOTHESIS (confirm at outline):** the fix requires a session→epic binding analogous to
  `_read_active_plan`, so the hook-driven render can resolve orchestrator state from `session_id`
  alone (the hook receives no `--slug`). Confirm/refute at `claude_runtime.py`
  § `_read_active_plan` and the session-cache writer that feeds it — determine whether the existing
  binding record can carry an epic slug alongside the plan id, or whether a parallel binding is
  needed. Verify-at-outline; if the binding already supports it, D3 collapses to wiring only.
- **HYPOTHESIS (confirm at outline):** the ORIGINAL dispatch-related symptom (a *plan* in phase-5
  showing a stale title) may be a **separate** residual from this orchestrator gap, since a
  plan-bound session does have a working primary channel. Confirm/refute by checking whether
  `_read_active_plan` resolves during a dispatched execute step — if it does, plan titles were
  never broken by dispatch and the original report is explained by the same `/dev/tty` no-op in a
  window no hook event spans. Do not assume the two symptoms share a cause.

## Deliverables

1. **D1 — GATE (mutates nothing).** Settle both HYPOTHESES above: whether the session binding can
   carry an epic slug, and whether the original plan-side stale-title symptom is the same defect or
   a separate residual. Establish the corrected design constraint — **no context in this runtime
   holds a controlling tty, so every reliable repaint must go through the hook-written
   `terminalSequence` envelope** — and record it, because this spec previously asserted the
   opposite and a future reader must not re-derive the refuted version.
2. **D2 — make non-delivery readable.** Route the "title repaint not delivered" / "title teardown
   not delivered" events (`_status_core.py`:600 and :576) through the persisted `log_entry` /
   manage-logging channel instead of the unconfigured Python `logging` logger, whose records reach
   only subprocess stderr and are never persisted. Best-effort: a logging failure must not change
   the command's status or exit code. Separable and correct independent of D3.
3. **D3 — give the orchestrator a path into the primary channel.** Per D1, teach the hook-driven
   `session render-title` to resolve and compose orchestrator title state (`kind=orchestrator`,
   the `Orchestrator-{SlugName}` body) when the session is bound to an epic rather than a plan,
   reusing `_read_orchestrator_title_state` and the existing composer branch rather than adding a
   parallel one.
4. **D4 — stop reporting a no-op as success.** `push-title-token` returns `status: success` with
   `pushed: false` when nothing was delivered; the repaint contract calls this best-effort. Make
   the distinction legible at the call sites that matter (and reconcile the standard's
   Terminal-Title Repaint Contract wording with the fact that the fallback channel is inert in this
   runtime), so a permanently-dead channel cannot masquerade as a configured-off one.
5. **D5 — regression tests.** (a) A session bound to an epic with **no** controlling tty renders a
   non-empty orchestrator `terminalSequence` from the hook path; (b) a `current_phase` transition
   with no tty writes a **persisted** non-delivery entry; (c) the plan-bound render path is
   unchanged (no regression to the working channel).

Five deliverables, D1 a gate — under the six-deliverable split guard. Deliberately **not** split
from the orchestrator-channel work: D2–D5 all touch the same two files
(`_claude_runtime_impl.py`, `_status_core.py`), so splitting would put two plans on one surface and
force a rebase, which the disjointness rule exists to prevent.

## Expected Surface

- OBSERVED: `platform-runtime/scripts/_claude_runtime_impl.py`:300-350 (`session render-title`
  Steps 1-3) and :448-531 (`push-title-token`, the `/dev/tty` fallback).
- OBSERVED: `platform-runtime/scripts/claude_runtime.py`:962-1008 (`_read_title_state`),
  :1011+ (`_read_orchestrator_title_state`), and `_read_active_plan` / the session-cache writer.
- OBSERVED: `manage-status/scripts/_status_core.py`:576, :581 (`_drive_repaint`), :600, :603
  (`_surface_drive`) — the non-delivery logging half.
- OBSERVED: `manage-terminal-title/standards/terminal-title-architecture.md`:22-26, :291-293 —
  the two-channel contract, updated if D4 changes the best-effort framing.
- OBSERVED: `persona-marshall-orchestrator/standards/orchestration-model.md` § Terminal-Title
  Repaint Contract — the nine-verb obligation reconciled with D4.
- HYPOTHESIS: `platform-runtime/scripts/opencode_runtime.py` / `runtime_base.py` — touched only if
  the render seam is shared across runtimes (verify-at-outline; only Claude Code is a tested
  runtime).
- OBSERVED: tests under `test/plan-marshall/platform-runtime/**` and
  `test/plan-marshall/manage-status/**`.

Re-verify against HEAD at outline: PLAN-49 renames `persona-marshall-orchestrator`, and this
plan edits that standard.

## Dependencies and Sequencing

- Depends on: none. Emittable now.
- Overlaps with: **PLAN-53** — its verify-first clause may pull `manage-status` into scope; both
  plans touch `_status_core.py` only if that happens, so re-check disjointness before running the
  two concurrently. **PLAN-49** renames a standard this plan edits and must stay last.
- Adjacent to: PLAN-42 (waiting-seam observability) is the same *archetype* on a different seam and
  stays untouched here; PLAN-47/48 touch orchestrator config, not the title channel.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-46-title-repaint-lost-from-dispatch-and-unlogged.md"
```

## Notes

- Prior terminal-title work — PLAN-05 stale-build-busy #931, PLAN-26 refresh-cadence #964, PLAN-30
  orchestrator-title-push-coverage #967, and the #856 unified phase-write seam — addressed cadence
  and *coverage of the push call sites*. PLAN-30 in particular added orchestrator push coverage
  **on the fallback channel**, which is why every verb now dutifully calls a seam that cannot
  deliver. D1 re-grounds against what those shipped before touching it.
- Archetype membership: this plan is now a **triple** instance — silent non-delivery reported as
  `status: success` (confident-signal), a nine-verb contract whose predicate never fires
  (vacuous-guard), and a standards doc describing a primary/fallback split that the orchestrator
  path never actually honours (doc-contract-divergence).

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` — the orchestrator owns every ledger write — and
reports its outcome through its PR alone. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
