# Landing Analysis: PLAN-TRUTH-049 — two producers write one marker field in two encodings, and one of them is not ours

epic: truthful-signals
workstream: WS-01
pr: #1125 — https://github.com/cuioss/plan-marshall/pull/1125

> Written by the `analyze` verb from an operator paste, with every material claim
> corroborated first-party before it was recorded. Where the corroboration CONTRADICTED
> the paste, the measurement is recorded and the paste's figure is not.

## Ground-Truth Corroboration Performed

| Claim (paste) | Verdict | Evidence |
|---|---|---|
| PR #1125 merged | corroborated | `ci pr view --pr-number 1125` → `state: merged`, head `feature/two-producers-one-marker-field-two-encodings` |
| Landed on main as `cf70cf787` | corroborated | `git log origin/main` — `cf70cf787 docs(orphaned-at): state existence-only invariant and fix D-1 pin-boundary confound (#1125)` |
| 5 deliverables shipped | corroborated | `git show --stat cf70cf787` — 5 files, 1142 insertions: `marketplace_bundles.py`, `generate_executor.py`, `manage-config/standards/data-model.md`, `tools-script-executor/SKILL.md`, `test_orphan_marker_existence_only.py` (+1027) |
| Worktree removed, tree clean | corroborated | `manage-status list` — plan absent from live plans (archived); `git status --porcelain` clean but for the two long-standing `enriched.json` |
| Pin-trap table (three consumers) | **CONTRADICTED in 2 of 3 rows** | see § The Pin-Trap Claim below |

## Deliverable Fidelity vs Spec

The spec staged **D-1, D0, D1, D2, D3**. The shipped set renumbered to D1–D5 and re-shaped D-1's
method; the mapping is one-to-one with one half of D3 left open.

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| **D-1** — aged-ISO-marker discriminator | **shipped-modified, and the modification is the right one** | The spec's own re-grounding had already declared the wait-and-see test unreachable ("do not re-run the wait; it is the thing that failed"). The run replaced it with a **matched control** — oldest foreign epoch-ms marker (5.39 d) vs oldest ISO marker (5.21 d), both on disk, both unexpired ⇒ no encoding-dependent survival differential ⇒ **outcome (i)**, and the inverted epoch-ms remedy is **refuted, not deferred** |
| **D0** — identify the second writer / establish it is external | shipped-as-specified | Recorded as a stated contract at the write site in `generate_executor.py` (+54) naming the foreign co-producer |
| **D1** — state the existence-only invariant | shipped-as-specified | `marketplace_bundles.py` (+42) at `_partition_version_dirs` and on `select_live_version_dir`'s policy list; `tools-script-executor/SKILL.md` (+21). Placed where the liveness contract already lives, as the spec required — no new document |
| **D2** — a test that FAILS if a consumer parses the content | shipped-as-specified, **and it fired** | `test_orphan_marker_existence_only.py` (+1027), population-derived. TASK-008's fix verified by driving the detector over synthetic sources with **6/6 negative controls confirmed to fail pre-fix** |
| **D3(a)/(b)** — correct the two wrong records | **shipped-partial — the in-repo half only** | `manage-config/standards/data-model.md` (+7) states the correct retention model. The **out-of-band half is still owed**: the two wrong records live in the operator memory store, outside the repo — see Follow-Ups |
| D5 (paste numbering) — retention model at its canonical home | shipped-as-specified | `data-model.md`, the canonical home the spec named |

**No unplanned scope.** The 5-file diff is exactly the declared surface — a notable contrast with
PLAN-TRUTH-011's landing in the same window, which carried ~700 lines of unspecified scope.

**The spec's own scope discipline held.** The spec warned "resist re-inflating it — the value here is
the corrected model, not a normalisation project", and the landed diff is a docs-and-invariant
correction with one enforcement test. It also honoured the write-boundary: nothing was written under
`~/.claude/plugins/cache/`, so no foreign producer's markers were "normalised".

## The Pin-Trap Claim — measured first-party, and the paste's table is stale

The paste reports incident 13 with this table:

| consumer | paste value |
|---|---|
| registry pin | `0.1.1327` — and 1327 is itself orphan-marked |
| executor | `0.1.1331` |
| unmarked dirs | `[0.1.1330, 0.1.1331]` — two, not one |

**Measured at this analysis, double-sampled seconds apart per the standing rule (both samples agreed,
so this is not a read-during-write):**

