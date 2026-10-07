# Landing — PLAN-TRUTH-035 `token-total-is-a-partition-labelled-a-whole`

**PR #1083** MERGED 2026-08-03T12:09:31Z, squash `3a20814b1` (parent `e1ae38142`). 13/13 tasks, 7/7
deliverables, 22/22 finalize steps. Verified first-party via `gh pr view`, not from the landing message.

**Cost**: 18h53m wall / **3h17m worked** / **6.3M tokens / 29.5M billing-weighted**. One loop-back,
**five** self-review firings, four verify runs. ⚠ The wall-clock gap is **idle time across sessions, not
compute** — do not read 18h53m as effort.

## What shipped

A **population-labelling discipline**, not a new headline number: a `total_tokens_population`
discriminator (`inline`/`mixed`/`dispatched`) per phase row; `inline_main_context_tokens` as a field of
its own population rather than an addend; a `dispatched unless marked` column header; `(spans
populations)` on a cross-population Total; `(n=k/6)` partiality markers; `billing_weighted_total`
promoted to a first-class cost figure; a key-space guard for the `plan-efficiency.md` calibration anchors
(which had rotted **in both directions at once** — 8 dead rows and 31 live pairs with no row).

⭐ **Operator decisions taken during execution are the authority over the written spec**: relabel rather
than delete; header-level rather than per-cell marking; label-only anchors (key-space completeness, not
values).

## ⛔⛔ The deliverables are OPERATIONALLY INERT IN THEIR OWN OUTPUT — and both reports are true

The operator's report says *"the deliverable is visibly working in its own metrics report … 29.5M
billing"*. Inbox `-008` says the plan's **D4 and D5 are inert**: every phase renders *"coverage
undecidable"* and the `Billing (cost)` column is `-` for all six phases.

**Both are correct, at different sampling points.** `enrich` runs inside `record-metrics` at manifest
position **20**; `plan-retrospective` consumes its output at position **17**.

| Reader | Sees |
|---|---|
| `plan-retrospective` (17) | no `subagent_samples`, no four-field usage, **no `billing_weighted_total`** |
| `record-metrics` (20) | populates them — hence the operator's 29.5M |

⇒ ⭐⭐ **A plan about measurement truth audited itself against a stale, un-enriched store.** Its
`metrics.md` was **~3 hours stale at read time** (`Generated: 09:22:33Z`; finalize ran to 12:39) and
understated `6-finalize` by **~1.03M tokens** (`dispatch_boundary_total: 1,345,299` on record vs
**2,372,638** across 13 rows on disk).

⇒ **This is `PLAN-TRUTH-050`'s ordering defect, confirmed with the sharpest evidence yet**: the fix
works and its own report cannot show it. Folded there.

## ⛔⛔ CORPUS: the third strike is worse than recorded — the rows are internally IMPOSSIBLE

`-009`, first-party from `work/metrics.toon` for this plan's `5-execute`:

```toon
duration_seconds: 41973.0   # 11h39m … while end_time − start_time = 37m41s
close_count: 3
total_tokens: 1961416       # … alongside tool_uses: 0 and agent_duration_ms: 0
```

⇒ Across the third close, **`total_tokens` ACCUMULATED (+37,777) while `tool_uses` and
`agent_duration_ms` were REPLACED with the closing call's zeros.** And `metrics.md` rendered the phase
with `Start: 09:22:33Z`, `End: 07:05:28Z` — **a phase that ends 2h17m before it starts.**

⛔ **`partial: false` certifies this row as complete**, because the partiality contract keys "recorded"
off the presence of an `end_time` — which a re-entered phase has.

⇒ ⛔⛔ **Our n=47 corpus reads exactly these fields.** The mechanism is no longer "rows are missing"; it
is **mixed accumulate/replace semantics producing rows that cannot be true**. Recorded as **strike 4**,
and it subsumes strikes 1–2 rather than adding to them: *the per-phase figures are not merely
under-counted, some are arithmetically impossible.*

