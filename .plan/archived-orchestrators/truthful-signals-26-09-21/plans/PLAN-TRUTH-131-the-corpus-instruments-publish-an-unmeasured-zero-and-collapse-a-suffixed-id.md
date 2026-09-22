# PLAN-TRUTH-131: The corpus instruments publish an unmeasured zero and collapse a suffixed id

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-03 from inbox drain messages `review-apparatus-023.md` (2026-09-02) and
> `review-apparatus-024.md` (2026-09-03), both **transferred** to this epic by the
> `review-apparatus` orchestrator under the three-way finding rule: the subject is the
> orchestrator's own instrument, not the PR-review apparatus.

## Objective

**Two defects in the `corpus` verb group, both first-party, both found by an orchestrator using its
own instrument to answer a question the instrument silently could not answer.** They share a surface
(`orchestrator.py` plus the shared `epic_spec_parser`) and a failure direction — a payload that looks
complete and well-formed while one of its populations was never measured or was measured under a
collapsed key.

### Member 1 — `corpus cross-check`'s live-plan arm reports a zero it never measured

Derived first-party on 2026-09-02 against `--slug review-apparatus`: `epics_scanned: 9`,
`plans_scanned: 3`, `specs_total: 46`, `specs_comparable: 43`, `file_overlap_match_count: 639`
(492 `corpus_spec` + 147 `sibling_epic_spec` + **0 `live_plan`**).

⛔ **All three live plans were at phase `1-init` and declared no footprint at all**:

| Plan | `manage-references get --field affected_files` |
|---|---|
| `documented-invocations-cannot-succeed-as-written` | `error: field_not_found` |
| `dual-homed-hook-install-renders-identically` | `error: field_not_found` |
| `planning-lane-change-type-scope-execution-manifest` | `error: file_not_found` (no `references.json`) |

So the live-plan arm compared each of 43 comparable specs against an **empty path set**, three times.
**The zero is SILENCE, not a checked negative.**

⭐ **The defect is the ASYMMETRY, not the emptiness.** `corpus cross-check` already publishes a
five-member `spec_surface_states[]` tally over its OWN specs, so one of ours with an indeterminate
surface is visible by construction. It publishes **no equivalent tally for the candidates it compares
them against**. A reader receives `plans_scanned: 3` and cannot distinguish three surface-bearing live
plans from three empty ones — **ADR-019 applied to one side of a comparison and not the other**.

⚠ **Operationally live:** `review-apparatus`'s resume anchor carries a standing instruction to
re-derive the live-plan collision set before every emit, because the reading expires as soon as a live
plan lands. A run following that instruction receives a clean-looking zero with no field telling it the
comparison was vacuous. Two prior sessions recorded real live-plan blocked sets (5 specs blocked on
2026-08-29) from the same verb — **the arm demonstrably DOES produce rows when candidates declare
surfaces**, which is exactly what makes the empty case indistinguishable.

### Member 2 — a letter-suffixed spec loses its suffix, and three specs collapse onto one `plan_id`

Found first-party during a `review-apparatus` cleanup re-grounding pass at HEAD `19453cb1b`:

```
corpus surfaces --slug review-apparatus
  PLAN-PR-025 <- PLAN-PR-025-a-refusal-is-recorded-as-a-refusal-and-the-contract-says-so.md   (retired)
  PLAN-PR-025 <- PLAN-PR-025A-a-refusal-is-recorded-as-a-refusal-the-record.md                (shipped #1368)
  PLAN-PR-025 <- PLAN-PR-025B-arm-the-refusal-recovery-that-has-never-run.md                  (staged)
```

Three distinct specs, three distinct queue rows, **one derived `plan_id`**. `corpus surfaces`'s flat
`claimed[]` list keys by `plan_id`, so a **staged, emittable** spec's declared paths are merged with a
**retired** one's and a **shipped** one's, and a consumer looking up `claimed[]` for `PLAN-PR-025B`
finds no rows at all — **silence, not an empty surface**.

