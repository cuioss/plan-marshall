> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-034`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-033: a plan has two identities, and the terminal shows only one

epic: truthful-signals
workstream: WS-01

## Objective

A plan is addressed by **two different identifiers that never appear together**, and the operator cannot
map one to the other at the moment it matters — when several plans run in parallel and they need to know
**which terminal is which**.

| Identity | Example | Where it appears |
|---|---|---|
| **Spec id** | `PLAN-TRUTH-031` | orchestrator emits, queue rows, epic ledger, landing reports |
| **Runtime plan id / slug** | `finalize-step-records-are-prose-not-facts` | terminal title, plan directory, branch name, inbox `sender_id` |

The orchestrator speaks exclusively in the first. The terminal shows exclusively the second. **Nothing
renders both**, so "launch TRUTH-027" and "which window is that?" are unconnected questions.

## Operator direction (2026-08-02), preference stated

1. ⭐ **PREFERRED — make the spec number part of the runtime slug**, so the terminal title carries it and
   the mapping needs no lookup.
2. **Fallback** — the orchestrator renders the slug alongside the spec id after ingestion, so at least
   one surface shows both.

⚠ **They are not equivalent.** Option 2 fixes the orchestrator's *output* only; the terminal title, the
branch name, the plan directory and the inbox `sender_id` all still carry the bare slug. Option 1 fixes
the identity itself. **The fallback is a mitigation, not the fix — say so if it is chosen.**

## Why this is worth a plan and not a note

⭐ **The orchestrator already pays this cost at every drain, by hand.** In the 2026-08-02 session it
mapped `gates-do-not-refire-over-the-loop-back-diff` → `PLAN-TRUTH-001`,
`lane-router-scale-blind-false-negative` → `PLAN-57`, `mandatory-plan-id-build-results-ledger` →
`PLAN-TRUTH-026`, and `finalize-step-records-are-prose-not-facts` → `PLAN-TRUTH-031` — **four mappings,
from ledger memory, with no machine check that any of them was right.** A mis-mapping would attach a
landing to the wrong queue row, and nothing would detect it.

⇒ The operator's terminal-identification problem and the orchestrator's reconciliation problem are **the
same defect** seen from two ends.

## Deliverables

1. **D0 — GATE (mutates nothing): derive every consumer of the runtime plan id before changing it.**
   Known-or-suspected consumers, to be confirmed and completed: the terminal title, the plan directory
   name, the archived-plan directory name, the git branch (`feature/{slug}`), the inbox `sender_id` and
   its `{sender}-{seq}.md` filenames, `inbox detect`'s pointer grammar, and `manage-status` plan
   resolution. ⛔ **This is a rename of a primary key — the population must be enumerated, not sampled.**
2. **D1 — decide option 1 vs option 2, and record the rejected one.** If option 1: fix the composition
   rule (**where** the number goes and in **what case**) against the constraints in § Constraints.
3. **D2 — implement, forward-only.** ⛔ **NEVER rename a launched or shipped plan** — an existing plan's
   directory, branch, archived record and already-emitted inbox messages keep their names. New plans get
   the new form; **the two coexist and every consumer must accept both.**
4. **D3 — close the reconciliation gap.** Whatever D1 chooses, the orchestrator must be able to resolve
   `sender_id → spec id` **mechanically**, not from memory. ⭐ Under option 1 this falls out for free;
   under option 2 it needs its own seam, which is a further argument for option 1.
5. **D4 — tests, each verified to FAIL pre-fix.** (a) A new plan's terminal title contains the spec
   number. (b) A pre-existing plan id still resolves (the coexistence requirement). (c) `sender_id → spec
   id` resolves mechanically for a new plan. (d) D0's consumer population is asserted non-empty and
   contains the terminal title, the branch, and the inbox `sender_id`.

## ⛔ Constraints — hard-won, do not rediscover

- **Never rename a launched or shipped plan.** Standing epic rule; D2 is forward-only.
- ⛔ **A lowercase code slug silently kills the finalize inbox message.** The `PLAN-{CODE}-{NNN}-{slug}`
  spec-file convention (since #1057) requires the CODE segment **UPPERCASE**; a lowercase one fails
  silently rather than loudly. **Any composition rule that lowercases the number segment for a directory
  or branch name must be checked against `inbox detect`'s grammar before it is adopted.**
- **`inbox detect` is the SINGLE detection seam** for orchestrated-plan pointers
  (`.plan/local/orchestrator/{slug}/plans/PLAN-NN-*.md`). ⛔ Do not add a second detector, and do not
  break this one — it is what makes a plan know it belongs to an epic.
- **Branch names are governed by a CLOSED prefix set** (`feature/`, `fix/`, `chore/`) because CI triggers
  only on those; a branch outside it gets no CI run and its PR can never go green. Any slug change must
  keep the prefix intact.

## Claim Labels

- **OBSERVED**: the two identities and where each appears — from this session's own queue rows, landing
  reports, inbox `sender_id` values, and archived-plan directory
  (`.plan/local/archived-plans/2026-08-02-finalize-step-records-are-prose-not-facts`).
- **OBSERVED**: the orchestrator performed four `sender_id → spec id` mappings by hand on 2026-08-02 with
  no machine check.
- **OBSERVED**: spec files already carry both identities (`PLAN-TRUTH-031-finalize-step-records-...md`) —
  ⭐ **so the composition already exists at the spec layer and is simply not propagated to the runtime id.**
  That is the cheapest possible starting point for option 1.
- **HYPOTHESIS**: the consumer list in D0 is complete. ⛔ **It is a sample assembled from this session's
  observations — DERIVE IT.** A missed consumer of a primary-key rename is a silent breakage.
- **HYPOTHESIS**: the terminal title renders the runtime plan id verbatim (rather than a derived label).
  **Confirm at D0** against the terminal-title seam — if it derives a label, option 2 may be cheaper than
  it looks.
- **Verify-first clause**: D2's coexistence requirement assumes every consumer can accept both the old
  and new id forms. Confirm per consumer at D0; any consumer that cannot forces a different D1 answer.

## Expected Surface

- **HYPOTHESIS**: `plan-marshall/skills/phase-1-init/**` — where the runtime plan id is minted
- **HYPOTHESIS**: `manage-terminal-title` / `platform-runtime` — the title seam
- **HYPOTHESIS**: `marshall-orchestrator` — `inbox detect`, and the emit/reconcile surfaces for D3
- **HYPOTHESIS**: `workflow-integration-git` — branch naming
- **HYPOTHESIS**: `tools-file-ops` — plan-directory resolution
- **OBSERVED**: the epic's own `plans/` naming already carries the composed form

## Dependencies and Sequencing

- **Depends on**: none. ⚠ **Adjacent to `PLAN-TRUTH-032`** — 032 owns the inbox protocol and would gain a
  mechanically-resolvable `sender_id`; if 032 lands first, D3 gets simpler. **Sequence, do not pair.**
- ⚠ **`PLAN-TRUTH-015`** renames `marshall-orchestrator` — re-ground paths if it lands first.
- ⛔ **Operator marked this FOR LATER (2026-08-02) — staged, deliberately NOT emitted.** Staged rather
  than left as a note because this epic's own rule is that **recording a defect is not owning it**.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-033-a-plan-has-two-identities-and-the-terminal-shows-only-one.md"
```

## ⭐ FOLDED 2026-08-03 — OPERATOR-RAISED, LOW priority: `?` says "I need you" when the plan is merely busy

**Operator**: *"If a plan starts a shell / monitor, `?` is displayed. But that means 'needs input / has a
question'. For those cases it must be a different icon / literal."*

⭐ **Folded here rather than staged separately**: same surface (`manage_terminal_title.py` +
`claude_runtime.py`), same subject (*the title does not tell the operator what they need to know*), and
both are operator-raised. ⛔ A separate plan would collide on both files for a one-glyph outcome.

### OBSERVED — first-party, the whole vocabulary

`manage_terminal_title.py:73-86`:

```python
_ICON_ACTIVE = "➤"   _ICON_WAITING = "?"   _ICON_DONE = "✓"
_ICON_TERMINAL = "✅"  _ICON_BUSY = "⚙"     _ICON_BUILD = "🔨"
```

`claude_runtime.py:303-331` — `_claude_event_to_process_state`:

| Event | State | Icon |
|---|---|---|
| `Stop` | `done` | ✓ |
| **`Notification`** | **`waiting`** | **`?`** |
| **`PreToolUse` + `AskUserQuestion`** | **`waiting`** | **`?`** |
| `PreToolUse` + `Bash` | `busy` | ⚙ |
| everything else | `active` | ➤ |

⇒ ⛔⛔ **TWO conditions with DIFFERENT operator obligations collapse into ONE state and ONE glyph:**

- **`AskUserQuestion`** — the operator **must act**; nothing proceeds without them.
- **`Notification`** — the operator **may not need to act at all.**

⭐⭐ **That is this epic's archetype in the icon slot**: a signal that cannot distinguish *"I am blocked
on you"* from *"something happened"*, rendered with the glyph that means the first. ⚠ **And the cost is
asymmetric in the expensive direction** — a `?` that does not need the operator trains them to ignore a
`?` that does.

⛔ **NOT ESTABLISHED — and it is the deliverable's first question**: *which* condition fires
`Notification` when a plan starts a shell/monitor. A plain `Bash` call maps to `busy` (⚙), **not** `?`,
so the observed `?` must come from `Notification`. **HYPOTHESIS**: Claude Code emits `Notification` both
for a permission request and on an idle-input timeout, and a long-running monitor trips the latter.
⚠ **Plausible and unverified — read the harness contract, do not infer it from the symptom.** ⭐ If the
`Notification` payload carries a distinguishing field, the fix is a resolver branch; **if it does not,
the state cannot be split at this seam and the deliverable changes shape entirely.**

### Deliverables (append to this plan's set)

1. **D-A — GATE: derive what `Notification` actually signals**, and whether its payload distinguishes
   permission-request from idle. ⛔ **Both directions**: every event that reaches `waiting`, and every
   condition that should. **The answer decides whether the rest is a one-line map change or a new
   channel.**
2. **D-B — split `waiting` into "blocked on the operator" and "unattended/idle".** ⭐ Reserve `?` for the
   genuinely-blocking case (`AskUserQuestion`, and permission-requests if D-A can identify them). Give
   the other its own icon. ⚠ **`⚙` is already taken by momentary-busy and `🔨` by build-busy** — the
   architecture doc records both as *deliberately distinct*, so **do not overload either**; pick a new
   glyph and record why.
3. **D-C — a test that FAILS pre-fix**: a `Notification` that is not operator-blocking must not render
   `?`. ⛔ **Verify it fails today** — the whole point is that the two are currently indistinguishable,
   so a test written against the current resolver would pass vacuously.

⚠ **LOW priority, by operator designation — and genuinely small IF D-A says the payload discriminates.**
⛔ **Do not size it before D-A.** *(Standing correction: I over-estimated the inbox-archive foldering by
inferring blast radius before checking; this note is here so the same reflex does not run the other way
and under-size a change that needs a new channel.)*

### ⛔⛔ SECOND SYMPTOM, same drain — a RUNNING terminal shows `?`, not `➤`. This is STALENESS, not mapping.

**Operator, same turn**: *"we have always-running terminals that display `?` as well instead of `➤`.
There seems to be an update issue as well."*

⭐⭐ **This is a DIFFERENT defect from the one above, and it dominates it.** D-B splits the glyph; a
correctly-split glyph that **never repaints** is still wrong. ⇒ **D-B alone would not fix what the
operator is actually looking at.**

#### OBSERVED — the mechanism is stated in our own contract

`platform-runtime/SKILL.md:47`, on `session push-title-token`:

> *"This seam **binds and persists — it does not repaint**: the hook-written `terminalSequence` envelope
> is the sole delivery channel and is **event-driven**, so delivery is **deferred to the next render**."*

⇒ ⛔ **The icon is not a live state — it is the LAST DELIVERED state.** Once `Notification` latches
`waiting`, the `?` persists until some later event produces a render. If the plan then works through
paths that yield no render event, **the `?` outlives the condition that caused it.**

> ⭐⭐ **The icon slot is a LATCH presented as a STATE.** An operator cannot distinguish a stale `?` from
> a live one — which is this epic's archetype at the one surface the operator watches continuously.

#### ⚠ HYPOTHESIS for why it persists so reliably — named, not assumed

`active` (➤) is only reached via `UserPromptSubmit` / `SessionStart` / `PostToolUse`. A plan spends most
of its wall-clock **inside dispatched agent envelopes**. **HYPOTHESIS: hook events raised inside a
dispatched envelope do not reach the render channel**, so the last main-session event — often a
`Notification` — stays latched for the entire dispatch.

⛔ **Plausible and NOT verified.** ⭐ **It is also a RECURRENCE if true**: `PLAN-46`
(*title-repaint-lost-from-dispatch-and-unlogged*) and `PLAN-79` (*terminal-title-channel-reconciliation*)
both **SHIPPED** against this family. ⇒ **Read their landings before scoping** — *a fix that shipped and
the symptom recurring is a stronger signal than a fresh defect*, and it means the earlier fix's
population was narrower than the condition.

⚠ **Competing reading, which must be discriminated**: the render channel works fine and the *state* is
simply never re-bound to `active` after a `Notification`, in which case the fix is in the resolver, not
the channel. ⛔ **The two remedies are in different files. Do not pick one before D-D.**

#### Deliverables (these supersede the sizing note above)

4. **D-D — GATE: determine whether the `?` is STALE or LIVE at the moment the operator sees it.**
   ⛔ **This is the decisive question and it precedes D-A/D-B.** Cheapest discriminator: instrument or
   inspect the last-delivered envelope against the session's current activity. ⭐ **Both outcomes are
   results** — stale ⇒ a delivery/repaint defect; live ⇒ the resolver never returns to `active`.
5. **D-E — the icon must decay or refresh.** Whatever D-D finds, a state that can only be *entered* by an
   event and never *left* by one is a latch. ⛔ **A test that FAILS pre-fix**: after a `waiting` bind,
   subsequent activity restores `active` on the delivered title.

⭐ **Priority note, corrected**: the operator filed the glyph half as **LOW**. ⚠ **This half is not the
same item** — a persistently wrong icon on every running terminal degrades the one signal they watch
continuously, and it makes the LOW-priority half unverifiable (you cannot tell a fixed glyph from a
latched one). ⛔ **Do not inherit "low" across the fold** — surface the split and let the operator
re-rank.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
