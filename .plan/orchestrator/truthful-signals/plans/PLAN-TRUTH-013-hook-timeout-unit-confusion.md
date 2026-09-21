# PLAN-TRUTH-013: Hook `timeout` is SECONDS — plan-marshall writes `5000`, widening the guard it advertises

> Renamed from **PLAN-108** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-28 from epic inbox finding `truthful-signals-003`.

## Objective

`claude_runtime.py` writes `"timeout": 5000` into every Claude Code hook entry it provisions. The
field's unit is **seconds**, so the value is ≈83 minutes — it **raises** the ceiling above the
platform default of 600 s rather than bounding it. Correct the literals and add a guard that keeps
emitted hook timeouts inside a plausible seconds range.

## The defect — OBSERVED

`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` writes
`"timeout": 5000` at three sites:

| Site | Line | Hook |
|------|------|------|
| `_render_entry()` | 537 | `SessionStart` title-render |
| `_capture_entry()` | 551 | `SessionStart` session-id-capture |
| `_enforcement_entry()` | 565 | **`PreToolUse` enforcement** |

The Claude Code hooks documentation states the unit verbatim: *"Seconds before canceling. Defaults:
600 for `command`, `http`, and `mcp_tool`; 30 for `prompt`; 60 for `agent`."* The value reads as a
**milliseconds-intent transcription** (5000 ms = 5 s), which is the wrong unit for this field.

## Severity — latent, not active. State it honestly.

⚠ **This does NOT slow the normal path.** A hook that completes promptly is unaffected. The defect is
the **size of the failure window**:

- On the two `SessionStart` hooks, a hang delays session start rather than being killed at ~5 s.
- On `_enforcement_entry()` (`PreToolUse`) a hang blocks tool execution for the duration — **this is
  the one with real exposure.**

**No incident is attributed to this.** It is a latent widening of a guard, filed before it produces
one. The plan must not overstate it.

**Blast radius:** `claude_runtime.py` provisions these entries into **consumer projects**, not only the
meta-project, so the value propagates wherever plan-marshall installs Claude Code hooks. The three
`5000`s observed in this repo's own (gitignored) `.claude/settings.local.json` were written by this
code path — **confirming the emit path is live.**

## Why it belongs to this epic

Theme match — **confident-signal-hides-a-caveat, in its numeric form.** An explicit `timeout` on a
hook entry reads as a deliberate fail-fast guard: a reviewer scanning the config sees a bounded hook
and moves on. **The number does the opposite of what its presence advertises.** The signal ("this hook
is time-bounded") is confidently true; the caveat (it is bounded at 83 minutes, above the default) is
invisible without knowing the unit. A unit-of-measure sibling of the archetype the epic already
tracks: a plausible-looking value silently 1000× off, with nothing in the surrounding code or the
emitted JSON revealing the discrepancy.

## Deliverables

1. **D1 — correct the three literals** to `5`, or to whatever bound D2's review settles as correct per
   hook type. ⚠ The right value is a judgement (a `PreToolUse` enforcement hook may warrant a
   different bound than a `SessionStart` render) — do not assume all three are `5`.
2. **D2 — sweep for sibling milliseconds-shaped timeouts.** ⛔ **Population-derived across every
   emitted hook/config surface in the bundles, not the three sites this spec names.** Report the
   divergent count separately from the number of emit sites examined.
3. **D3 — a test that fails pre-fix.** Assert every emitted hook timeout falls within a plausible
   seconds range. ⚠ **Population-derived over the emit sites** — the guard is only meaningful if it
   covers every site rather than the three found by one sweep. Include the positive-population
   assertion (the enumerated set is non-empty and contains the three known sites).

## Claim Labels

- OBSERVED (message-supplied, line numbers given): the three `5000` literals at `:537`, `:551`, `:565`.
  ⚠ **Verify by SYMBOL (`_render_entry`, `_capture_entry`, `_enforcement_entry`), not by line number.**
- OBSERVED: the unit and default table, quoted from the official hooks reference.
- OBSERVED: the three `5000`s present in this repo's untracked `.claude/settings.local.json`,
  establishing the emit path is live.
- HYPOTHESIS: other emitted config surfaces carry milliseconds-shaped timeouts — confirm/refute at
  D2's sweep (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`
- HYPOTHESIS: additional emit sites D2 surfaces (verify-at-outline)
- OBSERVED: the corresponding test module under `test/plan-marshall/platform-runtime/`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: ⛔ **PLAN-99 and PLAN-77 both touch `platform-runtime`.** PLAN-99 is currently
  LAUNCHED — **do not pair this with it.** Sequence after PLAN-99 lands, or confirm the sub-surfaces
  are genuinely disjoint at emit time (PLAN-99 instruments metrics; this edits hook provisioning).
- Adjacent to: none

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-013-hook-timeout-unit-confusion.md"
```

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -056

**Component:** `platform-runtime (hook provisioning and hook enforcement)` · **Deliverables after merge: 7** (raised cap is 12).

One component, one file family: the hooks `platform-runtime` writes and the hook logic that judges
agent commands.

- **`-013`** — `claude_runtime.py` provisions every hook entry with `"timeout": 5000`. ✅ **CONFIRMED at
  HEAD: three literals, and every sibling timeout in the same file is in seconds (3 / 5 / 10 / 15)** ⇒
  ≈83 minutes. ⚠ Line numbers have drifted from the spec's `:537/:551/:565` to `:715/:729/:743` —
  **verify by symbol, never by line.**
- **`-056`** — the R1 one-command guard scans for shell metacharacters **without respecting quoting**, so
  the agent **edits the evidence to satisfy a lexer**. The fix already exists 30 lines later in the same
  file (`R2` uses `shlex`).

⭐ **Merged for the component and because both are hook-contract defects the agent silently works
around** — a hook that would hang for 83 minutes and a hook that forces a false command shape are the
same class of *tooling that shapes behaviour without being noticed*. Small merge (7), well under cap.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count at outline; overlapping deliverables COLLAPSE rather than concatenate.**

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
