# PLAN-TRUTH-003: Migration and back-compat shims accumulate with no expiry mechanism

> Renamed from **PLAN-96** on 2026-07-30 (see `plan-id-rename-map.md`). ✅ Its `manage-metrics` deferral
> is DISCHARGED — the gating PR #1059 merged as `dfe7fde0b`.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Migration and back-compat shims in this tree carry **no owner, no version floor, and no removal
trigger**. There is no registry, no marker convention, no plugin-doctor rule, and nothing that ever
fires to say a shim is dead. Give every shim a declared expiry condition, add an edit-time guard so
the next one cannot land unmarked, and sweep the permanent "tolerate the old shape" readers — either
recording a concrete floor and trigger, or deleting where the tolerated shape can be shown extinct.

Source: PLAN-92's inbox message `one-coherent-automated-review-contract-001.md`, raised at its
phase-3-outline operator review. The operator explicitly scoped this as a SEPARATE plan, not a
PLAN-92 deliverable.

## The defect

The two shim shapes are not equally bad, and the distinction drives the whole plan:

- **Category A — one-shot migrations that self-disarm.** They expire by construction: the migration
  deletes the legacy key, so a second run is indistinguishable from never having had one.
- **Category B — permanent "tolerate the old shape" read paths.** These **never disarm**. They are
  the half that actually accumulates, and each one silently widens the accepted input surface of
  every reader downstream of it.

**The theme fit:** a shim reads as defensive correctness while being undeletable by construction —
nobody can prove it is safe to remove, because nothing records what it was tolerating or since when.
Confident signal, hidden caveat.

## ⛔ ORCHESTRATOR CORRECTION — the inbox inventory is a LEAD and one entry is already WRONG

The message supplied an inventory of **11 live sites** (5 category A, 6 category B) presented as
"verified inventory — first-party at HEAD". Spot-checking found it is **not** reliable as an
enumeration:

- ✅ **CORROBORATED:** `manage-status/scripts/_cmd_mark_step.py:146` `legacy_string_entry` — exact
  match at the stated line.
- ✅ **CORROBORATED:** `agents/execution-context.md` pin contract (used by the sibling PLAN-TRUTH-002).
- ⛔ **CONTRADICTED:** `manage-metrics/scripts/manage-metrics.py:1057` `_read_status_created`. The
  symbol exists at exactly that line, but the message quotes its docstring as *"safety net for plans
  materialised under older orchestrator versions"* — **that phrase does not appear anywhere in the
  file** (grepped for `older orchestrator`, `safety net`, `materialised`, `materialized`: zero hits).
  The actual docstring describes ordinary defensive `None` handling for missing/malformed
  `status.json` with a renderer fallback. **It may not be a version shim at all.**

This matters beyond one row: the contradicted entry is the message's **flagship example** for its
central argument — "the docstring cites older versions without recording a version floor, so nobody
can prove it is safe to delete". That argument now rests on a quote that does not exist.

**Binding consequence for D0/D3:** the inventory MUST be re-derived first-party before anything is
marked or swept. Do not carry the 11 rows forward as given, and do not assume the count is 11 — it is
neither a floor nor a ceiling. A row that cannot be corroborated is dropped from the sweep, not
marked.

## Deliverables

0. **D0 — re-derive the inventory, population-derived.** Enumerate shim sites from the source tree
   rather than from the message's table. Report the derivation method and the resulting count, and
   state explicitly which of the message's 11 rows survived, which were dropped, and which are new.
   ⚠ **A count of files examined is a VOLUME, not a coverage number** — this epic tracks
   volume-read-as-coverage as a recurring archetype (n=3 surfaces).
1. **D1 — a shim-marker convention.** Every migration / back-compat shim declares, at its definition
   site: an **owner**, a **version floor**, and a **removal trigger**. D1 settles the marker's form
   and where the convention is documented.
2. **D2 — a plugin-doctor rule flagging an unmarked shim.** An edit-time guard so the next shim
   cannot land unmarked. **Population-derived detector, not a hard-coded path list** — copy the
   pattern from `test/_shared/_dispatch_roster.py`. ⚠ The false-positive boundary is the hard part
   and needs test cases in **both** directions: a detector that fires on ordinary defensive
   `None`-handling (see the `_read_status_created` correction above) is a regression, not a win.
3. **D3 — retirement sweep over the surviving category-B sites.** For each: record a concrete version
   floor + removal trigger, **or** delete it outright where the tolerated shape can be shown extinct.
   ⛔ **Do NOT let the sweep degrade into deleting category-B readers without evidence the old shape
   is extinct. Absence of a marker is not evidence the shim is dead** — that inversion is the same
   archetype one level up, inside the fix for it.

Four deliverables, under the split guard.

## Claim Labels

