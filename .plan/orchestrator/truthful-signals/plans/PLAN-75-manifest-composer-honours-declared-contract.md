# PLAN-75: The Composed Manifest Silently Diverges From The Declared Step Contract — A Step Vanishes, Another Runs Post-Merge

epic: truthful-signals
workstream: WS-01

> Staged from **two independent defects observed in a single finalize run** (PLAN-51 / PR #1009,
> operator-reported 2026-07-26), both orchestrator-verified at HEAD. They share one shape: **the
> declared contract is correct and the composer does not honour it**, while finalize reports
> 20/20 green. Flagship archetype, located in the manifest composer itself.

## ✅✅ DEFECT B IS REAL — REINSTATED 2026-07-27 ON FRESH EVIDENCE. READ THIS FIRST.

**The "believed refuted" verdict recorded earlier on this date is ITSELF REFUTED. Defect B stands.
D0 is DISCHARGED — do not re-run it, and do not re-derive the stale-cache explanation.**

Decisive evidence, orchestrator-verified first-party:

- OBSERVED — plan `2026-07-27-retrospective-checker-assertion-integrity` (PLAN-54 / PR #1015)
  composed a phase-6 manifest whose `execution.toon` sequences
  `lessons-capture` → **`branch-cleanup`** → **`finalize-step-preference-emitter`**
  (lines 31-33), and executed them in that order at **07:06:43** and **07:07:35** on 2026-07-27.
- OBSERVED — **every plugin-cache version live at that composition time declares `order: 61` and
  `mutates_source: true`**: `0.1.1219` (mtime 07-26T21:17), `0.1.1221`, `0.1.1222`. The
  `order: 80` declaration exists ONLY in `0.1.1194`.
- OBSERVED — `0.1.1224` has mtime **07-27T09:00**, i.e. it was written ~2 hours AFTER this manifest
  executed, so it is irrelevant to this composition either way.
- **⇒ A manifest composed against a cache declaring `order: 61` STILL sequenced the step after
  `branch-cleanup` (order 70). The stale-cache explanation cannot account for this. Defect B is REAL.**

### ⚠ Provenance of the error — two orchestrator reversals on this one plan, in opposite directions

1. Defect B was first recorded as **CONFIRMED** from a 2026-07-26 artifact whose composing cache
   version could not be established.
2. It was then recorded as **REFUTED**, on the discovery that cache `0.1.1194` declared `order: 80` —
   a true fact about that cache, **over-generalized into a claim about the defect**. The correct
   conclusion available at the time was narrower: *"that particular artifact cannot serve as proof"*,
   **not** *"the defect does not exist"*. Absence of a usable artifact was treated as evidence of
   absence — the precise error this epic exists to eliminate.
3. A **falsifiable prediction** was recorded with the refutation — *"the step should sort to its 61
   slot and Defect B should close"* — and it was falsified within hours by the next plan to finalize.
   **Recording the prediction is the only reason this was caught quickly; keep doing that.**

**Net effect on scope: Defect A and Defect B are BOTH in scope.** The analysis below the retraction
marker is sound on the mechanism and unreliable on the cause — re-ground the cause at HEAD rather than
inheriting either verdict.

### Corroboration from the field

PR #1015's own finalize narrative independently observed the same inversion and classified it
**"latent-not-triggered"** — correct that nothing cleared the promotion threshold on that run,
**incorrect that it is therefore not a defect**. The consequence it names is exactly this plan's:
*"if a pattern ever does [clear the threshold], the edit lands post-merge and cannot ride the PR."*
A `mutates_source` step scheduled after the merge gate is a latent false-green, not a non-defect.

---

<details>
<summary>Superseded 2026-07-27 — the "believed refuted" block, retained for auditability. Do NOT scope
against it.</summary>

**Everything below about Defect B — including the section headed "HYPOTHESIS REFUTED + corpus
corroboration" that claims Defect B is CONFIRMED — is now believed FALSE. Do not scope against it.**

Surfaced by PR #1014's retrospective and then orchestrator-verified first-party:

- OBSERVED — source `finalize-step-preference-emitter.md:7` → `order: 61`.
- OBSERVED — plugin cache `0.1.1203` / `0.1.1204` → `order: 61` + `mutates_source: true`.
- OBSERVED — **plugin cache `0.1.1194` → `order: 80`, and no `mutates_source` at all.**
- OBSERVED — the plugin cache was **pinned at `0.1.1194`** until a manual fix on 2026-07-27. The
  dormated run this spec cites as its confirming artifact executed **2026-07-26**, under that pin.

**⇒ With `order: 80`, sequencing the step after `branch-cleanup` (order 70) is CORRECT ascending
order. There is no inversion, the composer was faithful, and PLAN-44's fix (#990) is NOT inert.**
The apparent defect was a stale plugin cache declaring a superseded order — the manifest honoured the
contract it was handed.

**Provenance of the error, recorded so it is not repeated:** the "confirmation" was the orchestrator's
own, produced by comparing a *runtime artifact* against *source* while the runtime was reading a
*stale cache*. That is this epic's flagship archetype turned on its author, and it is the **third**
refuted hypothesis on this single plan (after the `default:`-prefix hypothesis, refuted twice over).
**Treat every remaining unverified claim in this spec as suspect until re-grounded at HEAD.**

### D0 — MANDATORY GATE before any other work on this plan

Re-compose the phase-6 manifest at HEAD **against a freshly synced plugin cache** and record where
`finalize-step-preference-emitter` sorts.

- If it sorts to its `order: 61` slot → **Defect B does not exist. Delete it from this plan** and
  re-scope to Defect A alone (which is untouched by this refutation and still stands). Consider
  whether a single-defect plan still merits its queue position.
- If it still sorts late → Defect B is real after a fresh sync, and only THEN is the rest of this
  spec's Defect-B analysis worth reading — re-derived from scratch, not inherited.

⚠ **Why this is not fully closed:** `execution.toon` carries **no manifest/cache version stamp**, so
the pin is established by ledger correlation rather than by the artifact itself. That gap is the more
durable finding — *an execution record that says what ran but not which version composed it is
unfalsifiable after the fact*. Route that observation to **PLAN-64** (manifest observability); it is
the reason this refutation needs D0 instead of simply closing.

</details>

⚠ **The version-stamp gap above SURVIVES the reinstatement and is now better motivated, not less.**
Establishing which cache composed a manifest cost two reversals and a filesystem-mtime correlation.
**`execution.toon` must carry the composing manifest/cache version** — keep that routed to PLAN-64,
and treat it as a prerequisite for trusting any future ordering claim.

## Objective

`manage-execution-manifest` composes the phase-6 step list that finalize actually executes. In one
run it (a) **omitted a step that was configured, enabled, and shown in the posture preview** — so no
retrospective exists for that plan — and (b) **sequenced a `mutates_source` step after the merge
gate** despite its declared `order: 61` placing it pre-merge. Make the composed manifest either
honour every declared step contract or fail loudly when it cannot.

## ⚠ Mechanism — OBSERVED at HEAD, with one labelled HYPOTHESIS

### Defect A — a configured, enabled step is silently absent

- OBSERVED (operator-reported, PR #1009) — `plan-marshall:plan-retrospective` carries `lane: minimal`
  in `marshal.json` and **appeared in the auto-posture preview**, yet the composed manifest omitted
  it. The step never ran and **no retrospective exists for that plan**.
- OBSERVED — finalize reported **20/20 steps done**. Nothing in the run surfaced the omission; it was
  found only by the operator noticing a missing artifact afterwards.
- The preview-versus-composed divergence is the sharp edge: **two renderings of the same decision
  disagree, and only the non-authoritative one was shown to the operator.**

### Defect B — a `mutates_source` step is sequenced past the merge gate, making PLAN-44's fix inert

- OBSERVED — the declared contract is CORRECT:
  `phase-6-finalize/standards/finalize-step-preference-emitter.md` frontmatter carries
  `name: default:finalize-step-preference-emitter`, `order: 61`, `mutates_source: true`.
- OBSERVED — that is exactly what **PLAN-44 (#990)** landed: it moved the step `order: 80 → 61` into
  the post-wait settle band so its write rides the plan PR (see `landings/PLAN-44.md` D2).
- OBSERVED — `phase-6-finalize/standards/required-steps.md:33-44` independently places the step
  between `push` and `create-pr`, far ahead of `branch-cleanup`.
- OBSERVED (operator-reported) — **the composed manifest nonetheless sequenced it after
  `branch-cleanup` (order 70)**, i.e. post-merge. Because it is `mutates_source`, a promotion would
  have landed unpushably on `main`; the running plan correctly skipped the write and logged the
  pattern instead.
- **⇒ PLAN-44's shipped fix is INERT in practice.** The order value it corrected is not what
  actually sequences the step. This is a fix that looks landed, has a passing test, and changes
  nothing at runtime — the archetype at its most expensive.
- ⛔ **RETRACTED 2026-07-26 — the hypothesis below is REFUTED. Read the next section instead; do not
  scope against this bullet.** Retained only so the correction is auditable.
  ~~**HYPOTHESIS (verify-at-outline) — `default:`-prefixed ids are unsortable.**~~
  `_resolve_step_order` (`_manifest_validation.py:314-341`) documents that built-in steps "bare or
  `default:`-prefixed" resolve via `_resolve_standards_path`, but the `_is_external_step` branch
  (`:338-340`) returns `None` for external `bundle:skill` ids. If `_is_external_step` keys on the
  presence of a colon, `default:finalize-step-preference-emitter` takes that branch and resolves to
  `None`. A `None` order makes `_sort_steps_by_frontmatter_order` (`:344-374`) treat the entry as a
  **pinned position** that sortable entries flow around — so it keeps whatever index the config's
  keyed map gave it, which is late. **Confirm/refute at `_is_external_step`** (same module) against
  the literal id `default:finalize-step-preference-emitter`. If confirmed, the defect is
  class-wide: **every `default:`-prefixed step is unsortable**, and the comment at
  `manage-execution-manifest.py:1743` calling this sort "the sole ordering authority" is false for
  that entire class — a **vacuous-authority claim**, the same family as PLAN-73's vacuous ownership
  and PLAN-74's defending comment.

## ⚠ HYPOTHESIS REFUTED + corpus corroboration (2026-07-26 audit, orchestrator-verified)

**Defect B is CONFIRMED in a real composed manifest — and the orchestrator's stated mechanism is
WRONG. Do not chase it.**

- OBSERVED — the dormated plan `2026-07-26-build-queue-fifo-ordering-nondeterminism` carries the
  composed list in **`execution.toon`** (not `status.json`, a small correction to the audit's
  wording). Its `phase_6.steps[19]` reads, in order:
  `… lessons-capture, branch-cleanup, finalize-step-preference-emitter, project:finalize-step-deploy-target …`
  **`branch-cleanup` (order 70) precedes `finalize-step-preference-emitter` (order 61).** PLAN-44's
  fix is inert at HEAD, now confirmed against a real artifact rather than a report.
- OBSERVED — **the composed id is BARE (`finalize-step-preference-emitter`), NOT `default:`-prefixed.**
  The orchestrator's earlier HYPOTHESIS — that `default:`-prefixed ids hit `_is_external_step` and
  resolve to `None` — is **REFUTED twice over**: the id in the manifest carries no prefix, and
  `_resolve_standards_path` strips `default:` via `canonicalize_step_key` (`:251`) anyway, so the
  prefix could never have caused this. **The spec's earlier framing is retracted; a plan that hunts
  `default:` prefixes will find nothing and conclude the defect is absent.**
- OBSERVED — **exactly ONE inversion in a 19-step list.** Every other step is ascending
  (`project:` steps interleave correctly at 4 / 21 / 50 / 81 / 85; `record-metrics` 998,
  `print-phase-breakdown` 999, `archive-plan` 1000 tail correctly). A single misplaced entry amid an
  otherwise-sorted list is the signature of **one step resolving to `None` and being PINNED** by
  `_sort_steps_by_frontmatter_order` (`:344-374`) while the sortable entries flow around it — not a
  class-wide resolver failure.
- OBSERVED — **the parser is not the culprit.** `_read_frontmatter_order` (`:276-308`) partitions on
  the FIRST `:` and compares `key.strip() == 'order'`, so the `name: default:finalize-step-preference-emitter`
  line (a colon inside a value) is skipped harmlessly, and the nested `lane:` block is skipped too.
  The standards doc exists and carries `order: 61`.
- **NARROWED HYPOTHESIS (verify-at-outline) — path resolution, not id shape or parsing.**
  `_resolve_standards_path` builds `_PHASE_6_WORKFLOW_DIR / f'{bare}.md'` then
  `_PHASE_6_STANDARDS_DIR / f'{bare}.md'` from module-level constants. If those constants resolve
  relative to the EXECUTING script's location (the plugin cache) rather than the repo/bundle root the
  step doc actually lives in, `is_file()` fails, the function returns the non-existent `workflow/`
  path, `_read_frontmatter_order` returns `None`, and the step is pinned. **Confirm/refute by
  printing `_PHASE_6_STANDARDS_DIR` and `(_PHASE_6_STANDARDS_DIR / 'finalize-step-preference-emitter.md').is_file()`
  from the executing context.** ⚠ This is adjacent to the known `Path(__file__)` plugin-cache
  resolution bug (#894) — check whether that fix covered this module.
  **Why `finalize-step-preference-emitter` specifically and not its neighbours:** most bare finalize
  steps live in `workflow/`, which is probed FIRST and may resolve; this one lives in `standards/`,
  the fallback probe. That asymmetry is the first thing to test.
- OBSERVED (corpus scale, audit-reported) — `owner_drift` fires on **114 of 115** plans, which
  extends this plan from an ordering defect to an **ownership-class resolution** defect. D1 must
  decide whether the two share one root (a step-identity/resolution seam that answers neither "what
  order" nor "who owns it") or are separate.

**Consequence for D5:** the regression fixture must use `finalize-step-preference-emitter` in its
**bare** form and assert `61` sorts before `70` — a `default:`-prefixed fixture would pass today and
pin nothing, i.e. it would be a vacuous test of the very kind this epic exists to remove.

## Deliverables

### D1 — GATE: establish what the composer owes the declaration (mutates nothing)

Settle the invariant both defects violate: a step that is configured+enabled MUST appear in the
composed manifest, and a step with a resolvable declared `order` MUST be sequenced by it — or the
compose MUST fail loudly rather than emit a divergent list. Decide the failure mode (refuse vs
warn-and-emit) consistently with the fail-closed classifier. Confirm the Defect-B HYPOTHESIS first,
since it determines whether D3 is a one-line predicate fix or a resolution redesign.

### D2 — a configured, enabled step can never be silently omitted

Close Defect A: the composer either includes the step or records an explicit, surfaced reason for
excluding it. **Reconcile the two renderings** — the auto-posture preview and the composed manifest
must be derived from one source, so they cannot disagree; if they must stay separate, the compose
asserts agreement and fails loudly on divergence.

### D3 — every declared `order` actually sequences its step

Close Defect B per the D1 verdict: make `_resolve_step_order` resolve the `default:`-prefixed class
(or whatever the confirmed mechanism turns out to be), so the sort is genuinely the sole ordering
authority its comment claims. **Correct that comment** if the class-wide gap is confirmed — it
currently asserts an authority it does not have.

### D4 — the barrier invariant is asserted, not assumed

A `mutates_source: true` step sequenced after the merge gate is a **fail-closed error**, not a
runtime judgement call the executing plan has to catch. PLAN-51's plan caught it by reasoning; the
next one may not. Ensure `_check_ascending_order` (or a companion) actually fires for this class —
verify it is not itself skipping `None`-order entries, which would make it vacuous in exactly the
same way (`:330-332` documents that `None`-resolving steps "neither break nor satisfy" the check).

### D5 — tests

(a) A configured+enabled step omitted from the composed manifest is detected — the assertion that
fails against today's composer. (b) `default:`-prefixed steps sort by declared order; a fixture with
`default:finalize-step-preference-emitter` (61) and `branch-cleanup` (70) asserts 61 precedes 70,
and is confirmed to FAIL against current code. (c) A `mutates_source` step placed post-merge-gate
trips the D4 barrier. (d) Preview and composed manifest agree for a representative config.

## Expected Surface

- OBSERVED: `manage-execution-manifest/scripts/_manifest_validation.py` — `_resolve_step_order`
  (`:314-341`), `_is_external_step`, `_sort_steps_by_frontmatter_order` (`:344-374`),
  `_check_ascending_order`
- OBSERVED: `manage-execution-manifest/scripts/manage-execution-manifest.py` — the compose path and
  the sole-ordering-authority comment (`~:1733-1748`), the step-selection/lane-filter path (D2)
- HYPOTHESIS: the auto-posture preview renderer — exact module resolved at outline (D2 needs both
  renderings; verify-at-outline)
- OBSERVED: tests under `test/plan-marshall/manage-execution-manifest/**`

**Disjointness:** `manage-execution-manifest` (+ tests). Disjoint from PLAN-69
(`script-shared`/`tools-script-executor`), PLAN-70 (`automatic-review`), PLAN-73
(`marshall-steward`), PLAN-74 (`manage-config`).
⚠ **Adjacent to PLAN-64** (finalize-dispatch-manifest-observability) — same bundle; check overlap
before running them concurrently.

## Dependencies and Sequencing

- No hard dependency. **Priority argument:** Defect A silently destroys retrospective evidence on
  every affected run, and Defect B leaves a shipped fix inert — both are actively costing quality now.
- PLAN-44 is **NOT re-opened**: its source change is correct and stays. This plan makes it effective.

## Notes

- **Two composer defects in one run, same shape:** declared contract correct, composer diverges,
  finalize reports green. The composer is the single point where every step contract is supposed to
  become real, which makes an unfaithful composer unusually expensive.
- **Third instance of the vacuous-authority/ownership family in two days** — PLAN-73
  (`upgrade-flow.md` claims a sub-step owns upstream-skew detection), PLAN-74
  (`_config_defaults.py` comment defends a house-rule violation), and here
  (`manage-execution-manifest.py:1743` claims sole ordering authority). Argues for naming the family
  in the epic vision.
- A fix that ships, passes tests, and changes nothing at runtime (Defect B) is the most expensive
  failure this epic tracks: it consumes a plan, closes the ticket, and leaves the defect live.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
