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

# A config write reports what it meant to do, not what it did

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Three defects share one file and one shape: **`_config_core.py`'s write path returns intent rather
than effect.**

**1. `normalize-keys` reports `normalized` for keys it cannot order.** `order_config_keys` emits the
keys listed in `CANONICAL_TOP_LEVEL_KEY_ORDER` first, then appends *every* unrecognized key
afterwards. The preserve-don't-drop fallback is defensible — **the defect is the signal, not the
fallback.** `normalize_keys` ends with an unconditional `return {'action': 'normalized'}`: a
constant. It has no access to, and does not report, the set of keys that had to be appended, so
"normalized" comes back identically whether the result is canonical or not. And because `save_config`
routes through `order_config_keys`, the append-last behaviour is on **every** write path, not just
this verb.

**2. The one flow that should call it never does.** The `upgrade` verb's Stage 2 `reconcile-config`
runs `sync-defaults` and `steps-sort` — and **not** `normalize-keys`. That call exists only in the
interactive menu's Re-Run Remediation Pass, and `upgrade` bypasses the menu entirely. So the normal
post-version-bump path is *structurally incapable* of producing a canonical key order. That is how a
non-canonical order reached CI and was caught only by key-order tests. This is a **vacuous guard** in
the reachability half: the documentation describes normalize-keys as unconditional, which is true
inside the menu and false for everyone who upgrades via the verb.

**3. `sync-defaults` reports `added_count` from the plan, not the result** — an instance where it
returned `success, added_count: 1` while adding nothing — and **every config write is an unguarded
whole-document read-modify-write**, so a concurrent write is a lost update waiting to happen.

⭐ **These are one defect wearing three faces**, which is why they ship together. A loud
`normalize-keys` that `upgrade` still never calls changes nothing; a wired-up `normalize-keys` that
lies about its result just relocates the false green; and an honest return value on a write that can
silently lose the document is honest about the wrong thing.

**A fourth, adjacent instance in the same skill:** `cache_freshness.py`'s `check_freshness` compares
the cache against the **local clone** manifest with **no upstream leg**. A clone that is itself behind
makes both sides agree ⇒ `fresh`, `refuses_upgrade: false`, and the upgrade runs against a stale world
reporting "nothing drifted" — a green that is *locally consistent* rather than *actually current*.
Worse, the upgrade-flow document asserts that a sub-step **owns** cache-versus-upstream skew and
**nothing implements it** — the same documented-owner-implements-nothing shape as defect 2.

## Goal

Every `marshal.json` write reports what it actually did: `normalize-keys` names the keys it could not
order, `sync-defaults` counts what it added rather than what it planned to add, a concurrent write
cannot silently lose the document, `upgrade` actually runs the canonicalizer, and `check_freshness`
either compares against upstream or declares that it cannot.

## Deliverables

**Group A — the honest return value**

