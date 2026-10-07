# Landing Analysis — PLAN-CIS-030

**Plan**: `context-byte-attribution-instrumentation` (WS-04) · **PR**: [#1086](https://github.com/cuioss/plan-marshall/pull/1086)
**Merged**: `9b689d65b` on `main` — corroborated first-party via `git log`
**Analyzed**: 2026-08-03 · **Lever L3 — the measurement prerequisite for the entire token programme**

---

## 1. ✅ D2's hardest requirement is MET — verified by arithmetic, on ONE phase

The spec's binding clause was: *"the attributed total MUST reconcile to the phase total — an
attribution that does not sum back is a second unverifiable number, not a fix for the first."*

Read out of the archived `work/metrics.toon` and summed independently:

| | tokens |
|---|---:|
| `cache_read_attributed_exploration` | 181,995,039 |
| `cache_read_attributed_work` | 2,337,157 |
| `cache_read_attributed_execute` | 58,259,095 |
| `cache_read_attributed_orchestration` | 14,530,028 |
| `cache_read_attributed_unclassified` | 0 |
| `cache_read_unattributed` | 79,910,716 |
| **attributed sum** | **337,032,035** |
| **`cache_read_input_tokens`** | **337,032,035** |
| **delta** | **0** |

⭐ **Exact.** The reconciliation identity holds to the token. **This is a real result and the epic's
first genuinely verifiable instrumentation claim.**

## 2. ⛔ But it is verified on ONE phase of six — and my first check said otherwise

**`6-finalize` is the only phase carrying the attribution group. Phases 1-init through 5-execute
carry no `cache_read_input_tokens` field AT ALL** — the field is **absent**, not zero. For
comparison, #1080's `[1-init]` records `cache_read_input_tokens: 6,808,836` over 652 seconds; this
plan's `[1-init]` ran for **1,707 seconds** and records the field nowhere.

⇒ The five other phases ran under **pre-merge code**. This is the non-self-exercisability rule
(lesson `2026-08-03-06-004`) landing on the instrument itself: `record-metrics` runs at `order: 998`,
after the merge and after the cache sync, so only the finalize bucket was written by the new code.
**Expected, explainable, and not a defect** — but it means **the reconciliation is confirmed n=1
phase**, not six.

⛔⛔ **My own first pass reported "OK" on all six phases.** It read an absent field as `0` and
concluded `0 == 0` reconciles. **I reproduced, inside the verification of this plan, the exact defect
this epic exists to detect** — a check that passes over an empty population being indistinguishable
from a clean pass. Caught by comparing against a pre-fix plan's `[1-init]`, not by the check.

### ⚠ And that makes one shipped design decision worth flagging

The landing message states: *"the attribution group is emitted unconditionally inside every emitted
phase bucket, so a zero there is a MEASURED zero and `0 == 0` reconciles."*

⭐ **Today that is safe, because absent and zero are still distinguishable on disk.** ⛔ **Once every
phase emits the group, they will not be** — a genuinely-zero phase and a phase whose producer failed
will both render `0`, and the reconciliation will pass on both. **The claim "a zero here is a measured
zero" is exactly the assertion this epic refuses to accept from anything else.** It needs the same
remedy the epic prescribes everywhere: **publish the population the zero was computed over.**
Recorded as an Open Defect against the instrument, not as a landing failure.

## 3. ⭐⭐ D3's split is the most consequential number this epic has produced — and it is n=1

D3 separated exploration a substrate could plausibly remove from doc-residency it cannot. On the one
instrumented phase:

| | bytes | share |
|---|---:|---:|
| `exploration_index_answerable_bytes` | 109,531 | **7.0%** |
| `exploration_doc_residency_bytes` | 975,401 | **62.5%** |
| `exploration_unattributed_bytes` | 476,922 | 30.5% |
| total | 1,561,854 | (matches `exploration_result_bytes` exactly) |

⛔⛔ **If this generalises, it materially damages this epic's own value case.** The roadmap's premise
was *"exploration is 76–85% of tool-result bytes"* read as *the substrate can remove most of it*.
This says **only ~7% of exploration bytes are index-answerable**, while **62.5% is doc-residency a
code substrate cannot touch.**

⚠⚠ **DO NOT ACT ON THIS YET, and the reason is specific, not generic caution**: the one instrumented
phase is **`6-finalize`, which is precisely where doc-residency should be HIGHEST** — finalize is
workflow-document-driven by construction. ⇒ **This is plausibly the worst case, not the typical
case.** The phases where a code substrate would help most (2-refine, 5-execute) are exactly the ones
with no data.

⭐ **This is D3 working as designed.** Its spec said the split was *"a deliverable, not an
assumption"* and that *"without it, any saving attributed to the substrate is inflated by
doc-residency it cannot touch."* It has now produced a number that challenges the epic — which is
what makes it worth having. **Staged as `PLAN-CIS-036` to get the same split on the phases that
matter.**

## 4. The plan's own headline, and it is correct

> *"The first measurement this epic shipped cannot yet measure itself."*

All 15 dispatch-boundary rows carry zeroes because **no producer writes those four columns** — which
is exactly the warning `truthful-signals-038` sent while this plan was already at finalize, and which
this orchestrator recorded against the spec **in advance of the landing**. ⇒ **Confirmed as
predicted.** Plus: `6-finalize` never closes, so ~1.16M tokens never fold in (**~34% under-report**);
`2-refine` and the `q-gate-validation` spawns record no dispatch boundary at all.

⇒ ⛔ **Standing consequence: any figure this epic quotes from a pre-fix plan is a FLOOR, not a total.**

## 5. Defects caught in finalize, and the shape they share

Three fixed during finalize, none before it: self-review found subagent `cache_read` spread across
named parent buckets against a doc promising it in the residual; CodeRabbit (**Major**) found the
billing parser treating every `[...]` section as a phase, which would **inflate the corpus
denominator**; CodeRabbit (Minor) found `billing-composition_undercounted` double-counting a plan
tripping two independent tallies.

⭐ **All three are one shape: a predicate stated precisely with the set it ranges over left
implicit.** The preference-emitter and lessons-capture converged on it independently. **Nine tests
pin them including negative controls — because the pre-existing tests passed against defect #1.**

## 6. Two operator judgment calls — both recorded as sound

- **Merged rather than rebased** onto `origin/main` (7 commits over a file set #1083 also touched).
  Squash collapses the history anyway. ✅ Reasonable; `branch-cleanup` had classified
  `overlap_with_content_conflict` with `conflict_count=7` and escalated to the operator rather than
  auto-reconciling, which is the gate behaving correctly.
- **Recorded the pre-push gate honestly** as *"whole-tree pytest timed out locally at 462s, CI green"*
  rather than claiming a local pass. ⭐⭐ **This is the epic's own thesis applied by the operator to
  their own report** — a timeout reported as a timeout, with CI at the same SHA named as the covering
  evidence. **Recorded as a positive instance, not just an absence of a defect.**

## 7. ⛔ The plugin cache staleness BIT, and the near-miss is the finding

**Five separate agents were served `0.1.1240` while the registry pinned `0.1.1288`.** For
`lessons-capture` the two bodies **materially disagreed**: the served one would have called
`architecture enrich` post-merge, **writing tracked source onto `main` with no push path** — the
`#990` defect. Each agent read the pinned body from disk instead.

⇒ ⭐ **The armed defect this orchestrator filed after #1084 has now discharged once and was caught
only by the agents' own defensive read.** Cache is synced to `0.1.1292`; **the operator must restart
the session for the agent registry to pick it up.** Open Defect updated with the near-miss.

## 8. Sourcery — a mechanism, not a mood

**Sourcery hard-refuses above 150,000 diff characters**, and this PR was well past it. ⭐ **That is a
concrete, checkable threshold** and it retires a long-running ambiguity: the repeated "sourcery
unmeasurable / absent" observations across #1077–#1086 have at least one **deterministic** cause, not
only rate-limiting. → Forwarded to `review-apparatus`.

## 9. Reconciliation actions

- `PLAN-CIS-030` → `shipped`, stamped `pr=1086`, `landing=landings/PLAN-CIS-030.md`,
  `plan_marshall_plan_id=context-byte-attribution-instrumentation`.
- **New spec `PLAN-CIS-036`** — get D3's split on the phases that matter (n=1, and the one phase is
  the worst case).
- **Open Defects**: "a zero is a measured zero" needs a published population; the cache-staleness
  near-miss.
- **Two withheld medium-confidence proposals rescued** from the plan directory: the `sonar-roundtrip`
  mis-prune (→ CIS-012, second sighting) and `config_hash` drift firing at **4 of 4** phase
  boundaries — ⭐ *a warning that fires at 100% of boundaries is not a detector* (→ CIS-016).
- **Forwarded to `review-apparatus`**: the Sourcery 150K threshold.
