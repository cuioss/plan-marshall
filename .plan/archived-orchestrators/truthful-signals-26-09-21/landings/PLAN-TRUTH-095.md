# Landing Analysis: PLAN-TRUTH-095 — finalize-step contract guard residue

epic: truthful-signals
workstream: WS-01
pr: #1339 — merged as `b95d78437`

Drained from the epic inbox (13 messages) on 2026-08-24. **Full ship** — a tracked plan of this epic.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as `b95d78437` | corroborated | `git log origin/main` — `b95d78437 fix(finalize-step): derive guard scope from documented rules, close residue (#1339)` |
| Plan finished, worktree removed | corroborated | absent from `manage-status list` |
| Archived | corroborated | `.plan/local/archived-plans/2026-08-24-finalize-step-contract-guard-residue` |
| 9/9 deliverables | accepted from the report — not per-deliverable re-verified | recorded as verification debt |
| **The landing carried a COMPLETE `landing-facts` block** | **corroborated** | `inbox landing-check` → `complete: true`, `missing_keys[0]` |

⭐⭐ **That last row is the first complete landing block this epic has drained**, against PLAN-TRUTH-075's
which was missing all eight keys. See `PLAN-TRUTH-106`, which it re-scopes.

## What shipped

Nine deliverables closing plan-510 remediation residue: guards that asserted a wider scope than they
examined now derive scope from a documented rule and publish the population examined, and the config
write path refuses a key the read path rejects.

## ⭐⭐ The result worth more than the deliverables: it reproduced its own target archetype 12 times

`pre-submission-self-review` fired **8 times** to reach clean, with 7 prior `failed` outcomes, over
**115 candidates / 20 findings**. **The machinery caught all twelve instances.**

⛔⛔ **THE SHARPEST FINDING IN THE WHOLE RUN, AND IT QUALIFIES THIS ORCHESTRATOR'S OWN PRIOR
ANALYSIS.** One over-claim appeared at **four sites** and was corrected in the order *the tooling could
see them* — docstrings, then assertion messages, then a comment — because **the surfacer emits only
`context: docstring` prose, so two copies were structurally invisible.** The consequence the plan
attached:

> **when a delta's whole content is uncovered prose, the candidate set is byte-identical to the
> previous round's, and a clean verdict certifies nothing.**

⚠ **This orchestrator told the operator one turn earlier that the multi-round loop's `3→2→0→2→1→1`
pattern was "the design working".** That remains true for the delta-vs-full mechanism — but this names
a case the mechanism does **not** cover: a delta whose content the surfacer cannot see produces an
unchanged candidate set, and a clean round over it is vacuous. **A clean delta round is not merely a
filter; it can be a re-run of the previous round.** Recorded as `D-095-a`.

## Cost

**25h14m wall / 9h34m worked / 5.7M dispatched / 145.5M billing-weighted** at `n=6/6`.

⭐ **The plan's own retrospective could see only 63.5M at `population_count: 5` of 6** — 2.3× under —
*"because it correctly identified that it runs before the phase it reports on is closed."* That is R18 /
`-097` DD measured for the third time, and this instance is the sharpest: `6-finalize` alone dispatched
**2,635,188 tokens, 48% of the plan**, more than `5-execute` and `4-plan` combined, and is the phase the
retrospective cannot bill.

## Self-attributed orchestrator defects — recorded, not absorbed

The run named **four defects as its own** and one process miss, rather than filing them against the
plan:

1. **Driving the loop forward past a head-dependent gate**, stranding the quality gate's verdict on a
   superseded tree. ⭐ *"CI covered the merged tree, the local gate's record did not."*
2. **Fixing a finding but never recording it** — it sat `pending` toward the merge gate.
3. **Omitting a required prompt field.**
4. **Running two builds concurrently, manufacturing a fake failure.**
5. **Skipping `lessons-capture`**, caught only while assembling the landing.

⛔ Item 1 is `PLAN-TRUTH-107`'s coupling finding, independently reported by the run as inbox `-012`.

## External review contributed nothing measurable

`automatic-review`: **0 comments — 1 empty, 1 refused, 1 refused-structural.** The PR is **179,695 diff
characters against sourcery's 150,000 cap — 19.8% over**, and a source/test split would have gotten both
halves reviewed since each clears alone. ⇒ Forwarded to `review-apparatus` as `truthful-signals-034.md`
before this drain; the landing corroborates the figures it carried as leads.

## Residue drained — 13 messages, every one dispositioned

| Msg | Subject | Disposition |
|---|---|---|
| `-001` | `direct-gh-glab-usage` publishes a bare zero over a diff empty by construction | **Open Defect `D-095-b`** — unowned |
| `-002` | `enrich` cannot bill the terminal phase | **folded** → `-097` DD (third data point) |
| `-003` | build oracle: 4 clean zeros vs 112 builds / 88.6% of script time | **folded** → `-088` DA (RUNNING) — recorded as `W-095-a` |
| `-004` | no `-5-execute` dispatch-boundary file at all | **folded** → `-097` F2 |
| `-005` | 4 context-load flags `unmeasured` on 11/11 rows | **folded** → `-097` F2 (n=3) |
| `-006` | footprint resolver has no post-merge tier (squash = single parent) | **folded** → `-098` Arm 1 (n=2) |
| `-007` | seated cache `0.1.1240` lags source; nearly filed a false finding | **Open Defect `D-095-c`** + `-106` D0 |
| `-008` | **87.5% of operator turns are momentum, not direction** | **folded** → `-107` D0(b) — **answers it** |
| `-009` | `search --content` allowlist is two FILENAMES; `CLAUDE.md` says otherwise | **Open Defect `D-095-d`** — unowned |
| `-010` | `deploy-target` prescribes parsing TOON its generator never emits | **folded** → `-101` (fifth member) |
| `-011` | `prune-local-and-remote-ref` guards remote absence, not local | **Open Defect `D-095-e`** — unowned |
| `-012` | `mutates_source` above a head-dependent gate | **folded** → `-107` (confirms R78) |
| `-013` | the landing | this record |
