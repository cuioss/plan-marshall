envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-28T20:51:14Z

## Finding: hook `timeout` is SECONDS — plan-marshall writes `5000`, disabling the guard it looks like

### What was found

`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` writes `"timeout": 5000` into Claude Code hook entries at three sites:

- `_render_entry()` — line 537 — `SessionStart` title-render hook
- `_capture_entry()` — line 551 — `SessionStart` session-id-capture hook
- `_enforcement_entry()` — line 565 — **`PreToolUse` enforcement hook**

The Claude Code hooks documentation states the unit verbatim: *"Seconds before canceling. Defaults: 600 for `command`, `http`, and `mcp_tool`; 30 for `prompt`; 60 for `agent`."* (<https://code.claude.com/docs/en/hooks>)

So `5000` is **5000 seconds ≈ 83 minutes**, not 5 seconds. The value reads like a milliseconds-intent transcription (5000 ms = 5 s), which is the wrong unit for this field.

### Why it belongs to this epic

Theme match — **confident-signal-hides-a-caveat**, in its numeric form. An explicit `timeout` on a hook entry reads as a deliberate fail-fast guard: a reviewer scanning the config sees a bounded hook and moves on. The number does the opposite of what its presence advertises — it raises the ceiling *above* the platform default of 600s rather than lowering it. The signal ("this hook is time-bounded") is confidently true; the caveat (it is bounded at 83 minutes) is invisible without knowing the unit.

This is a unit-of-measure sibling of the archetype the epic already tracks: a plausible-looking value that is silently 1000x off, where nothing in the surrounding code or the emitted JSON reveals the discrepancy.

### Severity — latent, not active

Stated honestly: this does **not** slow the normal path. A hook that completes promptly is unaffected. The defect is the size of the failure window:

- On the two `SessionStart` hooks, a hang delays session start rather than being killed at ~5s.
- On `_enforcement_entry()` (`PreToolUse`) a hang blocks tool execution for the duration — this is the one with real exposure.

No incident is attributed to this. It is a latent widening of a guard, filed before it produces one.

### Blast radius

`claude_runtime.py` installs these entries into consumer projects, not only the meta-project — so the value propagates wherever plan-marshall provisions Claude Code hooks. The three `5000`s observed in this repo's own (gitignored, untracked) `.claude/settings.local.json` were written by this code path, confirming the emit path is live.

### Suggested disposition

Change the three literals to `5`. Check whether any other emitted hook config in the bundles carries a milliseconds-shaped timeout. Consider a test asserting emitted hook timeouts fall within a plausible seconds range — the population-derived detector pattern applies here, since the guard is only meaningful if it covers every emit site rather than the three found by this sweep.

### Provenance

Surfaced during an ad-hoc investigation into why assistant-reported wall-clock times ran two hours behind system time (cause: UTC-stamped artifacts, unrelated to this finding). The timeout defect was found while verifying the hook-config schema for a proposed `UserPromptSubmit` change; that change was dropped and not applied. Documentation claim verified against the official hooks reference, which supplies both the unit and the per-type default table.
