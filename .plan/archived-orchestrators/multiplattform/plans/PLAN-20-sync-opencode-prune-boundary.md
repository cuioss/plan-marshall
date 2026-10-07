# PLAN-20: The `/sync-opencode` prune boundary resolves one bundle per entry

epic: multiplattform
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> Staged from the PLAN-04 post-landing review (operator-prompted), not from the original decomposition.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim, act on what the tree says, and report divergence from the figure stated here.
- **Never edit another plan's surface**, even for an obvious adjacent fix — the neighbour may be running concurrently.
- **Confirm the Expected Surface against the tree as the first action** and report — rather than silently absorb — any file the work turns out to need beyond it.

## Objective

`/sync-opencode` deletes entries from the shared `~/.config/opencode/` directory, so its managed-set
derivation is a **deletion boundary** and every imprecision in it is a deletion defect. PR #1372's
review already caught one: `_derive_synced_bundles` truncated entry names at the first hyphen, so
`plan-marshall-*` collapsed to `plan`, and an unrelated user entry like `plan-my-tool` was classified
as managed and pruned. The fix matches entry prefixes against the exact `marketplace/bundles/`
directory names — but it adds **every** bundle whose name prefixes the entry, and two bundle pairs are
prefix-ambiguous. Make the derivation resolve exactly one bundle per entry: the longest match.

## Deliverables

1. **D1 — Longest-match bundle derivation.** `_derive_synced_bundles` currently does
   `for kb in known_bundles: if name == kb or name.startswith(f'{kb}-'): matched.add(kb)`, adding
   every match. Two prefix-ambiguous pairs exist in the tree — `pm-dev-frontend` /
   `pm-dev-frontend-cui` and `pm-dev-java` / `pm-dev-java-cui` — so a skill directory named
   `pm-dev-java-cui-cui-http` contributes **both** `pm-dev-java` and `pm-dev-java-cui` to the managed
   set. `_is_managed_skill` then returns true for a destination `pm-dev-java-*` entry, and an
   unscoped sync from a source tree carrying only `pm-dev-java-cui` entries prunes `pm-dev-java`
   entries it never synced. Resolve the **single longest** matching bundle per entry instead.
   *Done when:* an entry contributes exactly one bundle to the managed set — the longest match — and
   the `--bundles` early-return path (which returns `{only_bundle}` before reaching the matcher) is
   unchanged.
2. **D2 — Adversarial tests for the ambiguity, red-first.** The existing suite has three preservation
   cases and none of them is prefix-ambiguous, which is why the class survived the review fix. Add
   cases over a **real ambiguous pair**: a source carrying only `pm-dev-java-cui` entries must leave a
   destination `pm-dev-java-*` entry untouched, and a full source carrying both must manage both.
   ⛔ **Derive the ambiguous pair from `marketplace/bundles/` at test time, not from a literal pair
   copied out of this spec** — a hard-coded pair silently stops testing anything the day a bundle is
   renamed.
   *Done when:* each new case fails against the current derivation and passes after D1.

## Out of Scope

- **Any other `/sync-opencode` behaviour** — the singular→plural mapping, `--dry-run`, the
  `opencode.json` path, and the deploy engine are all shipped and verified by PLAN-04. Excluded so a
  one-function correction cannot grow into a re-review of the whole skill.
- **The destination-side safety model** (whether prune should require a manifest rather than a name
  convention). That is a design question this plan deliberately does not open; it fixes the
  convention's precision, not its existence.
- **`author-cloud-plan`'s residual "the template owns …" wording.** Also a `.claude/skills/` hygiene
  item, but a *cloud-lane* concern and recorded as out of epic scope — folding it here would smuggle
  out-of-scope work into an in-scope plan.

## Claim Labels

- OBSERVED: `_derive_synced_bundles` adds every prefix-matching bundle rather than one — read at
  `.claude/skills/sync-opencode/scripts/sync_opencode.py`, the `for kb in known_bundles:` loop, which
  calls `matched.add(kb)` inside the match branch with no longest-match selection.
- OBSERVED: exactly two prefix-ambiguous bundle pairs exist — `pm-dev-frontend` /
  `pm-dev-frontend-cui` and `pm-dev-java` / `pm-dev-java-cui`, derived by scanning
  `marketplace/bundles/` for any pair where one name plus `-` prefixes another. **A lead:** re-derive
  at execution; a new `*-cui`-style bundle changes the set.
- OBSERVED: `_is_managed_skill` returns true when the entry starts with `{bundle}-` for **any**
  bundle in the managed set — read in the same file — which is what turns the over-derived set into a
  deletion.
- HYPOTHESIS: no currently-shipped workflow reaches the defect, because the generator emits all
  bundles and `--bundles` early-returns before the matcher. Confirm/refute at
  `.claude/skills/sync-opencode/scripts/sync_opencode.py` § `_derive_synced_bundles`' `only_bundle`
  early return and § the `main` source-enumeration path (verify-at-outline). ⚠️ **If refuted, the
  severity rises** — a reachable path makes this a live deletion defect rather than a latent one.
- OBSERVED: severity is **lower than the defect review caught**, and the distinction is load-bearing
  for prioritisation — that one deleted *user-managed* content (`plan-my-tool`, owned by no bundle);
  this over-prunes *bundle-managed* entries that a full re-sync restores. No user content is at risk.

## Expected Surface

- OBSERVED: `.claude/skills/sync-opencode/scripts/sync_opencode.py` — D1
- OBSERVED: `test/sync-opencode/test_sync_opencode.py` — D2

## Dependencies and Sequencing

- Depends on: **PLAN-04** (landed, PR #1372) — this plan corrects the derivation that landing shipped.
- **Overlaps with: none.** No other staged spec declares `.claude/skills/sync-opencode/**` or
  `test/sync-opencode/**`; the surface was PLAN-04's alone and PLAN-04 is terminal.
- ⚠️ **Touches no `pyproject.toml`**, unlike PLAN-04 — `test/sync-opencode/` is already registered, so
  this plan does not acquire the PLAN-16 collision that PLAN-04's landing exposed.

## Notes

- The whole plan is one function's selection rule plus its tests. It is deliberately small: the
  correction is mechanical, and the value is in D2's adversarial cases, which are what would have
  caught the original defect before review did.

## Verification

- The full verify gate, read from its exit status **and** its result TOON `status`/`errors[]` — the
  wrapper exits 0 even on failure.
- D2's cases demonstrated **red-first** against the current derivation before D1 lands.
- ⛔ **The generator gate is runnable on this host — invoke it as `./pw generate`.** pyprojectx
  provisions `uv` into `.pyprojectx/` (`[tool.pyprojectx.main] requirements = ["uv"]`); a bare `uv`
  lookup on `$PATH` finds nothing and is the **wrong probe**. PLAN-19's F1 skipped a required
  verification item on exactly that false premise and has been retracted. Do not repeat it.

## Hand-Off Command

⛔ **Non-authoritative.** The canonical emit form for this epic lives in `epic.md` § Queue
annotations; this block is a convenience copy and the ledger wins on any divergence.

```text
Plan: .plan/local/oc-plans/multiplattform/200-sync-opencode-prune-boundary/plan.md
Staged orchestrator spec: .plan/orchestrator/multiplattform/plans/PLAN-20-sync-opencode-prune-boundary.md

Execute it per the runbook at .plan/local/opencode/RUNBOOK.md — it is the working contract
(Step 3 authors the plan from the staged spec; Steps 4–9 then apply). Do not delete the
orchestrator spec; it remains the source record.
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` — the orchestrator owns every ledger write — and
reports its outcome through its PR and its run report.
