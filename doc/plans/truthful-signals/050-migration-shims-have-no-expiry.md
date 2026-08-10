> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Migration and back-compat shims accumulate with no expiry mechanism

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

Migration and back-compat shims in this tree carry **no owner, no version floor, and no removal
trigger**. There is no registry, no marker convention, no plugin-doctor rule, and nothing that ever
fires to say a shim is dead. They accumulate, and nobody can prove any one of them is safe to delete.

The two shim shapes are not equally bad, and the distinction drives the whole plan:

- **Category A — one-shot migrations that self-disarm.** They expire by construction: the migration
  deletes the legacy key, so a second run is indistinguishable from never having had one. These are
  largely fine.
- **Category B — permanent "tolerate the old shape" read paths.** These **never disarm**. They are
  the half that actually accumulates, and each one silently widens the accepted input surface of
  every reader downstream of it.

The theme fit is exact: a shim reads as defensive correctness while being undeletable by
construction. Nobody can remove it, because nothing records *what* it was tolerating or *since when*.
Confident signal, hidden caveat.

⛔ **The starting inventory is a LEAD, and one of its rows is already known wrong.** The finding that
motivated this plan supplied a table of 11 sites (5 category A, 6 category B) presented as a verified
first-party inventory. Spot-checking broke it: the row for `_read_status_created` in
`manage-metrics.py` quotes a docstring phrase — *"safety net for plans materialised under older
orchestrator versions"* — that **does not appear in the file at all**. The actual docstring describes
ordinary defensive `None` handling for a missing or malformed `status.json`. That row may not be a
version shim in any sense.

