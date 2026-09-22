# Landing Analysis — PLAN-CIS-001

**Plan**: `content-search-seam` (WS-01) · **PR**: [#1084](https://github.com/cuioss/plan-marshall/pull/1084)
**Merged**: `714130bdb` on `main` — corroborated first-party via `git log`, not from the report
**Analyzed**: 2026-08-03

⭐⭐ **This is the epic's flagship lever (L4a) and the operator's named lookup leg.** It is the first
plan in this epic whose success test was binary and structural rather than a measurement.

---

## 1. The objective, PROBED LIVE (standing rule 2)

Not accepted from the report. Run against merged `main`:

```text
architecture search --content --pattern "FOOTPRINT_UNRESOLVED"
→ status: success   count: 6   files_scanned: 4227
  unreadable[0]:   truncated: false   elided[0]:
```

✅ **The verb exists, executes, and returns the four-field complete-coverage contract**
(`files_scanned` / `unreadable` / `truncated` / `elided`). A dispatched leaf denied `Grep` now has a
sanctioned content-search primitive. **The founding gap of WS-01 is closed and was verified by
execution, not by reading the diff.**

### ⚠ But the probe surfaced something the plan did not report

The six results are **three distinct files, each returned twice** — once under `module: default` and
once under `module: plan-marshall`:

```text
default,source,…/check-artifact-consistency.py,9
plan-marshall,script,…/check-artifact-consistency.py,9      ← same file, different module+category
```

⇒ ⛔ **`count: 6` is a row count, not a file count, and the two differ by the module-attribution
factor.** A caller who reads `count` as *"how many files matched"* is wrong by 2× here. This is the
**same dual-attribution shape as the CIS-027 29-vs-24 reconciliation** — where the reconciliation was
found and recorded. Here it is unlabelled.

⚠ **Not necessarily a defect** — per-module rows may be exactly what a module-scoped caller wants —
but **the field name does not say which question it answers**, and this epic's whole thesis is that
an unlabelled count is a confident number with a hidden caveat. **Recorded as an Open Defect**; the
fix is a labelled field or a documented contract, not necessarily a behaviour change.

## 2. Deliverable fidelity

| # | Claimed | Verdict |
|---|---|---|
| 1 | `architecture search --content` + coverage fields | ✅ probed live |
| 2 | `git grep` enforcement in the PreToolUse hook | reported; not independently probed |
| 3 | Workflow migration off `grep`/`rg` sweeps | reported |
| 4 | Search guidance across agent + concept docs | reported |
| 5 | Complete-coverage contract centralized in `client-api.md` | reported |

**Footprint: an exact 37/37 set match** against the merge commit — recall 1.00, precision 1.00, no
scope creep, through a scope that moved during execute. ⭐ That is the store's usual failure mode and
it did not fire; worth recording as a **success** so the next `references.affected_files` finding is
read against a real baseline rather than an assumed one.

## 3. Residue the plan itself flagged

1. **`search --content` ReDoS is ACCEPTED, not fixed.** A caller-supplied regex has no timeout;
   Python `re` offers none, and both mitigations were judged worse than the gap. ⛔ **The
   carry-forward is the important half**: any future bound MUST be a **reported coverage field**,
   never a silent body-size cap — a silent cap manufactures exactly the confident-false-negative
   defect this plan removed. **Folded into the epic as a standing constraint on the search surface.**
2. **Reviewer-list-as-sample, third sighting.** CodeRabbit named 8 duplication sites; the true
   population was 14 files, and the triage derived it. ⭐ **The triage did the right thing** — this is
   the first sighting in this epic where lesson `2026-08-03-06-002` was applied rather than violated.
3. **Bot coverage was not what the green check reported.** At merge all three bots were stale or
   rate-limited and the final commit `94206f88f` carried **no automated review from any of them**,
   while CodeRabbit's CI check read SUCCESS. The two measured bots found **non-overlapping** bypasses
   in the same function, so neither is redundant. → `review-apparatus`.

## 4. Five defects the retrospectives surfaced — all outliving the plan

1. **The loop-back ceiling reports its own breach**: logged `4 of max 3` *after* iteration 4 had spent
   155K tokens. **A post-hoc detector, not an admission gate.**
2. ⛔⛔ **The re-review that caught 14 unseen findings fired BY ACCIDENT.** At the first review pass 2
   of 3 bots refused, nothing retried, and the step **passed green**. Those 14 findings (two Major)
   surfaced only because an unrelated fix moved HEAD and triggered a `head_dependent` re-fire.
   ⇒ **With a clean self-review round, that branch merges unreviewed.** → `review-apparatus`; it is a
   fifth mechanism for their PLAN-PR-013 convergence.
3. **`sonar-roundtrip` pruned on a footprint that did not exist yet** — the composer logged *"footprint
   unresolvable"* and dropped the step on a `no_code_delta` predicate **in the same second**. The
   realized footprint touched four production `.py` files. ⇒ **A prune predicate evaluated against an
   input the composer had just declared unavailable** — the epic's flagship archetype at the
   composition layer.
4. **The retrospective destroys its own primary input** — it overwrote `status.metadata.session_id`
   with the auditor's session; caught and restored before `enrich` ran. **Left alone it corrupts the
   metrics.**
5. **`RE_ENTRY_COVERAGE` is vacuous at exactly the value it exists to catch** — its precondition is
   the presence of a marker it is meant to detect the absence of.

## 5. Token economics — a NEW lever, distinct from CIS-031

- **6-finalize 3.6M vs 5-execute 0.82M = 4.4×.**
- ⛔⛔ **32% of the phase's recorded dispatch spend went to dispatches that terminated in `error` or
  `blocked_session_restart`.**

⭐ **That 32% is pure waste, not examination depth**, which puts it on the right side of the
anti-goal: it is exactly the *"bytes that buy nothing"* the effort-raise analysis identified as the
legitimate target. **CIS-031 is about scoping re-sweeps; this is about dispatches that produced
nothing at all. Different mechanism, different fix.** → Staged as `PLAN-CIS-035`.

## 6. Process defects in the run itself

- ⛔ **The retrospective was dispatched with `orchestrated: false` without resolving it**, so **7
  lessons went to the GLOBAL store (`2026-08-03-14-001` … `-007`) instead of arriving here as
  `candidate-lesson` messages.** They exist and are not lost — **they are in the wrong store, and
  re-routing them is owed.** ⭐ This is `orchestrator inbox detect` existing and not being called: the
  single detection seam was bypassed rather than wrong.
- ⚠ **A denominator bug in the metrics this run generated**: the 6-finalize row reads
  **`17 of 9 dispatch(es) recorded — complete`**. **17 of 9 is not a ratio**, and it is stamped
  *complete*. → Folded into `PLAN-CIS-011` (dispatch observability).
- ⚠ **The merge mutex was force-released under operator authorization** while this plan was paused
  mid-finalize holding it at `staleness=fresh` — not auto-reclaimable, would never have self-released
  — so `PLAN-TRUTH-047`/#1085 could land. **No action owed; it re-acquires on next finalize entry.**

## 7. Reconciliation actions

- `PLAN-CIS-001` → `shipped`, stamped `pr=1084`, `landing=landings/PLAN-CIS-001.md`,
  `plan_marshall_plan_id=content-search-seam`.
- **New spec `PLAN-CIS-035`** — dispatch waste (the 32%).
- **Open Defects added**: the unlabelled `count` semantics in `search --content`; the owed re-route of
  7 misfiled lessons.
- **Folds**: the `17 of 9` denominator into CIS-011; the ReDoS carry-forward as a standing constraint.
- **Forwarded to `review-apparatus`**: the accidental re-review (fifth mechanism) and the
  three-bots-stale-at-merge observation.
