> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-064`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

> ⛔⛔ **PREMISE REFUTED AS STATED — RE-SCOPED 2026-08-08 AT THE FULL RECONCILIATION. READ BEFORE SCOPING.**
>
> The spec asserts *"`references.json` carries **no `affected_files` key at all** — verified first-party
> during `PLAN-TRUTH-047`'s finalize."* **That is not true of the population.** Measured across the
> whole dormated corpus at HEAD:
>
> | Measure | Value |
> |---|---|
> | `references.json` files examined | **246** |
> | carrying `affected_files` | **229** |
> | missing `affected_files` | **17** |
> | present but an EMPTY list | **0** |
> | list sizes | min 1 · median 11 · max 120 |
>
> The key is also **declared in the schema** — `_references_core.py:34` (`affected_files: list[str]`)
> — and the writer surface exists (`manage-references add-list/set-list --field affected_files`).
>
> ⇒ **The defect is NOT an absent key. It is (a) an inconsistently-written key — absent on 17 of 246,
> ~6.9% — and (b) UNDER-RECORDING when present**, which is the independently recorded 19-vs-37 finding:
> a plan whose scope moves during execute keeps the narrower list, so every `affected_files`-derived
> finalize step under-scopes. **Under-recording is invisible in this table** — all 229 look populated.
>
> ⭐ **Why the original claim looked right**: it was verified on ONE plan's finalize, and that plan was
> one of the 17. **A first-party observation of one instance generalised to "at all"** — this epic's own
> standing rule, fired against its own spec.
>
> ⛔ **The remedy changes with the diagnosis.** "Add the missing key" fixes 6.9% of cases and leaves the
> under-recording — the larger and silent half — untouched. **D0 must re-derive both halves**: which
> writers skip the key, and which writers record a list narrower than the realized footprint.
> ⚠ The "three consumers silently under-scope" claim must be re-derived too: consumers reading a
> *present but narrow* list fail differently from consumers reading an *absent* one.

# PLAN-TRUTH-057: `references.affected_files` is absent entirely, and three finalize consumers survive only by accident

epic: truthful-signals
workstream: WS-01

## Objective

`references.json` carries **no `affected_files` key at all** — verified first-party during
`PLAN-TRUTH-047`'s finalize. Three independent finalize consumers read it, and **all three degraded
safely only because each happened to carry a fallback branch.**

⇒ ⛔ **A consumer without a fallback under-scopes silently**, and nothing in the system reports that the
key was missing rather than empty.

## OBSERVED — first-party, three consumers, three different degradations

| Consumer | Behaviour on the missing key |
|---|---|
| `plugin-doctor` | whole-tree fallback — **logged, safe** |
| `pre-push-quality-gate` | whole-tree fallback — **logged, safe** |
| `check-artifact-consistency` | **`inconclusive`** |

⭐ **The third is the interesting one and it is the RIGHT behaviour** — it is exactly the fail-closed
posture `PLAN-TRUTH-010` shipped and `PLAN-CIS-028` reinforced. ⇒ **The defect is not that a consumer
handled it badly; it is that the producer never wrote the key and nothing noticed.**

⚠ **This is a WORSENING of a known defect, not a new one.** The recorded condition was
*under-recording* — `affected_files` populated but incomplete. ⛔ **It is now ABSENT OUTRIGHT.** A
remedy scoped to "improve recall" would not fix a key that does not exist.

## ⭐ Why the safe degradations are the danger, not the reassurance

Two of three consumers fell back to a **whole-tree** scan. That is safe for correctness and **expensive
for cost** — a whole-tree gate on a 29-file footprint is exactly the *bytes that buy nothing* the
token-reduction roadmap targets. ⇒ **The missing key does not merely risk under-scoping; where it does
not under-scope, it OVER-scopes and pays for it.**

⛔ **And the safety is coincidental.** Three consumers, three independently-authored fallbacks. **Nobody
designed a contract; three authors each guessed defensively.** The fourth consumer — whenever it is
written — has no reason to.

## ✅ ANSWERED 2026-08-03 — `PLAN-CIS-034 D4` does NOT cover this. Keep D1.

`code-intelligence-substrate` confirmed: **D4 is `realized_files` — the CAPTURE side only.** It has
`branch-cleanup`/`push` persist the footprint **as it actually was, at the moment it was still true**,
and makes the resolver prefer it. **It says nothing about `references.affected_files` existing.**

⇒ ✅ **D1 stays. Not redundant.** This plan's finding — the key is **absent, not under-populated**, and
three consumers degraded safely **only because three authors independently guessed defensively** — is a
different defect.

⭐ **And the two-producer risk I flagged does NOT arise, for a reason worth stating precisely**: these
are **two different keys answering two different questions** — `realized_files` (what the merge actually
touched, captured) vs `affected_files` (what the plan declared it would touch). ⛔ **`PLAN-TRUTH-049`
needs ONE field with TWO writers; this is TWO fields with ONE writer each.**

⚠ **What must be guarded is NAMING.** ⛔ **If either key drifts toward the other's name, or a consumer
starts FALLING BACK from one to the other, the distinction collapses and it becomes 049.** They have
written that into CIS-034 D4 and asked us to mirror it — **so it is a deliverable constraint here, not a
note**: no consumer may fall back between the two keys, and neither may be renamed toward the other.

## Deliverables

1. **D0 — GATE: derive the producer and the full consumer population, both directions.** Who is supposed
   to write `affected_files`, at what step, and **why it is absent** (never written / written then lost /
   written under another key). ⛔ **Both directions**: every reader of the key, AND every reader that
   *should* consult it and does not. ⚠ **Three consumers is what one plan's finalize happened to hit —
   *a list produced by looking is a sample*.** Derive it.
2. **D1 — the producer writes the key, or the contract says it is optional.** ⛔ **One or the other,
   never neither.** ⚠ If it is genuinely optional, **say so at the consumer contract** so a new consumer
   knows it must branch — today's safety rests on three private decisions.
3. **D2 — absent must be distinguishable from empty.** A footprint that was **not recorded** and one that
   is **genuinely empty** must not share a representation. ⭐ **`inbox list`'s `inbox_state` discriminator
   is the in-repo precedent** (`missing` vs `present, count: 0`) — reuse it rather than inventing a
   shape.
4. **D3 — tests, each verified to FAIL pre-fix.** (a) The key is present after a normal run. (b) A
   consumer given an absent key reports `indeterminate`, never a graded or silently-widened result.
   (c) The D0 consumer population is asserted non-empty and contains all three named consumers.

⚠ Four deliverables, deliberately small. ⛔ **Do NOT widen into footprint-recall quality** — that is a
different question and this plan's key does not exist yet.

## Claim Labels

- **OBSERVED (plan-reported, first-party, "verified first-party" in its own words)**: the key absent from
  `references.json`; the three consumers and their three degradations.
- ⚠ **NOT re-derived by this orchestrator.** ⭐ **Cheap to check** — read a recent archived plan's
  `references.json`. **Do it as D0's first action.** *A corrective is a hypothesis until the named site
  is read.*
- ⛔ **NOT ESTABLISHED**: whether the key was ever written, or regressed. ⚠ **The distinction changes the
  fix entirely** (a producer gap vs a regression), and D0 must settle it rather than assume the
  worsening narrative above.
- **HYPOTHESIS**: only three consumers exist. **Derived from one run's finalize — treat as a sample.**

## Expected Surface

- **HYPOTHESIS**: `manage-references` — the producer and the `references.json` schema
- **OBSERVED (as consumers)**: `plugin-doctor`, `pre-push-quality-gate`, `check-artifact-consistency`
- **HYPOTHESIS**: `phase-6-finalize` — wherever the footprint is supposed to be recorded

## Dependencies and Sequencing

- ⚠ **Adjacent to `PLAN-CIS-034` D4** (*capture, don't derive* — `branch-cleanup`/`push` persists the
  realized footprint). ⭐ **They may be the same fix from two ends**: CIS captures the realized footprint,
  this ensures the declared one exists. ⛔ **Notify and align before implementing D1** — two producers for
  one footprint key is `PLAN-TRUTH-049`'s shape.
- ⚠ Surface-adjacent to `PLAN-TRUTH-055` (record shape) — different store. SERIALIZE if both in flight.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-057-references-affected-files-is-absent-and-three-consumers-silently-under-scope.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