⭐ **It bit immediately and observably:** that pass's intersection sweep scored `PLAN-PR-025B` at `0/0`
declared paths moved and would have recorded it as undisturbed. Its declared surface actually contains
`.plan/marshal.json`, which **did** move in the window. A wrong *undisturbed* verdict on a spec that is
next in the emit queue.

⛔ **Scope it correctly — the write path is FINE.** Two of three surfaces are already correct and must
not be widened:

| Surface | Status |
|---|---|
| `corpus set-verdict --plan PLAN-PR-025B` | **correct** — resolves via `_spec_matches_row` (`orchestrator.py:1119`), `path.stem == plan_id or path.stem.startswith(f'{plan_id}-')`, which matches uniquely |
| the per-spec `corpus surfaces` ROW | **correct** — keys by `spec` filename; reports 025B `declarative`, `claimed_count: 5`, `admits_disjointness_check: true` |
| the derived `plan_id` field, and `claimed[]` keyed on it | ⛔ **wrong** — suffix dropped |

**Root cause is a grammar gap.** The documented plan-id forms (`orchestrator inbox detect`) all require
**trailing digits**: `PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`, `{SLUG}-{DIGITS}`. The letter-suffixed
`025A`/`025B` naming was invented by `review-apparatus`'s own mandatory 025 split and never taught to
the parsers, so id derivation stops at the digit run and drops the suffix.

## Deliverables

1. **D0 — GATE: settle whether letter suffixes are a legal plan-id form at all.** ⛔ **This is a
   DECISION with a recorded asymmetry, not a regex fix.** Either extend the grammar in its single
   detection seam and everything that derives an id from a spec filename, or rule the form out and
   rename — **but renaming is barred for a launched or shipped plan, and `PLAN-PR-025A` is already
   shipped, so the rule-out arm cannot be applied retroactively.** Record the rejected arm and its
   cost. ⛔ Derive the population first: `corpus epics` gives the store, and the sweep must state how
   many letter-suffixed specs exist across ALL epics — the sender checked only `review-apparatus` and
   says so explicitly.
2. **D1 — publish a candidate-side derivation-status tally per `candidate_kind`.** Over the same closed
   five-member vocabulary the own-spec side already uses, so `file_overlap_match_count: 0` states which
   zero it is, for `live_plan` **and** `sibling_epic_spec` **and** `corpus_spec`. ⚠ **The
   `sibling_epic_spec` limb was NOT examined by the sender — it is an unchecked limb, not a clean one**,
   and D1 must treat it as unknown rather than as covered.
3. **D2 — derive the id from the queue row wherever a row is already in hand**, and where a filename
   must be parsed, extend **the single detection seam** rather than adding a second parser. ⛔ The
   marketplace already enforces one reader for `## Expected Surface`; a second id-derivation path is
   the same defect one field over.
4. **D3 — matched negative controls, one per member, and both are load-bearing.**
   - Member 1: **a live plan that DOES declare a footprint and genuinely does not overlap must still
     report a checked negative** — or an unmeasured zero is merely replaced by an unmeasured non-zero.
   - Member 2: **a spec whose id genuinely has no suffix must resolve unchanged** — or a dropped suffix
     is merely replaced by a spurious one.

## Claim Labels

