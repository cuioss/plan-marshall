# PLAN-TRUTH-102: A dual-homed hook install renders identically to a healthy one

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-102-a-dual-homed-hook-install-renders-identically-to-a-healthy-one.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

The `display` and `hook` health checks read BOTH `.claude/settings.json` and
`.claude/settings.local.json` and report an entry in **either** as present. That merge is correct for its
own purpose — it prevents a false MISSING on a project whose install landed in the other file — but it
means the one state worth surfacing, **an entry in BOTH**, renders identically to the healthy state. Make
a cross-file duplicate reportable as a **divergence**: still not MISSING, but named.

⭐ **This is a reporting change, not a repair.** Migration was offered to the operator on PR #1330 and
**explicitly declined** — silently deleting entries from a version-controlled file is a destructive write
no install flow should perform unprompted. ⛔ **That decision stands and this plan does not reopen it.**
What it closes is the gap the decision leaves behind: an operator on an upgraded project has no way to
learn their install is dual-homed.

## Deliverables

Five deliverables, well under the epic's split guard of 12. D0 is a gate.

**D0 — GATE: settle the three-state reporting vocabulary before writing a detector.** The check today is
binary (present / MISSING). This plan makes it three-valued, and the third value needs a name and a
contract before any code moves:

| State | Today renders as | Must render as |
|---|---|---|
| entry in exactly one file | present ✅ | present ✅ (unchanged) |
| entry in **both** files | **present ✅** — indistinguishable | **divergence** — named, non-fatal |
| entry in neither | MISSING | MISSING (unchanged) |

⛔ **A divergence is NOT a failure.** It must not fail the health check, must not block any flow, and must
not trigger a repair. It is an observation an operator can act on. Settle where it renders and in what
vocabulary, consistent with how this codebase already reports non-fatal observations.

**D1 — detect the cross-file duplicate at the read side.** `_merge_display_settings`
(`claude_runtime.py:618`) states in its own docstring that *"Per-event `hooks` entry lists are
concatenated; the first present `statusLine` and each first-seen `env` key win"* — so **there is no
cross-file de-duplication anywhere**, and both files can simultaneously hold a live render-title entry.
Detect that condition. ⚠ **Detect it WITHOUT changing the merge semantics** — the concatenation is what
makes the either-file read work, and D2 of PLAN-TRUTH-100 is not the only consumer that depends on merge
behaviour staying put.

**D2 — report it, and repair NOTHING.** Surface the divergence in the `display` check and in the `hook`
check (both merge, so both hide it). ⛔ **No migration, no deletion, no rewrite of either settings file** —
see the Objective. The report names which files hold the entry, so an operator can decide.

**D3 — tests: three states, three distinct outcomes, and a matched control.** One case per row of D0's
table, asserting the outcomes are **distinguishable from each other** — not merely that the duplicate case
does not crash. ⭐ **The negative control is the load-bearing one**: an entry in exactly one file must still
report present and MUST NOT report a divergence, because that is the case the old merge was built to
protect and the case a naive duplicate-detector breaks first.