- OBSERVED (orchestrator-verified first-party 2026-07-28): `_cmd_mark_step.py:146`
  `legacy_string_entry` exists as described.
- OBSERVED (orchestrator-verified): the `_read_status_created` docstring quote is **absent** from
  `manage-metrics.py` — the inventory row is contradicted as characterized.
- HYPOTHESIS (message-supplied, NOT corroborated): the remaining 9 inventory rows and the A/B
  split — confirm/refute each at its named file § named symbol during D0 (verify-at-outline).
  **Treat as a sample, not an enumeration.**
- HYPOTHESIS: `_read_status_created` is not a back-compat shim at all but ordinary defensive
  `None`-handling — confirm/refute at `manage-metrics.py` § `_read_status_created` (verify-at-outline).
  If confirmed it is dropped from the sweep and is a useful negative test case for D2.
- HYPOTHESIS: PLAN-92's D3 `enabled_bots` → `required_bots` auto-map is category A (self-disarming) —
  confirm/refute once PLAN-92 lands. It should be marked by D1's convention but is **not a defect and
  does not block PLAN-92**.
- Verify-first clause: D0 re-derives before D1/D3 scope on it. If D0's population-derived count
  diverges sharply from 11, re-scope rather than proceeding against this spec's framing.

## Expected Surface

- OBSERVED: `manage-status/scripts/_cmd_mark_step.py` — `:146` and the sibling tolerate-paths.
- HYPOTHESIS: `manage-config/scripts/_cmd_sync_defaults.py`, `manage-providers/scripts/_providers_core.py`,
  `tools-permission-fix/scripts/permission_fix.py`, `manage-status/scripts/_cmd_assert_step_recorded.py`,
  `manage-metrics/scripts/manage-metrics.py`, `marshall-steward/scripts/determine_mode.py` +
  `gitignore_setup.py` — message-named, each verify-at-outline via D0.
- HYPOTHESIS: `pm-plugin-development` plugin-doctor rule home + tests (D2).
- OBSERVED: tests under `test/plan-marshall/**`.

**Disjointness:** wide but shallow — touches many bundles' script files at their shim sites, plus
`pm-plugin-development` for the doctor rule.
⚠ **OVERLAPS PLAN-92 (in flight) at `marshall-steward`** — the message says so and it is the reason
for the sequencing below. ⚠ Also plausibly overlaps **PLAN-TRUTH-004** (plugin-doctor rule surface) and
**PLAN-81** (population-derived detector work) — check both before pairing.

## Dependencies and Sequencing

- Depends on: **PLAN-92** — ✅ **SATISFIED**: PLAN-92 shipped as **#1041**, so its D3 auto-map is in
  the tree D0 derives its inventory from. This dependency no longer blocks emission (verified
  2026-07-29 against `status.json`).
- ✅ **CROSS-EPIC COLLISION RESOLVED (2026-07-29, same day it was recorded).** PR **#1059 MERGED**
  (`dfe7fde0b`), so the sibling's PLAN-10 is no longer in flight in `manage-metrics` and **the
  constraint below is DISCHARGED** — that file may be edited normally. ⚠ Still **rebase onto #1059
  and re-read the file by symbol before editing**: it changed underneath this spec. ⭐ The constraint
  was live for under two hours, which is the point — **re-verify a cross-epic collision at outline
  rather than trusting a note written at emit time.** Original text retained below as the audit
  record.
- ⛔ ~~**CROSS-EPIC COLLISION — `manage-metrics`, LIVE AT EMIT TIME (2026-07-29).**~~ This spec names
  `manage-metrics/scripts/manage-metrics.py` as a HYPOTHESIS shim site. The sibling epic
  `code-intelligence-substrate`'s **PLAN-10 `end-phase-replace-not-accumulate` is IN FLIGHT in that
  exact file** — PR **#1059** (`fix(manage-metrics): accumulate phase attribution on loop-back`) is
  **OPEN**. Per-epic disjointness does not see this.
  - **Constraint:** while #1059 is open, **do NOT edit `manage-metrics/scripts/manage-metrics.py`.**
    D0 may still *inventory* it read-only — the shim census does not require mutating the file.
  - **If D0's derivation says that site must be edited**, stop and re-check #1059's state. If it has
    landed, rebase onto it and proceed. If it is still open, **defer that ONE site** and record the
    deferral as residue — do not drop it silently, and do not block the other ~6 sites on it.
  - ⚠ **Re-verify #1059 at outline** — it was open when this constraint was written, and a PR that
    lands changes the answer.
- Overlaps with: PLAN-TRUTH-004, PLAN-81 (detector/doctor surface — verify before pairing).
- Adjacent to: PLAN-TRUTH-002 (the sibling message from the same drain) — both want a population-derived
  plugin-doctor detector over a roster. **Co-design the detector pattern; do not build two.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-003-migration-shims-have-no-expiry.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