- OBSERVED: the `corpus cross-check --slug review-apparatus` payload figures, quoted from a live read on 2026-09-02.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The spec own verify-first clause says this reading expired (2 of 3 plans now at 6-finalize with real footprints)
- OBSERVED: all three then-live plans returned `field_not_found` / `file_not_found` for `affected_files`, per the three `manage-references` reads the sender ran.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Same expired historical reading per the spec own verify-first clause
- OBSERVED: `spec_surface_states[]` exists for own specs and no candidate-side equivalent is emitted.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: orchestrator.py cmd_corpus_cross_check emits spec_surface_states for own specs only; no candidate-side tally in the returned payload
- OBSERVED: the three-way `plan_id` collapse, read from a live `corpus surfaces` payload at HEAD `19453cb1b`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: epic_spec_parser.plan_id_of collapses PLAN-PR-025A to PLAN-PR-025 via PLAN_ID_PREFIXED_SEGMENT trailing digits -- same id as -025 and -025B
- OBSERVED: `_spec_matches_row` at `orchestrator.py:1119` matches the suffixed stem correctly, and the per-spec row keys by `spec` filename — the write path and the row are not affected.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _spec_matches_row at orchestrator.py:1119 is exactly path.stem == plan_id or path.stem.startswith(plan_id + dash)
- OBSERVED: the three accepted id forms all require trailing digits (`inbox detect` § grammar table).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: epic_spec_parser.py PLAN_ID_PREFIXED_SEGMENT and PLAN_ID_BARE_SEGMENT (lines 87, 95) both end in mandatory digits
- HYPOTHESIS: the `sibling_epic_spec` candidate class has the same candidate-side gap as `live_plan`. ⛔ **NOT checked — the sender states this explicitly and forbids reporting it as found** (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: cmd_corpus_cross_check folds sibling_epic_spec and live_plan into one candidates list; neither gets a per-kind tally
- HYPOTHESIS: other letter-suffixed specs exist elsewhere in the store. ⛔ **NOT checked — only `review-apparatus` was swept. Do not report a population without deriving it** (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: A corpus-wide sweep for other letter-suffixed specs was not independently performed
- Verify-first clause: before D1, confirm the arm still reports `0 live_plan` at current HEAD. The three plans named have since advanced (two are at `6-finalize` with real footprints), so the *specific* vacuous reading has expired even though the *mechanism* has not. A D1 that cannot reproduce the empty case must build one rather than assume it.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Requires running corpus cross-check on review-apparatus, excluded here, and the named plans have since advanced

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — the `corpus cross-check` candidate arms and the id derivation (D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/epic_spec_parser.py` — the single `## Expected Surface` reader (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — the `corpus` and `inbox detect` canonical blocks (D0, D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — the gate's reading contract, if D0 extends the grammar (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/**` — the D3 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⛔⛔ **Overlaps with `PLAN-TRUTH-124` (STAGED, queue head) on `plan-orchestrator/scripts/orchestrator.py` and `test/plan-marshall/plan-orchestrator/`.** `-124` is the unified-ledger-vocabulary clean slate and is first in the emit order. **SERIALIZE behind `-124`** — do not pair, and do not emit this before `-124` lands.
- ⚠ Also overlaps `PLAN-TRUTH-100` and `PLAN-TRUTH-099`, both of which claim `orchestrator.py`. The `orchestrator.py` surface is heavily contended in this queue; **re-run `corpus cross-check` at emit rather than trusting this note**.
- Governing authority for both members: **ADR-019** — *an audit separates what it could not evaluate from what it evaluated and found wanting*.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-131-the-corpus-instruments-publish-an-unmeasured-zero-and-collapse-a-suffixed-id.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-020`** (relayed from Token-Sheriff, observed at the landing of `PLAN-05-retire-cui-http-snapshot-pin`, PRs #697/#698) — *the disjointness gate structurally CANNOT see repository automation, so its `disjoint` verdict is narrower than it reads.*

  ⛔⛔ **This is a POPULATION BOUNDARY, not a data gap, and it widens D1 from “name the zero” to “name the populations”.** The gate compares a spec’s declared surface against exactly three populations — `corpus_spec`, `sibling_epic_spec`, and `live_plan`. **Repository automation is in none of them.** A bot has no spec, no epic and no plan directory, **so it can never produce a row in `file_overlap_matches[]` at ANY `candidate_kind`.** ⇒ *“Every `disjoint` verdict the gate has ever issued has been silent about bot writers, and that silence is indistinguishable from a checked negative”* — ADR-019 applied to the populations themselves rather than to the surfaces within them.

  **What happened:** `PLAN-05` was emitted into a second slot after a clean live-plan reading; its entire real surface was the root `pom.xml`. While it was in flight, `cuioss-release-bot[bot]` opened and merged **PR #696**, changing **that same root `pom.xml`** — the parent version, one line. ⭐⭐ **The parent bump was made TWICE, concurrently, with no coordination, and came out correct ONLY because the two edits were byte-identical**: git absorbed the duplicate at rebase, which is why the merged PR carries 42 deletions and **no `+1.6.0` line at all.** *“Had the bot chosen a different version or reformatted the block, #697 would have hit a merge-queue conflict instead.”* ⛔ **And because the duplicate was absorbed at rebase, `main` retains NO TRACE that the edit was made twice** — the evidence exists only in the pre-rebase branch.

  ⛔ **It is recurring, not incidental:** the same bot moved the same property **three times inside one epic’s life** (`#676`, `#686`, `#696`), with dependabot writing other build files across `#683`–`#692`. **Any repository with dependabot or a release bot has a continuous, unmodelled writer against exactly the shared build files that plans most often declare.**

  ⭐⭐ **A SECOND, independent narrowing of the same verdict was observed in the same epic and is folded into `PLAN-TRUTH-105`:** two concurrent plans collided through the **build timeout budget** while their file surfaces stayed disjoint. ⇒ **A path comparison can represent neither an unmodelled writer nor a shared-resource coupling** — two different directions, one conclusion about what `disjoint` does and does not mean.

  ⭐ **The sender’s own self-criticism is worth keeping, because it is the failure mode this epic exists to remove:** its ledger *“recorded the effect three times and never asked the question”* — it noted the parent had moved twice and concluded only that a parent bump was not the signal to watch for, **never asking WHO was moving it.** *“The data was in the ledger; the question was not asked.”*

  **Direction (the sender explicitly declines to prescribe):** the valuable half is **disclosure, not prevention** — a `disjoint` verdict that NAMED the populations it compared, the way `corpus surfaces` already names `class_tally[]`, would let a reader see that automation was never in scope. Whether the gate should additionally query open bot PRs is heavier and belongs to whoever owns it. ⚠ **The standing mitigation is manual and currently in force in the source epic:** before emitting any plan whose declared surface includes a root or module POM, a BOM, or a workflow file, **check for open bot PRs against it — because the gate will not.**

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§8.2 — `baseline-reconcile` compares BY PATH, so a rename/edit conflict is invisible — and it compounds with a surface omission in the same direction.**

  A plan edited an ADR that an upstream PR **RENAMED** while it was in flight. `baseline-reconcile` reported **`classification=no_overlap, conflict_count=0`** while GitHub reported the PR **`CONFLICTING`**. The orchestrator **auto-proceeded** and learned of the conflict only from GitHub's mergeability state, **after the push**. ⭐ *"The rebase itself was fine — git's own rename detection carried the edit across correctly. The defect is purely in the probe."*

  ⛔⛔ **The compounding half is why this belongs to THIS spec and not only to the git probe:** *"The plan had ALSO under-declared its `## Expected Surface`, so the orchestrator's disjointness gate could not see the overlap either. **A rename defeats the probe; an omission defeats the gate.** Fixing only the probe leaves half of it open."*

  ⇒ **This is a THIRD independent narrowing of the disjointness verdict, alongside the two already folded here**: repository automation is in no compared population (`deployment-and-refresh-gaps-020`), a shared-resource coupling is not a path overlap (`-022`, folded into `PLAN-TRUTH-105`), and now **a path-keyed comparison cannot represent a RENAME.** ⭐ All three say the same thing from different directions — **`disjoint` is a statement about compared path sets, and D1's population disclosure must say which comparisons were possible, not only which returned rows.**

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-143-the-orchestrator-inbox-has-no-delivery-path-and-its-corpus-instruments-publish-an-unmeasured-zero.md` (PLAN-TRUTH-143)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
