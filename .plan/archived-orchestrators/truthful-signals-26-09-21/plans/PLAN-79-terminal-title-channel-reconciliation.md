# PLAN-79: Terminal Title — Reconcile The Channel Set, Once

epic: truthful-signals
workstream: WS-01

> **Operator-directed 2026-07-26**, with screenshots, and with an explicit instruction: *"In the past we
> had multiple iterations on this. When we fixed one aspect, another aspect reoccurred… I want you to
> do a thorough analysis… in order to overhaul the complete machinery. I want you to fix it one for
> all."* Two read-only analysis contexts were dispatched in parallel — one over the machinery, one over
> the repair history — and **they converged on the same root from independent evidence**. This spec is
> their synthesis. **It is an overhaul, not a point fix, and it is scoped that way deliberately.**

## Objective

The title system has **one channel that delivers** (the hook `terminalSequence` envelope) and **three
that do not** (`/dev/tty`, `hookSpecificOutput.sessionTitle`, and statusLine which cannot carry OSC).
Every repair since #619 has added a *writer* or a *state field* instead of reconciling that channel
set — which is why each fix closed one leak and opened another. Reconcile the channels, give every
machine-set state a machine-owned clear, and pin the two observable invariants that no existing test
asserts.

## ⚠ Mechanism — OBSERVED, two independent analyses agreeing, with field evidence

### Defect 1 — the ✅ terminal state is composable but structurally undeliverable

- OBSERVED — the composer is CORRECT. `manage_terminal_title.py:112` defines
  `_TERMINAL_PHASES = {complete, archived}` and `compose()` (`:266-267`) renders `✅ pm:Completed`.
  **This is not a missing feature.**