| consumer | measured value |
|---|---|
| registry `installPath` | `0.1.1327` (14/14 plan-marshall entries) |
| registry `version` | `0.1.1326` — **orphan-marked** (the two-field disagreement recorded at the pre-restart check; the third-party control `frontend-design` still has the two fields in agreement) |
| executor `MARSHALL_VERSION` | `0.1.1331` |
| **sole unmarked dir** | **`[0.1.1327]` — ONE, not two** |

⇒ Two of the paste's three rows are contradicted: `0.1.1327` is **not** orphan-marked (it is the sole
unmarked dir), and the unmarked set is a singleton, not `[1330, 1331]`. Only the executor row
corroborates.

**⭐⭐ AND THE MECHANISM THAT EXPLAINS THE DISAGREEMENT IS THE PLAN'S OWN SUBJECT, OBSERVED LIVE.**
Marker timestamps and directory mtimes place the change to the second:

| dir | marker | content | mtime |
|---|---|---|---|
| `0.1.1326` | marked | `2026-08-08T21:24:10Z` (ISO — ours) | 08-08 23:24 |
| `0.1.1329` | marked | `2026-08-09T03:13:16Z` (ISO — ours) | 08-09 05:13 |
| `0.1.1330` | marked | `2026-08-09T04:34:55Z` (ISO — ours) | 08-09 06:34 |
| `0.1.1331` | marked | **`1786261143967` (epoch-ms — FOREIGN)** | **08-09 09:39:03.967** |
| `0.1.1327` | **UNMARKED** | — | dir mtime **08-09 09:39:03.901** |

At `09:39:03`, within 70 milliseconds, the foreign producer **marked `0.1.1331` and un-marked
`0.1.1327`**. The paste's reading was taken during finalize (~06:00), when `1330` and `1331` were the
newest and `1327` was still marked — **so the paste was correct when taken and was invalidated by the
foreign GC three and a half hours later.** Non-stationarity reproducing for the third recorded time; a
marker reading is a snapshot, never a status.

**⛔⛔ THREE FINDINGS THIS PRODUCES, NONE OF WHICH THE PLAN COULD HAVE SEEN:**

1. **The foreign producer DELETES markers, not only writes them.** The spec's re-grounding flagged a
   "marked → re-marked → UNMARKED" third state the aging model does not contain and asked D-1 to settle
   it. **This observation settles it in the affirmative, with a timestamp.** ⇒ D-1's conclusion
   ("no differential within the observable window") is bounded by a second confound the run did not
   name: **the observable window is truncated by marker RESETS, not only by our own sweep's pruning.**
   The verdict — outcome (i), remedy refuted — is not overturned by this; its stated bound is simply
   wider than recorded. Recorded as a Watch, not as a refutation.
2. **The un-marking tracks the registry `installPath`, not the executor.** The foreign GC left exactly
   `0.1.1327` unmarked — which is precisely the registry `installPath` (14/14). ⇒ **the "sole unmarked
   dir" oracle measures the REGISTRY's opinion, not ours.** This is a mechanism for the pin/orphan
   inversion that no prior incident named: the two consumers are not merely un-synchronised, they are
   **actively driven apart** by a third party that re-anchors on the registry each time it runs.
3. **The live split is therefore executor-vs-everything, and it is armed.** `.plan/execute-script.py`
   pins `0.1.1331`, which the foreign GC orphan-marked at 09:39 in the encoding its own 7-day GC
   parses. Scripts work today; the fuse is ~7 days. This is the `ModuleNotFoundError` failure mode with
   a live fuse — the same shape the spec recorded at `0.1.1325`, one incident later.

**No repair attempted** — registry repair is operator-only (classifier-blocked for the agent), and the
paste correctly records that the run did not attempt it either.

**⚠ A fourth consumer the standing survey does not cover, from the paste's retrospective:** the plan's
own session was seated on orphan-marked `0.1.1304`. This session is seated on `0.1.1327` (the unmarked
dir), so the two disagree — which is itself evidence that **session seating is a per-session snapshot
taken at session start**, and a survey run in one session says nothing about another's seating.

## Metrics and Anomalies

- **Tokens: 6.4M raw / 104.9M billing-weighted.** The ~16.4x ratio is consistent with the verified
  billing formula (`input + output + 1.25*cache_creation + 0.1*cache_read`) and with the corpus finding
  that ~99% of cost is context rather than generation. No re-derivation attempted here.
