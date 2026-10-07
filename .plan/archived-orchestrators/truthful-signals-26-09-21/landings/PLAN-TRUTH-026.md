# Landing: PLAN-TRUTH-026 — mandatory plan-id, plan-scoped build results, extended ledger

**PR**: #1075 — merged as `b5477589c` (**corroborated against `origin/main`**)
**Plan id**: `mandatory-plan-id-build-results-ledger` · **Size**: 12 commits, 74 files
**Emitted**: 25 inbox messages (1 landing + 12 findings + 12 candidate-lessons)

⚠ **PR-NUMBER CORRECTION.** This orchestrator's anchor recorded **#1074** for this plan, inherited from
an operator paste and never corroborated. **#1074 is a different PR** (`tools-marketplace-inventory: wire
resolver into arch graph`); ours is **#1075**. The machine authority was never wrong — the queue row was
unstamped until now — but the anchor prose was, for a full day. ⇒ *A landing claim is a lead* applies to
**PR numbers**, not just merge state. Sixth instance.

## Deliverable fidelity vs spec

All four scoped areas landed: `--plan-id` mandatory across the build surface, build results resolving
through `get_build_results_dir` into the owning plan's tree, `kind=build` rows carrying the resolved plan
id, plus a security-audit path-containment guard on the results-directory resolution (2 findings, 5 new
tests green).

⭐ **The `NO_PLAN` sentinel was NARROWED, not removed** — which produced the guard sweep below and is the
better outcome: the spec's D1 framing (an absent value cannot be distinguished from a caller that forgot)
is preserved, while the sentinel keeps a legitimate plan-less path.

⭐ **`finalize-step-simplify` collapsed 8 separate `if not plan_id:`-shaped guard sites into ONE
`names_real_plan` TypeGuard seam** — the real-vs-sentinel distinction is now decided in a single place.
That is this epic's *where a copy exists, delete the copy* rule applied by the machinery itself, and it is
the strongest structural outcome of the plan.

## ⛔⛔ THE LOAD-BEARING RESULT: this landing made a KNOWN OPEN DEFECT WORSE, exactly as predicted

`PLAN-TRUTH-026` did not close `PLAN-TRUTH-010`'s false-fresh hole (a zero-exit `discover` /
`run-config-key` call stamping a `kind=build` **success** row). It was deliberately out of scope. But
D3/D4 changed the bogus row's **attribution**:

| | before #1075 | after #1075 |
|---|---|---|
| bogus `kind=build` row's `plan_id` | `null` | a **real plan id** |
| how the row reads | orphan row, unclear provenance | **that plan's successful build** |

⇒ **The plan-id mandate improved every genuine row and simultaneously removed the only accidental
discriminator the bogus row had.** A `null` plan_id was a weak tell; the row is now fully-formed and
indistinguishable from a real successful build for a named plan.

⭐ **This is the epic's flagship archetype in its purest form to date**: a fix that improves the signal in
the common case **deletes the accidental tell that exposed the broken case**. Nothing regressed in the
fix's own terms — the defect is strictly in what the fix stopped revealing.

⛔ **THE ORCHESTRATOR'S EMIT ADVISORY WAS CORRECT AND WAS NOT ACTED ON.** At emit (2026-08-01) this
orchestrator recorded: *"TRUTH-010 arguably settles 'what is genuinely build-class' FIRST — making
plan-id mandatory on a set that wrongly includes `--help` would harden the misclassification."* The plan
launched anyway and **the predicted harm materialised exactly as described**. Recorded not as blame —
launching was a legitimate operator call on an advisory, not a blocker — but so the next such advisory
carries the weight this one earned.

⇒ **A WINDOW IS OPEN NOW.** Between this landing and `PLAN-TRUTH-010` landing, the change ledger contains
bogus build rows that are **indistinguishable from genuine ones**. Anything that trusts `kind=build`
during this window — the `pre-commit-verify-freshness` gate above all — is reading a corrupted corpus.
**TRUTH-010 is the window-closing plan and is emitted next on that basis.**

## Reconciliation actions

- Queue `running → shipped`; `pr=1075`, `landing`, `plan_marshall_plan_id` stamped via `--set-row`.
- **Surface released**: `script-shared/build`, the executor template `kind=build` writer,
  `manage-change-ledger`, the four build wrappers, `extension-api` build docs.
- **Unblocks**: `PLAN-TRUTH-027` (hard-depended on this landing's `duration_seconds` field) and
  `PLAN-TRUTH-028` (its serialization pair — 028 may now proceed without editing the same call sites
  twice, which was the whole reason for preferring 026 first).
- ⚠ **Also landed, not ours**: #1072 (`extension-api` path-attribution seam) and #1074
  (`tools-marketplace-inventory` resolver wiring). `origin/main` advanced three commits since #1073 and
  only one was ours.

## ⛔ Owed

- **Post-merge PR revisit on #1075** — standing rule, unaffected by anything above.
- **The 12 findings this plan emitted are dispositioned in the 2026-08-02 drain** (see
  `logs/decision.log`), not here.
