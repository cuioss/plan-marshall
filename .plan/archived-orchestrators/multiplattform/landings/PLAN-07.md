# Landing Analysis: PLAN-07 — runtime facts, prose, and single sources

epic: multiplattform
workstream: WS-03
pr: #1458 (https://github.com/cuioss/plan-marshall/pull/1458)

> Landing record for one shipped plan. Lives at `landings/PLAN-07.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

Drained from `inbox/runtime-fact-prose-and-single-sources-001.md`, corroborated against the merged
diff (`a83389fdb`), the CI abstraction, and the change ledger. **95 files — the largest landing in
this epic, surpassing PLAN-06's 45.**

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| **D1** — layout literals route through the seam | **shipped, and it closed the set cleanup had just re-derived** | `bootstrap_plugin.py` now carries **zero** `'.claude'` constructions. Cleanup (hours earlier, at `8fc353b6e`) had re-derived the live segment-wise set as exactly two sites — `:163` and `:205` in that file. Both are gone. |
| **D2** — terminal-title architecture relocated | **shipped-as-specified** | `manage-terminal-title/standards/` **no longer exists**; `terminal-title-architecture.md` is now at `platform-runtime/standards/`. A genuine relocation, not a copy. |
| **D3** — bundle-wide qualification sweep | **shipped** | Hook-event names, `.claude` literals and ceiling values qualified per target or given runtime citations across the sweep. |
| **D4** — effort table single-sourced | **shipped** | Level→model rows single-sourced to `effort-levels.md`; the cross-target import recorded as a proposal rather than actioned — the correct disposition for a recorded-open question. |
| **D5** — command forms single-sourced | **shipped** | New `script-shared/scripts/command_forms.py` (30 references across 15 files at HEAD). Agent-instructions filename per target with a red-first test; `--settings` literals routed through permission ops. |

## ⛔ My cleanup verdict overstated D5, and the plan used the right unit

Twelve hours before this landing, cleanup re-derived D5's lead and stamped a `contradicted /
rescoped: yes` verdict reading: *"152 hits across 87 FILES … D5 must be scoped against 87 files
rather than an M8 enumeration … weigh the scope-bloat guard before launch."*

**That figure was wrong in its unit.** The probe was a literal content search for `/marshall-steward`,
which counts every textual **mention** — documentation prose, skill bodies, standards — not the
**emission sites** D5 actually targets. The plan scoped against **29 emission sites** and
single-sourced them through `command_forms.py`. Measured at HEAD after the landing: `command_forms`
resolves to 30 hits across 15 files (the extra one being the definition), while the raw
`/marshall-steward` literal still returns 130 hits across 76 files — because the overwhelming
majority of those were always prose, and prose was never D5's target.

⭐ **The plan's unit was correct and mine was not.** The claim's own instruction — *"re-derive by
literal search; the hit list is the work list"* — is what misled the probe, and cleanup inherited
the imprecision instead of catching it. The verdict was right that the §M8 figure was an unchecked
lead; it was wrong about what replaced it. ⛔ **The scope-bloat warning it produced was therefore a
false alarm**, and had the operator acted on it by splitting PLAN-07, the split would have been
made on a phantom.

## ⭐ Zero undeclared across 95 realized paths — the third clean landing running

Realized **95**, declared **10** entries, **0 undeclared**, 4 unrealized. Series: PLAN-11 **15** →
PLAN-10 **19** → PLAN-21 **0** → PLAN-22 **2** → PLAN-06 **0** → PLAN-07 **0**.

⚠️ Same mechanism as PLAN-06, and the same caveat applies: PLAN-07 declared
`marketplace/bundles/plan-marshall/**` plus `test/plan-marshall/**`, so a zero was structurally
guaranteed inside those globs. This is coverage, not precision — and it over-serialized the whole
bundle while the plan was live. The open under-declaration class (a spec declaring a **split** or a
**prose consumer-set**) remains untouched by three consecutive zeros.

All four unrealized entries have positive accounts: `configurable_contract.py` was already **closed**
(cleanup's claim-0 verdict said so, and the plan correctly left it alone);
`manage-terminal-title/standards/terminal-title-architecture.md` was **relocated by D2**, so the
declared path names a location that no longer exists — the declaration was made obsolete by the
plan's own act; `AGENTS.md` and `CLAUDE.md` went untouched.

## ⛔ The change ledger records ONLY FAILURES for this plan — and CI is what settles it

Six build entries exist for this worktree and **every one is a failure**: four `compile
plan-marshall` at `exit -1` / `exit 1`, and two `verify` at `exit -1` / `exit 1`. There is **no
successful local build recorded at all**.

The hand-off explains why, and the explanation holds up: the Step 5 gate first failed on a
pre-existing stale `argparse_surface` disk cache (cleared), and the daemon-mode gate could not build
the worktree project-dir on this host (`pwx` unresolved), so the gate ran via `in_process` — a path
that evidently writes no ledger entry.

⛔ **This is a sharper failure mode than PLAN-06's, and the two must not be filed together.**
PLAN-06's hand-off omitted the gate result while the ledger held it — absent evidence, recoverable.
Here the ledger holds evidence that **actively contradicts** the claim: a reader querying it for
PLAN-07 sees six failures and nothing else. Misleading evidence is worse than missing evidence.

✅ **CI settles it, independently and durably.** `checks status --pr-number 1458`:
`overall_status: success` over 11 checks — `verify / verify` **SUCCESS in 1186s** (a real full run,
not a skip), `verify / conclusion` SUCCESS ×2, `verify / gate` SUCCESS ×2, `generate-check` SUCCESS,
`CodeRabbit` SUCCESS. `Sourcery review` SKIPPED — optional, rate-limited, correctly disclosed.

## ⛔ This also corrects the defect I raised at PLAN-06's landing

At PLAN-06 I recorded that a hand-off omitting the gate result yields an *"unverifiable landing"*,
because the change ledger is machine-local and a reader elsewhere cannot reach it. **That framing
was too strong, and this landing shows why:** CI is queryable by anyone through the same read-side
abstraction, it is durable, and it travels. I checked PLAN-06's PR retroactively — `#1456` is
`overall_status: success` with `verify / verify` SUCCESS. Its landing was never unverifiable; I
reached for the wrong instrument.

⭐ **The correct recovery order is CI first, ledger second** — the reverse of what I did at PLAN-06.
The reporting defect is real and stands (a hand-off should carry its own gate statement), but its
consequence is inconvenience, not unverifiability. The Open Defect is narrowed accordingly.

## Metrics and Anomalies

- **Tokens: not reported.** `complete: false`, `missing_keys: [total_tokens]`. **11-for-11.**
- **Local test count: unavailable** — no successful local build was recorded, so this landing
  contributes no reading to the count series. The CI run's count is not surfaced by `checks status`.
- **Post-merge verify:** the local-gate question is moot here since no local success exists; the
  merge-queue CI run is the gate, and it passed on the head that merged. Merge parent `8fc353b6e`
  (#1456) — this plan merged directly on top of PLAN-06 with nothing in between.

## Routing and Merge Behavior

- **Review — a substantial cycle, and the disposition split is well-formed.** CodeRabbit posted
  **17** comments: **11 fixed** — including three real defects (a `--scope` save bug, the gitignore
  legacy-header migration, and a `repr` serialization fix) — and **6 replied-with-reason**
  (target-awareness, and the recorded `marketplace/targets` proposal). ⭐ Three genuine defects
  caught by review in one PR is the strongest review yield in this epic; a fixed/replied split with
  stated reasons is the correct shape, not a shortfall.
- **CI/merge:** merged via the merge queue as `a83389fdb`, ancestor of `origin/main` confirmed.
  Branch `chore/070-runtime-fact-prose-and-single-sources`. Worktree removed, branch deleted, main
  pulled.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1458`; `landing` `landings/PLAN-07.md`; `plan_marshall_plan_id` `n/a`
- [x] Open Defect opened — the ledger records only failures where the gate was green elsewhere
- [x] Open Defect NARROWED — PLAN-06's "unverifiable landing" framing corrected; CI is the travelling evidence
- [x] Cleanup verdict correction recorded — D5's 87-file figure was a wrong-unit overstatement
- [x] resume_anchor updated; START-HERE and Ordered Queue regenerated

## Follow-Ups

- **F1** ⛔ Two environment findings both sit in **PR #1445's** subject area (`--project-dir` and
  build-gate footguns): the stale `argparse_surface` disk cache, and daemon-mode's inability to
  build the worktree project-dir on this host (`pwx` unresolved). #1445 has now been open across six
  landings and has accumulated a third supporting observation.
- **F2** ⚠️ **An `in_process` gate run writes no change-ledger entry.** That is the mechanism behind
  this landing's misleading ledger state. Recorded as an observation; it belongs to the build-gate
  surface, which no staged spec owns.
- **F3** PLAN-11 residue F2's `plan-retrospective` half — still unowned. **PLAN-12 is the last
  staged plan**; if it does not absorb it, the residue outlives WS-03.
