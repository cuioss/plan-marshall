# Landing Analysis: PLAN-TRUTH-083 — plugin-doctor detectors report clean over unexamined populations

epic: truthful-signals
workstream: WS-01
pr: #1320 — merged as `8dd6f1a5e`
cloud-run: `cloud-runs/500-plugin-doctor-detectors-report-clean-over-unexamined-populations/`

> A gap-fix plan authored by the epic audit (PR #1298). It shipped with **no `verification.md` and no
> `gaps.md`** — the post-run verification was performed during ingestion on 2026-08-22, to the same
> method as the other 44. All four mutations were snapshotted to `$TMPDIR` and restored by byte-copy
> with md5 verified; the repository was otherwise untouched.

## Verdict

| Field | Value |
|---|---|
| Verdict | **implemented-with-gaps** |
| Deliverables | **8/8 landed** — every executable *Done-when* clause passed |
| New gaps filed | 8 (high 1 · medium 4 · low 3) |

**This plan is the corpus's single largest gap-closer alongside #1309** — it closed gaps across
040, 050, 060, 100, 130, 320 and 360.

## ⛔ Carry-forward — the defect class was closed in three rules and left live in a fourth

`analyze_argument_naming` **returns `[]` and the gate reports `findings: 0` whenever
`.plan/execute-script.py` is absent — which is every cloud clone** — silently disabling the whole
`ARGUMENT_NAMING_*` cluster **including the rule this plan itself added**. The no-op is undisclosed:
the gate renders clean rather than "could not look".

That surface is inside the plan's own Expected surface, and the plan twice demanded the coverage gap
be "recorded, not asserted clean". The report never records it. **This is the epic's namesake defect,
committed inside the fix written to remove it, at the fourth site of four.** (`G1`, high.)

## Gaps filed

| Gap | Sev | Kind | Summary |
|---|---|---|---|
| G1 | **high** | vacuous-guard | `analyze_argument_naming` no-ops without `.plan/`, reports clean, undisclosed |
| G2 | medium | vacuous-test | D1 anchor-vs-type-list control never calls `_scoped`; mutation stays green |
| G3 | medium | omission | `resolve_project_dir.py` + `test_ci_base.py` missing from § Collateral |
| G4 | medium | stale-statement | Header says "PR not yet opened / in progress"; body says PR #1320 |
| G5 | medium | omission | § Residue never written; C4/C7 live only on a merged PR thread |
| G6 | low | stale-statement | Mutation register "(+3 others)" re-derives as +4 |
| G7 | low | incomplete-sweep | Clean gate publishes population 152, not `blind_spots` 69 |
| G8 | low | process | Run edited its own D7 acceptance criterion in `plan.md` (disclosed) |

## Report inconsistencies

The header (`PR: not yet opened`, `Outcome: in progress`, `Verification loop exit: not yet reached`)
contradicts § Review participation (PR #1320) and § Step 6's exit (operator-stop, 8 rounds) **in the
same file**. § Reviewer participation reads "Pending — no PR yet" **100 lines above** a complete
three-reviewer verdict table and a five-attempt CodeRabbit retry log ending in `obtained`. § Cost and
§ Residue both still read "pending", and § Residue — the report's final section — is empty.

⛔ **§ Collateral claims derivation from `git diff` against `origin/main` but omits two files the
landing touched**, including a **production** change to `script-shared/scripts/resolve_project_dir.py`
(new `ROUTER_FLAGS` constants). Both came from the CodeRabbit C9 commit, made *after* round 8 last ran
the derivation — **the 4th recurrence of the exact defect the report's own Proposal 2 names.**

## ⭐ Counter-signal worth keeping: the figures are exceptionally accurate

Checked and cleared — **every** census/population/count figure in the report re-derives EXACTLY:
152/81/71/69, the 43/18/2/7/1 cause split, 18 across seven notations with the per-notation breakdown,
6 brace-less sites, 25 anchors / 4 detectable, 33 and 414, 46 collected / 21 functions, 29 coverage
rows, 6 subsections, 5 signatures. **The narrative sections went stale; the derived numbers did not.**
That is the opposite of the corpus-wide pattern and is the strongest available evidence that
mechanically-derived figures survive a run where hand-written prose does not.

## What was NOT checked

- No full `./pw verify`. Ran 691 tests across the plan's 15 named test files plus the whole
  1885-test plugin-doctor directory (2 unrelated failures: `pyyaml` missing from an ad-hoc venv).
- PR #1320 thread state — no GitHub API queries; the substance of C1/C2/C3/C5/C6/C9/C10/C15 was
  confirmed by **execution** instead.
- The four cold reads (no transcript committed) and the eight rounds' history.
- Commit-level claims — the fetched remote branch is stale at `b55ad1d7b`, so the final five commits
  resolve to nothing here. Over the visible range 23 of 24 carry the trailer, consistent with the claim.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` = `1320`
- [x] row `landing` = `landings/PLAN-TRUTH-083.md`
- [x] `verification.md` + `gaps.md` authored at ingestion and retained under `cloud-runs/500-…/`
