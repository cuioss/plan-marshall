envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-05T07:50:19Z

# Follow-up to `truthful-signals-046.md` — the consumer-fleet hypothesis is now CORROBORATED, and the population is 2, not 1

`truthful-signals-046.md` carried this as the one thing it could NOT corroborate:

> **HYPOTHESIS (ours, NOT corroborated here — foreign-repo evidence):** at least one consumer repo is in
> exactly that state and is currently merge-blocked by it.

**It is now OBSERVED, first-party, and the population was DERIVED rather than sampled.**

---

## The derived population — 9 configs walked, 2 carry the retired token

An operator data-point from **TokenSheriff** named itself. Rather than take the instance, this
orchestrator walked **every** `.plan/marshal.json` under `~/git/` — the enumeration, not the anecdote:

| Figure | Value |
|---|---|
| repos walked | 30 |
| carrying a `.plan/marshal.json` | **9** |
| unreadable | **0** |
| carrying `pr-agent` | **2** |
| clean | 7 — `API-Sheriff`, `cui-http`, `cui-jsf-test-basic`, `cui-llm-rules`, `cui-open-rewrite`, `cuioss-parent-pom`, `plan-marshall` |

⛔ **The operator named ONE. There are TWO.** `nifi-extensions` was not in the report.

---

## ⛔⛔ The two are NOT the same severity, and the difference is load-bearing

| Repo | Site | Line | Effect |
|---|---|---|---|
| **TokenSheriff** | `required_bots: "coderabbit,pr-agent"` | `.plan/marshal.json:107` | ⛔ **MERGE-BLOCKED** |
| **nifi-extensions** | `optional_bots: "sourcery,pr-agent"` | `.plan/marshal.json:106` | ⚠ **NOT blocked** — dead config that renders `unregistered_kind` |

**Mechanism, verified first-party at `review_completeness.py`:**

- `:1130-1131` — every bot whose state is in `_UNPROVEN_STATES` joins `unproven_bots`.
- `:1139` — `required_unproven = [b for b in unproven_bots if b in required_set]`.
- `:1147` / `:1149` — `participation_complete` is computed from `required_*` **only**.
- `:310-313` — `unregistered_kind` is a member of `_UNPROVEN_STATES`: *"Blocking exactly as `absent` is
  … so the barrier still fails closed."*

⇒ An **optional** bot in `unregistered_kind` contributes nothing to `participation_complete`. So the
operator's *"every plan fails its review quorum on a spelling"* is **exactly right for TokenSheriff and
does not transfer to nifi-extensions** — and a fleet sweep that treats the two alike will either
over-report a blocked repo or under-report a dead token. Both are wrong in the way this epic cares
about.

---

## What this settles for you

**`PLAN-PR-044` shipped a DETECTOR, and the detector is working exactly as designed.** TokenSheriff is
not evidence against the fix; it is the fix firing. What has no owner is the **migration** half — the
rename invalidated every consumer config fleet-wide and nothing propagated it, so a correct
fail-closed barrier now blocks a repo whose only fault is that nobody edited its config.

- **OBSERVED:** the block is real, reached through a correct code path, and will recur for every future
  plan in that repo until the token is edited.
- **OBSERVED:** the remedy is a one-line config edit per repo — `pr-agent` → `cuioss-review-bot`.
- ⚠ **HYPOTHESIS (NOT corroborated):** these 9 are the whole fleet. The walk covered `~/git/*` on ONE
  machine at depth 1. A consumer checked out elsewhere, on another machine, or nested deeper is
  **outside this population** and its absence from the table is silence, not a clean reading.

⛔ **This orchestrator did NOT edit either config.** Both are foreign repository source, which is
outside the orchestrate-never-implement boundary — the finding is reported, not applied.

---

## Also carried: the fourth report of the scope-creep guard, and it named a miss

Not yours — recorded here only so you do not re-forward it. The same TokenSheriff data-point reported
`scope_creep_check` returning `could_not_look` on **all 10 of its tasks**, the fourth independent
corpus to do so. It carried what the first three lacked: *"it's the guard that would have flagged this
plan's one genuine out-of-footprint edit."* We have **staged it as `PLAN-TRUTH-138`** after three
rounds of leaving it unowned.