**D4 — record what this plan deliberately does not establish.** The bounded-harm reasoning rests on an
open question and the spec must not launder it: **whether Claude Code EXECUTES two byte-identical hook
entries across settings layers, or collapses them, is UNESTABLISHED** — the sources consulted on PR #1330
disagree. State it in the shipped doc. ⭐ The harm is bounded either way (the render hook is idempotent, so
the worst case is duplicated invocations of a script the codebase itself calls *"among the largest
recurring script costs"*, `claude_runtime.py:966-969`) — **a cost, not a correctness break** — which is
precisely why the divergence report is the right remedy: **it does not depend on the answer.**

## Claim Labels

Checked first-party at HEAD `f6d058b4b` on 2026-08-23; re-ground at the plan's own HEAD before relying on
any one of them.

- **OBSERVED** — `_merge_display_settings` (`claude_runtime.py:618-628`) concatenates per-event `hooks`
  lists with no cross-file dedup, per its own docstring.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: _merge_display_settings is at claude_runtime.py:618 exactly as cited, and its own docstring states 'Per-event hooks entry lists are concatenated' with no dedup
- **OBSERVED** — the merge exists deliberately: the docstring states the `display` check *"must reflect
  entries wherever they legitimately live"* and *"mirrors the `hook` check, which already treats either
  file as authoritative."* ⇒ D1 must preserve it.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Docstring verbatim: the display check 'must reflect entries wherever they legitimately live' and 'This mirrors the hook check, which already treats either file as authoritative.' The merge is deliberate, so D1 must preserve it
- **OBSERVED** — PR #1330 (`92d61b521`, verified on `origin/main`) pinned the terminal-title install to
  `.claude/settings.local.json` for NEW installs, which is what leaves upgraded projects dual-homed. The
  install-side fix is shipped; this plan is the read side only.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: 92d61b521 is PR #1330 'fix(platform-runtime): pin terminal-title hook install to settings.local.json', present on main
- **OBSERVED** — the migration decision was the operator's and was explicit. ⛔ Not reopenable by this plan.
  - verdict: corroborated | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Corroborated against the epic ledger rather than source, which is the only place a decision record lives: the migration was operator-declined on #1330 and is recorded as not reopened
- **UNVERIFIABLE (deliberately)** — whether two byte-identical entries both execute. D4 records it as
  unestablished rather than resolving it; the remedy is chosen so the answer does not matter.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-labelled UNVERIFIABLE (deliberately). D4 records whether two byte-identical hook entries both execute as UNESTABLISHED, and the remedy is chosen so the answer does not matter. This is the correct terminal state, not an open gap
- **HYPOTHESIS** — that the `display` and `hook` checks can share one detector. They merge the same two
  files but may render in different surfaces; if a shared detector forces a worse report in either, split
  it and say why.
  - verdict: unverifiable | checked_at: 31bed3e76 | by: truthful-signals/cleanup | rescoped: n/a | evidence: A detector-sharing design bet resolved at outline; no implementing source settles it today

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py`
- `test/plan-marshall/platform-runtime/test_claude_runtime.py`

## Dependencies and Sequencing

✅ **MACHINE-DERIVED at staging (`corpus cross-check`, 2026-08-23, 150 specs / 7 sibling epics / 7 live
plans).** The hand-written version of this section named one collision and MISSED two; it was replaced.
⛔ Re-derive again at emit time — a running plan's real surface can be wider than its spec.

- **Depends on:** nothing. The install-side pin this complements already landed (#1330 / `92d61b521`).
- ⛔ **`PLAN-TRUTH-086` — 2 files, LIVE COLLISION, SERIALIZE.** `_claude_runtime_impl.py` and
  `test/plan-marshall/platform-runtime/test_claude_runtime.py`. `-086` is `staged`, so neither blocks the
  other today — **but they must never be paired in one `next` block.**
- ⚠ **`code-intelligence-substrate/PLAN-CIS-052` — 1 file, CROSS-EPIC.** `claude_runtime.py`. CIS-052 is
  `staged` and is that epic's **recommended first pair**, so it can start as soon as their operator hold
  lifts. ⭐ Its declared intent on this file is **read-mostly** — *"D2c (read; change only if the seeding
  belongs on the read side)"* — so the likely outcome is no real contention. **Confirm against their live
  queue before emitting**, per the standing rule that a ledger cannot see a duplicate in another ledger.
  ⚠ This epic already holds a separate `-100 ↔ CIS-052` conflict; that one is a contract conflict, this one
  is a file overlap. **They are different problems — do not merge the two records.**
- ✅ **`PLAN-TRUTH-013` — 1 file (`claude_runtime.py`), NOT A CONSTRAINT.** It is `shipped` (PR #1131). The
  overlap is historical and is recorded only so a future reader does not re-flag it as live.
- **Adjacent to:** `PLAN-TRUTH-100` D2 — that plan reads merge behaviour for a different purpose (the
  plan-directed mailbox), and D1 here explicitly preserves the merge semantics it depends on. No file
  overlap, but a shared assumption: **whichever lands second must confirm the other did not move it.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-102-a-dual-homed-hook-install-renders-identically-to-a-healthy-one.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator
owns every other ledger write — and reports its outcome through its PR and its inbox message. The inbox
exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