✅ **What still survives, and only this**: the **billing composition** (`cache_read` ≈76% / `output` ≈1%)
is a ratio over components that a corrupted row distorts together. **"99% of cost is context" holds.**
Everything per-phase is retired as evidence until re-derived.

## ⭐ The bots caught what five self-review passes did not — twice

- **`-003`**: the fix **reintroduced its own target defect on a second run.** `cmd_enrich` keyed the
  inline fold on `total_tokens` being falsy; run 2 sees the value **run 1 wrote**, falls to the `elif`,
  and re-stamps the row `mixed` — silently dropping the `(spans populations)` marker the plan existed to
  add. ⭐ Caught by **CodeRabbit and pr-agent independently, on the same lines**, with the correct fix.
- **`-004`**: `pre-submission-self-review` fired **three consecutive times, each finding "the last site"
  of one doc cascade, each wrong** (2→3→4 sites). The fourth site sat **18 lines below prose a previous
  pass had just corrected in the same file**. ⭐ **Only the final pass enumerated the population
  (`git log -S`) instead of sampling — and that is the only "nothing further" in the sequence.**

⇒ Both fold into `PLAN-TRUTH-048`. ⭐ The second is the strongest available evidence for its thesis:
**five passes is not five perspectives**, and passes 1–4 cost real tokens to produce three false
closures.

## ✅ Two corrections accepted from the operator's report

1. **CodeRabbit was NOT rate-limited.** Its stored comment body says it declined as an *incremental
   review system that does not re-review already-reviewed commits*, range ending `bfa2a30aa`.
   ⇒ **Waiting would not have helped.** ⭐ The fact that mattered — *it never reviewed the fix commits* —
   held under either mechanism, which is why the decision was still right.
2. **Sourcery refused ONCE, not twice.** The second firing posted **nothing at all** — silence, not a
   substantiated refusal. ⚠ **Exactly the distinction `-004`/PLAN-PR-006 exist to make**: an absent row
   and a refusal must not share a representation.

⭐ Both corrections came from **later agents contradicting earlier ones**, with the later readings better
evidenced. **Recorded as a pattern worth trusting**, not as noise.

## ⛔ Registry pin — 7th incident, and this one defeats the standing mitigation

Cache at **0.1.1289**, pin reads **0.1.1288**, and **every** version dir carries `.orphaned_at` —
including the pin and the newest.

⭐⭐ **`-007` is first-hand from inside a dispatch envelope**: the orchestrator routed `lessons-capture`
to an absolute `0.1.1289` path, and inside that envelope
`Skill: plan-marshall:persona-plan-marshall-agent` resolved to **`0.1.1240`** — **two versions, one
session, one dispatch, 49 versions apart**, with no indication from the loader.

⇒ ⛔ **The standing mitigation ("check the pin before every plan launch") CANNOT cover this** — it fired
**mid-finalize**, hours after any preflight would have passed. **The failure is not in the pin; it is in
what the session's loaded registry serves when asked.** It was caught **by coincidence**, and the
workaround (hand-routing absolute paths) does not survive into the next plan.

**Operator action owed**: `/reload-plugins`, and the pin repaired to 0.1.1289.

## Residue and routing

- **NEW `PLAN-TRUTH-054`** — `baseline-reconcile` anchors on the phase-1 SHA (`-002`). ⛔ **It fired
  twice in this run and was wrong both times, with mutually inconsistent answers**, and one of its
  classifications **auto-merges**.
- **NEW `PLAN-TRUTH-055`** — the metrics record cannot represent a re-entered phase, and its schema
  carries slots nobody writes (`-009`, `-010`, `-012`).
- **Folded**: `-008`/`-011` → `PLAN-TRUTH-050` (ordering + the retrospective **rebinding the session it
  is measuring**); `-003`/`-004` → `PLAN-TRUTH-048`; `-005` → `PLAN-TRUTH-012`; `-006` → archetype
  record; `-007` → the pin memory.
- ⚠ **`lessons-housekeeping` reported `0 removed, 1 promoted, 1 adapted, 186 retained`** — the first
  non-zero disposition since `PLAN-TRUTH-044` was staged. **The three owed trims are still owed.**