1. **D1 — GATE: settle the honest-signal shape.** Mutates nothing. Decide (a) what `normalize-keys`
   returns when unrecognized keys were appended — the established shape in this epic is a **non-clean
   status naming the offenders**, so prefer `action: 'normalized'` plus `unrecognized_keys: [...]` at
   warning grade over a bare success; (b) whether an unrecognized top-level key is **ever legitimate**
   (a consumer project's own block?) — if yes the signal is a warning, if no it is an error; (c) where
   `normalize-keys` belongs in Stage 2 relative to `sync-defaults` (which may **add** keys) and
   `steps-sort`.
   *Done when:* all three verdicts are recorded with reasons.
   ⛔ **Ordering is load-bearing:** normalizing *before* `sync-defaults` adds a block would
   re-introduce the very defect. Get (c) wrong and D3 ships a no-op.
2. **D2 — `normalize-keys` names what it could not order.** `order_config_keys` (or a thin sibling)
   reports the appended-unrecognized set; `normalize_keys` surfaces it per D1.
   *Done when:* a caller can no longer read `action: 'normalized'` and conclude the file is canonical
   when it is not.
3. **D3 — `sync-defaults` reports effect, not intent.** `added_count` is computed from what the write
   actually changed.
   *Done when:* a `sync-defaults` that adds nothing reports zero, and a test pins that specific
   inversion.
4. **D4 — Guard the whole-document read-modify-write.** Close the lost-update window on the config
   write path.
   *Done when:* two concurrent writes cannot silently drop one side's change, demonstrated by a test.

**Group B — reachability**

5. **D5 — `upgrade` Stage 2 runs the canonicalizer.** Add `normalize-keys` to the Stage 2
   `reconcile-config` sub-steps at D1(c)'s position.
   *Done when:* the post-version-bump flow can produce a canonical order — and the upgrade-flow
   document **and** any emitted `sub_steps` list are updated **in lock-step**.
   ⛔ **Check whether the sub-step list is emitted from code or read from the doc.** If from code, D5
   must edit **both**, or the doc and the behaviour diverge again — which is defect 2 recreated.

**Group C — the freshness signal**

6. **D6 — GATE: decide what `fresh` is allowed to mean.** Mutates nothing. Settle whether an
   upstream-blind comparison may return `fresh` at all, or must declare inapplicability.
   *Done when:* the verdict is recorded.
7. **D7 — Implement D6 in the implementing source.** Give `check_freshness` a real upstream leg, or
   make it declare inapplicability rather than return a confident `fresh`.
   *Done when:* a clone that is itself behind can no longer produce a bare `fresh`.
8. **D8 — Retire the vacuous ownership claim.** Reconcile the upgrade-flow document's assertion that a
   sub-step owns cache-versus-upstream skew to what is actually implemented.
   *Done when:* the document describes only behaviour that exists.
9. **D9 — Correct the remediation text — and the test that pins it wrong.** The current text says
   uninstall + install. That is **wrong**: `/plugin update plan-marshall` is sufficient and
   non-destructive, and must be followed by a version-verify step.
   ⛔ **THE WRONG GUIDANCE IS TEST-ENFORCED** — a test asserts the literal uninstall/install strings.
   This is the **test-pins-the-defect** archetype. **Correct the test with the text, and verify the
   corrected test FAILS against the old behaviour first** — otherwise the fix is unverified.
   *Done when:* the text is right, the test asserts the right thing, and the report records that the
   corrected test was seen to fail before it passed.

**Group D**

10. **D10 — Tests.** (a) A config with a top-level key absent from `CANONICAL_TOP_LEVEL_KEY_ORDER`
    produces D1's non-clean signal **naming that key** — never a bare `normalized`. (b) An
    already-canonical file stays **byte-stable** and reports clean (idempotence preserved). (c) Stage
    2's sub-step list contains `normalize-keys` at the decided position, pinning D5 against silent
    removal. (d) The upstream-skew path. (e) The concurrent-write case.
    *Done when:* all five hold.

⭐ **Split-guard verdict, recorded before hand-over:** **ten deliverables against a raised cap of
twelve.** **No split.** This plan is the *merge* of two previously-serialized plans on the same file,
and the merge exists to resolve a **contested row** — the ordering-bypass concern that belonged to
neither plan alone and could have survived both. Splitting would recreate exactly that gap. ⚠
**Re-count at outline: overlapping deliverables COLLAPSE rather than concatenate** — D2/D3 may prove
to be one honest-return-value change, which is the whole reason the merge was made.

## Out of scope

- **Redesigning `CANONICAL_TOP_LEVEL_KEY_ORDER` itself, or what belongs in it.** The plan makes the
  ordering *honest and reachable*; deciding which keys are canonical is a config-schema question with
  a different owner and no operator here to settle it.
- **A general concurrency framework for every store in the tree.** D4 closes the lost-update window on
  *this* write path. Generalising it is a much larger design with its own risks, and scope-creeping
  into it mid-run would put an unreviewed locking primitive under every skill.
- **Anything in the executor-preflight / version-resolution surface.** Related and compounding — this
  plan's freshness half sits next to it — but it is separately owned. Touching it here would make two
  plans race one story.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` — `order_config_keys`,
  `normalize_keys`, `save_config`, the `sync-defaults` count, and the write path (D2–D4).
- `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — the `normalize-keys` Canonical
  invocations block. ⚠ **plugin-doctor reads this section as source-of-truth**, so a changed return
  shape must be reflected here or the doctor rule diverges.
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` — Stage 2, and
  the vacuous ownership assertion (D5, D8).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` — the Re-Run Remediation Pass
  step, which must stay consistent with the new Stage 2 wiring.
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — **only if** the
  Stage 2 sub-steps are emitted from code rather than read from the doc.
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_freshness.py` — `check_freshness`
  (D7).
- `test/plan-marshall/manage-config/**`, the steward upgrade test module, and the cache-freshness test
  module (D9, D10).

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one — which is worse than a
missing one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count, every
file path, and every asserted absence. ⭐ **Asserted absences are the higher-risk half.** **Labelling
is this run's job, before any deliverable is sized.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `normalize_keys` ends in an unconditional `return {'action': 'normalized'}` | HYPOTHESIS | `_config_core.py` § `normalize_keys` — locate **by symbol**, not by line |
| `order_config_keys` appends unrecognized keys last, and `save_config` routes through it | HYPOTHESIS | that file § `order_config_keys`, § `save_config` |
| `upgrade` Stage 2 runs `sync-defaults` and `steps-sort` but **not** `normalize-keys` | HYPOTHESIS | `upgrade-flow.md` § Stage 2 — an asserted **absence**, verified as a presence |
| `upgrade` bypasses the interactive menu entirely | HYPOTHESIS | `marshall-steward/SKILL.md` § the upgrade verb |
| The Stage 2 sub-step list is emitted from `upgrade.py` rather than read from the doc | HYPOTHESIS | `upgrade.py` § the Stage 2 sub-step table. ⛔ **If true, D5 edits both** |
| `sync-defaults` returned `success, added_count: 1` while adding nothing | HYPOTHESIS | reproduce against the current code; the specific figure is a **lead** |
| Every config write is an unguarded whole-document read-modify-write | HYPOTHESIS | the write path in `_config_core.py` |
| `order_config_keys`'s docstring asserts two routed write paths while **five sites exist and ≥3 bypass it** | HYPOTHESIS | ⛔ **re-derive the site count** — this figure came from a separate investigation and was never re-verified. It is the row that was *contested* between the two merged plans, so it must be **claimed explicitly** in this run's first deliverable and named in the report |
| `check_freshness` compares only against the local clone manifest, with no upstream leg | HYPOTHESIS | `cache_freshness.py` § `check_freshness` — asserted **absence** |
| The upgrade-flow doc claims a sub-step owns cache-vs-upstream skew, and nothing implements it | HYPOTHESIS | that doc, then a search for the implementation — the **absence** is the claim |
| The uninstall/install remediation text is asserted by an existing test | HYPOTHESIS | the cache-freshness test module. ⛔ If true this is **test-pins-the-defect**: the test must be corrected **and seen to fail first** |
| `/plugin update plan-marshall` is sufficient and non-destructive | HYPOTHESIS | operator-supplied correction — ⚠ **not independently verified**; confirm before shipping it as guidance |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D9's corrected remediation text is text-whose-value-is-what-a-reader-does**, so it gets a **cold
  read**: give the Step 6 verification sub-agent only the new text and ask what it would run to
  recover. The correct answer is the non-destructive update plus a version verify. If it reaches for
  uninstall+install, the wording failed.
- ⛔ **D9's test correction must be demonstrated, not asserted.** The report states that the corrected
  test was run against the **old** behaviour and **failed**. A corrected test that was never seen red
  proves nothing.
- **D10(b) byte-stability** is the guard against this fix becoming a reformatter: an already-canonical
  file must come back byte-identical.
- **D10(c)** exists specifically to pin D5 against silent removal — Stage 2 losing the canonicalizer
  again is the failure mode with no other detector.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- **Flagship archetype instance.** A tool returns success while suppressing the caveat that makes the
  answer wrong. Sibling instances already shipped in this project include an omitted-sections report
  under `success`, a routed build reporting false-green, a confident false-negative from a search
  verb, and a title-repaint that reported delivery it never made.
- **This plan absorbed a second plan** that independently found the lost-update and `added_count`
  defects in the same file. The absorbed spec is retained upstream as the record and **must not be
  implemented or emitted separately**. The merge exists because the contested row — writes that bypass
  the ordering authority — belonged to neither plan alone, and an unclaimed row between two serialized
  plans on one file is exactly how a defect survives both.
- ⚠ **Sequencing:** this compounds the residue of the executor-preflight plan in the same epic. If
  that one is still open, note in the report that the version-freshness story has no end-to-end
  truthful signal yet; do not wait on it.
- ⛔ **Do not go looking for the orchestrator spec, the absorbed spec, or any landing record.** They
  live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this
  file.