- **Duration: 6h31m worked.**
- **⛔ 68% of spend was 6-finalize**, driven by **four review rounds and three loop-backs** — for a
  five-file documentation-and-invariant change. This is the epic's own cost signal: the finalize
  apparatus cost roughly twice the plan it was finalizing. Recorded as a Watch; it is a data point for
  the token-reduction priority, not a defect of this plan.
- Anomalies: none in the harness sense — no kills, no retries, no fabricated output.

## Routing and Merge Behavior

- **Review: four rounds, five real defects across three independent mechanisms.** Including the
  **vacuous-guard-reintroduced-by-its-own-fix** archetype — TASK-006's fix reopened the class it
  closed. That archetype now stands at n≥7 and, again, was introduced *by a fix for it*.
- **TASK-008's fix was verified by driving the detector over synthetic sources with 6/6 negative
  controls confirmed to fail pre-fix.** This is the discipline the epic keeps asking for and it
  demonstrably stopped a third recurrence — a guard observed to fire.
- **CI/merge: 21/21 finalize steps, all green; merge queue.** `archive-plan` ran, so the finalize is
  complete and this plan's inbox messages are drainable.
- **Two self-inflicted process defects were fixed at source rather than worked around:** a stale
  `metadata.worktree_sha` that made baseline-reconcile re-count already-merged commits and fire a gate
  on a rebase already done (⭐ **this is PLAN-TRUTH-054's and PLAN-TRUTH-046's exact surface, observed
  live** — see Follow-Ups); and a livelock where branch-cleanup's own trigger comment drew a bot reply
  that blocked its own merge barrier.

## Parallelization Consequences

- **`0.1.1327`'s surface is now free.** PLAN-TRUTH-049 held `marketplace_bundles.py` +
  `generate_executor.py` + `cache_retention.py`. Its landing **unblocks PLAN-TRUTH-069**, which was
  held at `staged` for exactly this reason (three of its four files).
- **PLAN-TRUTH-069 must re-ground against `cf70cf787` before emission** — 049 just rewrote the
  invariant text in two of 069's files, and 069's lever C ("stop writing `.orphaned_at`") now has to
  reckon with a *stated, test-enforced* invariant rather than an undocumented convention.
- No collision was observed between 049 and the two plans running alongside it (`-011` on
  `manage-logging`, `-055` on `manage-metrics`). The disjointness call held.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-049 --status shipped`
- [x] row `pr` stamped — `1125`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-049.md`
- [x] row `plan_marshall_plan_id` stamped — `two-producers-one-marker-field-two-encodings`
- [x] epic.md queue reconciled from status.json
- [x] Watches opened: marker-reset confound on D-1's bound; the 68%-finalize cost signal
- [x] Open Defect updated: pin/orphan inversion — incident 13 re-measured, new mechanism named
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

1. **D3's out-of-band half — OWED, and only the operator's memory store can close it.** Two records
   outside the repo are still wrong: the "7-day `.orphaned_at` retention / keep-oracle = no marker"
   model, and the "`.in_use` is the second marker that identifies the pin" claim. The in-repo half
   landed; **the deliverable is not complete on that alone.** → corrected at this analysis.
2. **The un-marking mechanism (finding 2 above) folds into PLAN-TRUTH-059** — its oracle must now
   reject a fifth shape, and more importantly must state **which consumer it is measuring**, because
   the unmarked-set tracks the registry rather than the executor. → folded.
3. **The marker-reset confound folds into PLAN-TRUTH-069** — lever A (resolve at executor runtime)
   makes the whole class unrepresentable and is strengthened by this observation. → folded.
4. **Six tooling defects routed as inbox messages `-001…-009`** — not this plan's diff. The two
   sharpest, per the paste: `review_completeness --participated-bots` silently rejects malformed values
   and still exits 0, **manufacturing a false participation gap indistinguishable from a real one**;
   and **Sourcery's two substantive observations never reached the findings store at all**, one of them
   a hard-coded `parents[3]` root depth (the #894 archetype). ⭐ **Sourcery looked worthless in the
   metrics table and in fact produced the run's only non-overlapping findings** — a measurement that
   inverts a retirement decision the operator has already had to make twice. **Both are PR/review
   subject matter ⇒ they route to `review-apparatus`, not here.** Left in the inbox for the drain,
   which owns the routing.
5. **The worktree_sha defect was fixed in-run.** PLAN-TRUTH-054 and PLAN-TRUTH-046 both own that field.
   Whichever runs next MUST re-ground against `cf70cf787` — a fix landed inside another plan's PR is
   exactly the "already fixed, still staged" shape the 07-04 review sweep found eight instances of.