That matters far beyond one row, because the contradicted entry was the **flagship example** for the
whole argument ("the docstring cites older versions without recording a floor, so nobody can prove
it is safe to delete"). The argument survives; its evidence did not. **The inventory is therefore
re-derived first-party before anything is marked or swept.**

## Goal

Every migration or back-compat shim in the tree declares an owner, a version floor, and a removal
trigger at its definition site; an edit-time rule stops the next one from landing unmarked; and the
surviving category-B readers each carry a concrete retirement condition or have been deleted against
evidence that the shape they tolerated is extinct.

## Deliverables

1. **D0 — GATE: re-derive the inventory, population-derived.** Enumerate shim sites **from the source
   tree**, not from the table above. Report the derivation method, the resulting count, and
   explicitly which of the 11 reported rows survived, which were dropped, and which are new.
   *Done when:* the derived inventory exists with its method stated, and the survived/dropped/new
   partition is reported.
   ⛔ **STOP CONDITION — this deliverable may re-scope the plan.** If the population-derived count
   diverges sharply from 11, or if the category A/B split does not hold, **halt and report that**
   rather than proceeding against this plan's framing. D1 and D3 scope on D0's output, not on the
   numbers written here.
   ⚠ **A count of files examined is a VOLUME, not a coverage number.** Report the population size and
   the hit count separately — volume-read-as-coverage is a recurring archetype in this project.
2. **D1 — A shim-marker convention.** Every migration / back-compat shim declares, at its definition
   site: an **owner**, a **version floor**, and a **removal trigger**. D1 settles the marker's form
   and documents the convention where an author will find it.
   *Done when:* the convention is documented and at least the D0-confirmed category-A sites carry a
   conforming marker.
3. **D2 — A plugin-doctor rule flagging an unmarked shim.** An edit-time guard so the next shim
   cannot land unmarked. **Population-derived detector, not a hard-coded path list** — copy the
   pattern from `test/_shared/_dispatch_roster.py`.
   *Done when:* the rule ships with tests **in both directions** and publishes the population size it
   examined.
   ⚠ **The false-positive boundary is the hard part.** A detector that fires on ordinary defensive
   `None`-handling is a regression, not a win. The `_read_status_created` case above is the ideal
   **negative** test case if D0 confirms it is not a shim — use it.
4. **D3 — Retirement sweep over the surviving category-B sites.** For each: record a concrete version
   floor and removal trigger, **or** delete it outright where the tolerated shape can be shown
   extinct.
   *Done when:* every surviving category-B site is either marked or deleted, and each deletion cites
   the evidence that the old shape is gone.
   ⛔ **Do NOT let the sweep degrade into deleting category-B readers without that evidence. Absence
   of a marker is not evidence the shim is dead** — that inversion is this plan's own defect
   archetype reappearing inside the fix for it, which is a pattern this project has hit repeatedly.

Four deliverables, under the split presumption.

## Out of scope

- **Building a second detector framework.** A sibling plan in this epic (`inert-thinking-directives-
  in-dispatched-docs`) also wants a population-derived plugin-doctor detector over a roster. If both
  are in flight, **co-design one pattern rather than shipping two** — two near-identical detectors is
  a maintenance cost with no compensating benefit. Note the overlap in the report; do not block on
  it.
- **Auditing whether each shim was a good idea when it was added.** The plan gives shims an expiry,
  it does not relitigate their existence. Widening to "should this have been written" turns a bounded
  sweep into an open-ended design review with no operator present to close it.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — the one
  corroborated shim site, plus its sibling tolerate-paths.
- **Candidate sites, each verify-at-D0, none assumed:** `manage-config/scripts/_cmd_sync_defaults.py`,
  `manage-providers/scripts/_providers_core.py`, `tools-permission-fix/scripts/permission_fix.py`,
  `manage-status/scripts/_cmd_assert_step_recorded.py`, `manage-metrics/scripts/manage-metrics.py`,
  `marshall-steward/scripts/determine_mode.py`, `marshall-steward/scripts/gitignore_setup.py` — all
  under `marketplace/bundles/*/skills/`.
- `marketplace/bundles/pm-plugin-development/**` — the plugin-doctor rule's home and its tests (D2).
- `test/plan-marshall/**` — tests.

Wide but shallow: many bundles touched at their shim sites, plus one bundle for the rule.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `_cmd_mark_step.py` contains a `legacy_string_entry` tolerate-path | OBSERVED | that file — locate **by symbol**; the reported line `:146` is a lead |
| The `_read_status_created` docstring does **not** contain the quoted "older orchestrator versions" phrase | OBSERVED | `manage-metrics.py` § `_read_status_created` — re-read it; this is an asserted **absence** and is verified exactly as a presence |
| `_read_status_created` is ordinary defensive `None`-handling, not a back-compat shim | HYPOTHESIS | that same symbol. If confirmed, it drops from the sweep and becomes D2's negative test case |
| The remaining 9 inventory rows exist and split A/B as reported | HYPOTHESIS | each named file § named symbol, during D0. ⛔ **Treat the table as a sample, not an enumeration** |
| The inventory is 11 sites | HYPOTHESIS | D0's derivation. The number is **neither a floor nor a ceiling** — re-derive it |
| `manage-metrics.py` is safe to edit (no in-flight collision) | HYPOTHESIS | git history — a cross-epic plan was in flight in that exact file and landed as `dfe7fde0b`. ⚠ **The file changed underneath this plan: re-read it by symbol before editing, and rebase first** |
| Nothing in the tree already provides a shim-expiry mechanism | HYPOTHESIS | ⛔ an asserted **absence**, and the higher-risk half — search the bundles for an existing marker or registry convention **before** building D1, or the plan ships a duplicate |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1's convention is text whose value is what a later author does with it**, so it gets a **cold
  read**: have the Step 6 verification sub-agent read the documented convention with no other context
  and then mark up two code samples — one genuine category-B shim and one ordinary defensive
  `None`-check — stating which needs a marker. The correct answer is the shim only. If it marks the
  defensive check, the convention's wording has recreated D2's false-positive problem in prose.
- D2's detector must **publish the population size it examined**. Run it and read that number; a rule
  that can report clean from an empty population is exactly the archetype this epic is named for.
- For every D3 deletion, the report must state the evidence the tolerated shape is extinct. A
  deletion with no such statement is a finding against this run, not a completed deliverable.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- **The cross-epic collision that shaped this plan is instructive and worth carrying:** a constraint
  forbidding edits to `manage-metrics.py` was recorded, and was discharged by a merge **under two
  hours later**. The lesson is not about that file — it is that a collision note written at authoring
  time is a lead, and must be re-verified against git at the moment of the edit rather than trusted.
- A sibling plan's auto-map (`enabled_bots` → `required_bots`) is expected to be category A and
  self-disarming. It should acquire a D1 marker, but it is **not a defect** and nothing here blocks
  on it.
- ⛔ **Do not go looking for the orchestrator spec, the inbox message, or any landing record.** They
  live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this
  file.