- OBSERVED — `current_phase = 'complete'` is written **only** by `cmd_archive`
  (`_cmd_lifecycle.py:443`); the alternative writer is explicitly forbidden in phase 6
  (`phase-6-finalize/SKILL.md:1266`: *"A separate `manage-status transition --completed 6-finalize`
  call MUST NOT be issued from this phase"*).
- OBSERVED — `cmd_archive` calls `_drive_teardown` (`:472`) → `session_teardown`
  (`_claude_runtime_impl.py:673`), which writes the reset escape **only to `/dev/tty`** (`:707-712`) —
  the channel **this repo's own architecture doc calls a "permanently-inert FALLBACK"**
  (`terminal-title-architecture.md:26-33`) — and then calls `session_binding.unbind` (`:717`)
  **unconditionally, not gated on the reset succeeding**.
- OBSERVED — an unbound session makes `session_render_title` `return ""`
  (`_claude_runtime_impl.py:319-344`, six distinct silent early-return paths), and `""` writes nothing
  by contract (`:280`). **No render → no repaint → the last painted bytes persist forever.**
- **Therefore the single command that finally says "done" is the same command that destroys the only
  route capable of saying it, after failing to say it on a channel known to be dead.**
- **OBSERVED IN THE FIELD, not inferred** — `.plan/temp/dormated-plans/global-logs/work-2026-07-25.log`
  carries 5 post-#964 occurrences of `title teardown not delivered … title_reset_failed` and **zero**
  `binding_release_failed`. Every archive: **reset fails, unbind succeeds.** The operator's "consistent
  for all plans" was already in our logs, unread.

### Defect 2 — 🔨 is SET by machinery and CLEARED by prose

- OBSERVED — `_claude_runtime_impl.py:403-415` sets and **persists** `title_token = "build-busy"` on
  `PreToolUse:Bash` when `_command_is_build` matches. The comment at `:397-400` states the asymmetry is
  intentional: *"The hook only SETs — it never CLEARs … the clear is necessarily the agent's D3
  obligation."* The clear is an **English instruction to an LLM**
  (`agent-behavior-rules.md:337-344`), not machinery.
- OBSERVED — the only machine net, `drop_stale_build_busy` (#931, `_cmd_lifecycle.py:382`), fires
  **on phase transition only**. `6-finalize` is the terminal phase and has no successor, so
  **the net cannot fire in the build-densest phase.** `grep -rn build-busy` across
  `phase-6-finalize/` returns **nothing**.
- **OBSERVED, measured** — set:clear ratios in real work logs: **17:3** in
  `2026-07-23-plan-46-…`, and **6:0** in `2026-07-25-repair-plan-retrospective-false-verdicts`.
- OBSERVED — `title_token` is a **single scalar shared by two orthogonal concerns**: a merge-lock
  acquire (`merge_lock.py:694,709`) silently clobbers a live `build-busy`, and `_clear_title_token`
  (`:658`) clears whatever another writer owned. Four independent writers, one overwritable string,
  no ownership.
- HYPOTHESIS — that the frozen glyph is specifically 🔨 rather than ⚙/➤ depends on which hook event
  painted last before archive. Highly likely (finalize is build-dense, the token persists) but **the
  freeze mechanism is what is proven, not the particular icon.**

## ⚠ The repair history — why this must not be another point fix

**The build glyph was already declared structurally impossible, deleted, and then re-added anyway.**

- `#619` (06-10) adds the 🔨 build glyph → `#622` finds it goes stale → **`#639` investigates,
  concludes it is structurally unpaintable, and DELETES the feature**, recording the diagnosis in the
  commit message: *"a build runs as a single blocking tool call, so no between-call hook event ever
  fires while `building` is set, and `/dev/tty` is `[Errno 6] Device not configured` in the build
  subprocess — so the only in-call renderer also no-ops."*
- **18 days later `#792` re-adds it**, working around the impossibility by painting *before* the call
  and *persisting* the state — which converts a rendering problem into the set/clear asymmetry that is
  Defect 2 today. `#931` then bolts on a net that cannot fire in phase 6.

**A reviewer predicted the exact defect at merge time and it was declined.** CodeRabbit on #792
(🟠 Major): *"a stray match can leave the title stuck on 🔨 until some later manual clear."* Author's
reply: *"The consequence of a false positive is cosmetic only… The argv-based approach you suggest is
stricter and correct in principle; it is noted as a future improvement. Accepting for now."* #931 was
filed 20 days later for a sibling trigger of the same hole.

**#964 diagnosed the dead channel in its own PR body and then built the reset on it** — *"a `/dev/tty`
push that silently no-opped when the writing process owned no controlling terminal"* — and made the
unbind unconditional on that reset succeeding. CodeRabbit also flagged that the teardown result was
discarded; **observability was added (`title_reset_failed`), the failure itself was not fixed.** That
is why the defect is now legible in our logs while the title still freezes.

**The existing tests are GREEN on both defects because they pin the seams that cause them.**
`test_title_token.py:468` asserts *"archive fires teardown exactly once"*; `test_claude_runtime.py:1356`
asserts *"a build command persists the build-busy token"*. The `✅ pm:Completed` tests pass because
`test_claude_runtime.py:1536` **hand-writes the `active-plan` file that production's `unbind` deletes**,
and the teardown tests **mock `reset='true'`, a value production can never return.** Every fix has been
verified at the wrong altitude. Across all 8 archived title plans, **not one verified against a real
terminal** — two say so outright (#851: *"the shared verification path is the manual/observational
title-render check, not an automatable test"*; #967: *"verify by asserting the invocation is present…
NOT by looking at the terminal tab"*).

⚠ **Review coverage collapsed exactly where the changes got structural.** #851, #931, #967 and #994
received effectively **zero** automated review (Gemini error/sunset + CodeRabbit/Sourcery rate limits).
#851's binding policy shipped unreviewed and was **reversed two days later by #856**. This is
**PLAN-72's reviewer-quorum hole with a measured cost** — cross-link it there.

## Deliverables

### D1 — GATE: reconcile the channel set and write the delivery contract (mutates nothing)

Settle, and record, the **complete** channel inventory and which states each may carry. Binding rule
the analyses converged on: **nothing may be cleared or reset on a channel that cannot deliver, and no
binding may be released before the reset it depends on is confirmed.** Decide (a) whether `/dev/tty`
is deleted from the design or demoted to an explicitly-tested debug path — *a fallback that provably
never lands is worse than none, because it makes the reset look implemented*; (b) how the terminal
state reaches the tab — the analyses' recommendation is to render `✅ pm:Completed` from the archived
state on the next hook event (the archived-path reader at `claude_runtime.py:930` already resolves it)
and **defer or drop the unbind**, since unbinding is not how "done" is expressed; (c) the ownership
model for `title_token`. **Name every artifact each choice edits.**

⚠ **D1 must co-design with PLAN-77.** #964 *widened* the render cadence (matcher-less `PostToolUse`);
PLAN-77 measures that cadence as the single largest script cost (**77,337 `platform_runtime session`
calls / 3h39m, 59.5% of all script wall-clock**) and wants it *narrowed*. A CodeRabbit comment on #964
asked for a debounce and **received no recorded reply**. These two plans pull in opposite directions on
the same seam; D1 must state the joint position or the next plan re-opens this one.

### D2 — the terminal state actually reaches the terminal

Implement D1's completion path so that finishing a plan paints the terminal state on the delivering
channel. **Hard constraint: no binding release before the state it enables has been delivered.**

### D3 — machine-set means machine-cleared

Give `build-busy` a machine-owned clear that does not depend on an LLM turn: clear on the matching
`PostToolUse:Bash`, plus a timestamp on the token so any reader treats an aged token as absent — the
leak must be **self-healing regardless of which process died**. **Remove the prose obligation from
`agent-behavior-rules.md` in the same change**; leaving it is the defending-documentation pattern.
Stop `title_token` being one slot shared by lock and build concerns (structured owner + state +
timestamp, with last-writer arbitration).

### D4 — no silent no-op renders

Replace the six silent `return ""` paths (`_claude_runtime_impl.py:319-344`) with an explicit rendered
state, so "no output" stops being indistinguishable from "correct output". ⚠ **Verify against the host
first** — what Claude Code does with empty statusLine output (keep previous vs blank) is **not
established** and is not in this repo; D1 must confirm it before D4 relies on it.

### D5 — tests that pin the OBSERVABLE, not the seam

This is the deliverable that makes the fix durable, and it is the one every prior attempt lacked.

(a) **Terminal-state invariant** — drive a plan through finalize+archive against a fake terminal sink;
the **last bytes written** must carry the terminal marker, never a `pm:{active-phase}` body.
**This test must be verified to FAIL against current code.**
(b) **No-orphan-token invariant** — property-style over the token vocabulary: every state-setting path
has a clear that fires on the matching completion event, so a newly added token **cannot ship without
a clear**. This is the class guard.
(c) **Total-render invariant** — `render-title` emits for every reachable input, including unbound
session and missing `status.json`.
⚠ **Delete or rewrite the tests that currently pin the defects** (`test_title_token.py:468`,
`test_claude_runtime.py:1356`, the `active-plan` hand-write at `test_claude_runtime.py:1536`, the
`reset='true'` mock). Leaving them green beside a fixed system re-creates the exact false confidence
this plan exists to remove.

### D6 — converge the doc and config divergences this analysis surfaced

Each is the same doc-vs-code failure mode and each is cheap: installed hook config diverges from
`_DISPLAY_RENDER_ENTRIES` (`claude_runtime.py:279-287` — the live file has matcher-scoped `PostToolUse`
and an extra `SessionStart:clear`; `_prune_matcher_scoped_render_entries` at `:442` exists to retire
that shape and **has never run here**) — make this a **doctor check that FAILS, not reports**;
`terminal-title-architecture.md:437-441` claims *"unbind is self-scoped"* while
`session_binding._gc_slot:373` unbinds **other** sessions; `references/workflow-overview.md:45` still
advertises a "Steps 4–7: … terminal title" step **that does not exist**.

**Six deliverables — AT the split guard, proceeding unsplit deliberately.** Rationale: D1 is a gate,
D5 is the cross-cutting guard, D6 is mechanical doc convergence — the implementation core is D2/D3/D4,
all on one seam. **Splitting is the failure mode here**: this defect class has been split across seven
PRs and that is precisely why it kept regressing. If D1 finds D2 and D3 do not share a delivery
contract after all, split then — with the reason recorded.

## Expected Surface

- OBSERVED: `platform-runtime/scripts/_claude_runtime_impl.py` — `session_render_title` `:268`,
  early-returns `:319-344`, build-busy assist `:403-415`, statusLine `:426-432`, `terminalSequence`
  `:435-453`, `session_push_title_token` `:458` + `/dev/tty` `:561-564`, `session_teardown` `:673`,
  reset `:707-712`, unbind `:717`.
- OBSERVED: `platform-runtime/scripts/claude_runtime.py` — `_claude_event_to_process_state` `:207`,
  `_command_is_build` `:252`, `_DISPLAY_RENDER_ENTRIES` `:279`, archived-path reader `:930`,
  `_read_title_state` `:976`, `_manage_status_set_title_token` `:1118`,
  `_prune_matcher_scoped_render_entries` `:442`.
- OBSERVED: `platform-runtime/scripts/session_binding.py` — `unbind` `:264-285`, `_gc_slot` `:373`.
- OBSERVED: `manage-status/scripts/_status_core.py` — `TITLE_TOKEN_BUILD_BUSY` `:66`,
  `_drive_teardown` `:547`, `_drive_repaint` `:589`, `_surface_drive` `:618`,
  `drop_stale_build_busy` `:634`.
- OBSERVED: `manage-status/scripts/_cmd_lifecycle.py` — `:262`, `:375-388`, `:443`, `:452`, `:472`.
- OBSERVED: `manage-terminal-title/scripts/manage_terminal_title.py` — `_TERMINAL_PHASES` `:112`,
  `compose` `:195`, `resolve_icon` `:130`. **Likely read-only — the composer is correct.**
- OBSERVED: `manage-locks/scripts/merge_lock.py` — `:658`, `:694`, `:709` (token co-ownership).
- OBSERVED: `persona-plan-marshall-agent/standards/agent-behavior-rules.md:337-344` — the prose
  obligation D3 removes.
- OBSERVED: `manage-terminal-title/standards/terminal-title-architecture.md`,
  `references/workflow-overview.md:45`, `phase-6-finalize/SKILL.md:1266`.
- OBSERVED: tests under `test/plan-marshall/platform-runtime/**` and
  `test/plan-marshall/manage-status/**`.

⚠ **Disjointness — this is a WIDE surface; treat as exclusive.** It spans `platform-runtime`,
`manage-status`, `manage-locks` and the agent persona. **Do NOT pair concurrently with: PLAN-77**
(same `platform_runtime session` seam, opposite direction — sequence, and co-design at D1);
**PLAN-57** (different file but the same `test/plan-marshall/manage-status/**` test tree);
**PLAN-71/PLAN-72** only if they touch the persona standards. Disjoint from PLAN-75, PLAN-62,
PLAN-76, PLAN-78.

## Dependencies and Sequencing

- **No blocking dependency** — the surface is free of everything currently in flight
  (PLAN-69, PLAN-70, PLAN-54, PLAN-55).
- **PLAN-77 must be co-designed at D1, not sequenced blindly.** Their positions in the queue are far
  apart; whichever runs first sets the cadence policy the other inherits.
- Cross-link **PLAN-72**: the review-coverage collapse on #851/#931/#967/#994 is that plan's premise
  with a measured cost — a structural change reversed two days later after shipping unreviewed.

## Notes

- **⚠ `MEMORY.md` was STALE and is corrected**: PLAN-26 (terminal-title-refresh) **SHIPPED as #964**;
  the index listed it as PENDING under WS-10. Its spec survives at
  `.plan/temp/dormated-plans/2026-07-21-terminal-title-refresh-cadence/request.md` and carries the
  **settled host contract — reuse it, do not re-derive**: statusLine cannot carry OSC;
  `terminalSequence` is the only landing channel; `SessionStart source=clear` is hookable.
- **Reuse, do not re-derive**: PLAN-46's spec carries the load-bearing **REFUTATION** — *"the main
  context holds no controlling tty either"*, so dispatch-vs-inline was never the discriminator — and
  its §D1.4 explicitly scopes the plan-side residual (this plan) out. #639's commit message carries the
  original impossibility proof.
- Lesson `2026-06-30-20-001` (sibling-seam symmetry) is on its **5th recurrence** — the #964 teardown
  asymmetry is that recurrence. Lesson `2026-07-22-12-001` (title-token log noise, 33% of a work log)
  is filed, `status=active`, unfixed — fold into D3.
- Theme fit: flagship. The system reports success on a channel that cannot deliver, and its tests are
  green on the exact behaviours that cause the defects.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
