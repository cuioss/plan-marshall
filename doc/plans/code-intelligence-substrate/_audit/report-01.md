# Run report — code-intelligence-substrate landed-plan audit (run 01)

**Date (UTC):** 2026-08-19    **Branch:** `claude/code-intelligence-substrate-analysis-kah884` (harness-assigned)    **PR:** [#1304](https://github.com/cuioss/plan-marshall/pull/1304)    **Outcome:** completed

> **Verification loop exit:** `verifier-clear`

## What this run was

Not a plan execution. An operator-directed audit of the epic's 36 landed plans, followed by authoring
the fix plans it produced. The `cloud-plan-lane` contract was followed where it applies; **Step 3
(plan directory) is not applicable** — no plan file was handed over, so nothing was moved, and this
report lives in `_audit/` beside the summary rather than in a plan directory. That placement is
itself disclosed as an open question — see § Residue.

## Skills loaded

- `cloud-plan-lane` — the working contract, loaded first.
- `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-script-architecture` — the lane's
  two unconditional loads, read from their bundle paths (the plugin is not installed in this session).
- `author-cloud-plan` and `doc/plans/_template/plan.md` — for the eight fix plans.
- `doc/plans/cloud-bridge.md` — for the naming, status and collect rules the plans depend on.

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Deliverables

| # | What | State |
|---|---|---|
| D1 | Epic-level analysis (`README.md`, plan inventory) | Done — 36 landed plans, all carrying `plan.md` + ≥1 `report-NN.md` |
| D2 | Per-plan `verification.md` | Done — 36 of 36, each with per-deliverable verdicts against the tree |
| D3 | Per-plan `gaps.md` | Done — 36 of 36, 472 entries, each carrying all ten required fields |
| D4 | Adversarial review per plan | Done — 36 of 36, appended as `## Adversarial review`; all returned *sound after correction* |
| D5 | Fix plans numbered from 500 | Done — eight, `500`–`570`, sparse in tens |

**Verdicts across the 36:** 33 CONFIRMED WITH GAPS, 2 PARTIALLY REFUTED (`150`, `200`), 1 PARTIAL (`170`).

**Gap corpus:** 472 — 46 high, 216 medium, 210 low, counted from the entries' own `Severity` field.
Every gap is claimed by exactly one fix plan; the per-plan high counts sum to 46.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` — **empty. No buildable footprint, build skipped.**
The diff is 82 files, all `.md`, all under `doc/plans/code-intelligence-substrate/`. CI confirmed the
documented skip path on the merged head: `verify / verify` **skipped**, `verify / conclusion`
**success**, `verify / gate` success, `dependency-review` success.

**Stale-base re-verification (merge gate condition 2).** `git rev-list --count HEAD..origin/main` was
**2** at the gate — `main` had taken `#1302` and `#1303`. Shape used: **merged on the branch and
pushed**, merge commit `eb46c15`. The gate was re-run on that merged tree: the `*.py` predicate is
still empty and the changed-path set is still epic-only.

Because this diff's substance is `path:line` citations into code, the merge mattered for a reason the
`*.py` predicate cannot express: `#1303` renamed test fixture modules. The citation sweep was
therefore re-run **against the merged tree** — 3,396 resolvable citations, **zero** genuine past-EOF,
one expected overshoot which is a citation the document deliberately quotes as an example of a wrong
citation. Condition 2 is **established**.

## Findings

Six verification rounds. Every round found defects; from round 2 on, the majority were introduced by
the previous round's own fixes.

| Round | Found | Of which introduced by the previous round's fixes |
|---|---|---|
| 1 | 5 | — |
| 2 | 4 | 3 |
| 3 | 2 | 2 |
| 4 | 4 | 2 (plus one round-**1** residue rounds 2 and 3 both read past) |
| 5 | 6 | 3 |
| 6 (narrow) | 3 | 3 |

**All fixed.** Every finding was category A (a false statement) or was closed with a stated bound; no
finding was rejected, and none was deferred. The three most instructive:

- **An invented rationale (round 2).** Round 1's fix justified a severity raise on the gap entry's own
  escalation trigger, while quoting the fact that refutes it one sentence earlier. The trigger is a
  conjunction and the plan satisfied only half. Re-derived against the code — the harvest has one
  non-test caller whose module paths are never root-scoped — and the raise was **withdrawn**, not
  repaired.
- **A severity roll-up wrong at three sites (round 1).** The extraction script tested for `"high"`
  anywhere in the severity line, so entries reading *"Raise to high if…"* and *"why medium and not
  high"* were both counted high. It propagated into two plans and the summary. Corrected to the
  entry-derived 46/216/210.
- **A sweep with a blind spot (round 6).** Round 5's citation sweep could not distinguish a citation a
  document *uses* from one it *quotes as an example of a wrong citation*, so it "corrected" a quoted
  defective form and made the finding sentence false. Reverted; the sweep re-run with the roles
  separated.

### Stop record

- **Exit: `verifier-clear`.** Round 6 answered directly that one category-A false statement remained
  and no category-B defect stood without a bound; that statement was fixed, and the two minor items
  beside it were fixed on evidence round 6 itself quoted.
- **Budget:** five, the contract's default. It was **exhausted at round 5**, the operator was asked at
  the boundary via `AskUserQuestion`, and granted **one narrowly-scoped round 6** — not a further five
  — on round 5's own recommendation to close its findings, verify those edits narrowly, and stop.
  Round 6's scope was commit `ecdcf4e` and its surrounding blocks, explicitly not a fresh sweep.
- **Evidence stronger than a read:** the whole-epic partition, re-derived from the 472 entries rather
  than from any table — every gap assigned exactly once, zero orphans, zero phantoms, zero cross-plan
  duplicates, reproducing all eight per-plan triples and the epic total cell for cell. It came back
  *different* at round 1 (48/214/210, plan `500` at 11 high), which is what makes it a real check.
- **Narrowing:** yes, and rounds 4–6 falsified **nothing** in the audited subject matter — every
  coverage table, every severity, the whole partition and every external fact about the governing
  contracts re-derived clean. Findings moved from the deliverables to this run's own records.
- **Survivors:** none. No finding was left open.
- **Residue to assume remains:** round 6's own three fixes were not put through a seventh round. Read
  the deliverables as still carrying defects of the kind rounds 5 and 6 found — record-level
  imprecision, stale enumeration lead-ins, imprecise restatements — **not** falsified deliverables.
  Round 6's own estimate of a hypothetical round 7 was more of that shrinking class, probably
  self-generated, at declining value.

## Reviewer participation

Population derived from the registry — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | "PR Reviewer Guide": no relevant tests, no security concerns, no major issues — a real review artifact over the diff |
| `coderabbitai` | see below | — | Began a full review of all 82 files against `6c2c0d1`; superseded by the condition-2 merge push. **Re-requested** with the registry's declared `@coderabbitai review` trigger |
| `sourcery-ai` | `rate-limited` | **no** | "your pull request is larger than the review limit of 150000 diff characters" — a size ceiling, a property of this diff rather than the clock, so it never reopens for this PR |

**The CodeRabbit review was an explicit operator requirement**, so this PR deliberately carries **no**
`skip-bot-review` label — that label is honoured by CodeRabbit's central config and would have
suppressed the very review that was required. The diff also earns its review on the lane's own rule:
it contains eight plan files, and a plan is behavioural prose a later run executes.

Its final verdict is recorded by the operator against the PR rather than predicted here.

## Cost

- **Tokens:** not available to the agent in this session — the harness surfaces no per-run count.
- **Wall-clock:** one extended session on 2026-08-19; the dominant cost was ~80 sub-agent dispatches
  (36 audits, 36 adversarial reviews, 8 authoring agents, 6 verification rounds).
- **Population:** this single Claude Code cloud session as the harness counts it. ⛔ **Not comparable**
  to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under
  a per-task billing boundary this session does not share. No comparable figure is available.

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | § Skills loaded; bundle-path reads |
| 2 Branch | done | Harness-assigned `claude/*` kept as-is; on `origin` before any edit |
| 3 Plan directory | **n/a** | No plan was handed over — this is an epic audit, not a plan execution |
| 4 Implement | done | Deliverables addressed; every commit carries the `Co-Authored-By` trailer |
| 4 Per-commit gate | **n/a** | No commit touched `*.py` |
| 4 Pushed | done | No unpushed commit; pushed after every commit |
| 5 Build gate | done | Git-derived verdict and result in § Build gate |
| 6 Verification sub-agent | done | Six rounds, all findings fixed; stop record in § Findings |
| 7 PR cycle | done | PR #1304; no `skip-bot-review`; comment surfaces read; CodeRabbit re-triggered after the merge superseded it |
| 8 Merge gate | see § Build gate and § Reviewer participation | Condition 2 established on merge commit `eb46c15` |
| 8 Bridge | done | No status or bookkeeping write outside `_audit/`; no other plan's directory touched |
| 9 This check | done | This table |
| 9 What have we learned | done | Below |

A `/sync-plugin-cache` is **not owed** — a machine-local build step a cloud run never performs.

## What have we learned (Step 9)

**One contract change is worth proposing, and this run produced the evidence for it.** The lane's
§ Step 6 says the highest-risk text is the prose the *previous round wrote*. This run found that
incomplete: round 4's first finding was a **round-1** residue that rounds 2 and 3 both read past,
because each round examined what the previous round *added* and not what it *edited around* — a count
left standing after the item it counted was deleted. The proposed increment is one clause: when a fix
deletes or moves an item, re-read the whole block it sat in, not the changed line.

⛔ **Not shipped here.** The contract forbids a run self-approving a change to the contract governing
it, and the lane requires such a change to ship as a separate `chore/` PR touching only the skill.
This report records the proposal; the operator decides.

## Residue

- **CodeRabbit's verdict** is outstanding at the time of writing; it was re-requested after the
  condition-2 merge superseded its first attempt.
- ⛔ **`_audit/` becomes collectable when this PR merges, and that is an open risk, not a bounded
  one.** `cloud-bridge.md` § Path 3 says every directory under an epic is a plan a run has worked;
  step 2 needs a merged PR *and* a `report-NN.md`, and step 6 deletes what steps 2–5 corroborated.
  **This report is that `report-NN.md`, and it names PR #1304** — so on merge both halves are
  satisfied and a collector following Path 3 would treat this directory as a landed plan and delete
  it. Only #1304 being open prevents that today.
  An earlier revision of this row said the merged-PR half "still does not hold … as `_audit/` is not
  a plan and no PR lands it as one". That reasoning is wrong: Path 3 keys on the *presence* of a
  merged PR named by the report, not on whether the directory is a plan. Corrected here, and in
  `README.md` and `summary.md`, after the PR reviewer caught it. Making the exclusion explicit is a
  contract change, raised as proposal **P8** in `570`. ⚠ **Until P8 is decided, collect over this
  epic needs a manual check of `_audit/`.**
- **Round 6's own fixes** were not put through a seventh round — see § Findings → Residue to assume
  remains.
- **The eight fix plans are authored, not executed.** Their sequencing constraints are in their own
  Notes; `560` last is the one that matters.
