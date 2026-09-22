# Landing analysis — PLAN-PR-033

**Plan**: `the-foreign-gate-population-and-branch-f-recovery`
**PR**: #1473 — **merged** via merge queue at `38af136ede5c7d6ea531a38d59a67ece1bf3ade2`
**Deliverables**: 2/2 · **Finalize steps**: 23/23 · **Landing message**: `-008`, `complete: true`
**Corroboration**: PR state read first-party through `ci pr view --pr-number 1473` (`state: merged`),
merge commit confirmed against `git log`. ⛔ Not taken from the landing narrative.

## Deliverable fidelity vs spec

Both deliverables landed as scoped, and both are recorded under an **operator ruling taken at the
outline gate** rather than as a plan-side judgement:

| # | Deliverable | Verdict |
|---|---|---|
| D1 | Restrict both foreign selectors to declared changes | shipped — one `declares_change` predicate in `_plan_parsing.py`, consumed by the `foreign` roll-up AND the gate's population walk |
| D2 | `cleanup_owed` as the structured carrier for owed branch cleanup | shipped — recorded at all eight terminal `branch-cleanup` call sites, required `landing-facts` key, guard test |

⭐ **D1's design answer is the one worth carrying**: the column and the gate now cannot disagree about
what a foreign change is, because one predicate owns the rule. A second copy is how two producers come
to disagree — the defect class this epic keeps re-finding.

⭐ **The `080 G5` hypothesis was REFUTED at HEAD and the plan said so** — `branch-cleanup.md`'s F2/F3
blocks already disclaim re-entry. What survived was a narrower real gap (F2's owed-ness lived only in
an 80-character display string no consumer routes on), and the operator overrode the earlier
prose-only recommendation in favour of the machine-readable fact. ⛔ A refuted premise that produced a
narrower true defect is the verify-first contract working, not a failure.

## ⛔⛔ THE FINDING OF THIS LANDING — the realized footprint is twice the declared one, and it silently discharged OTHER plans' deliverables

**`references.affected_files` recorded 14 of the 28 files that actually landed** (the plan's own
residue reports this). The undeclared half is not incidental — it contains work this epic had staged
as separate plans:

| Shipped here, undeclared | Whose deliverable it was |
|---|---|
| `github_re_review.py` — `head_sha_verified` now decided by `_verifies_head_sha(...)` over the comment BODY on the `issue_comment` path | **`PLAN-PR-056` D6** (ex-`PLAN-PR-043` D5a) |
| `review_completeness.py` + `test_measured_diff_size_bare_flag.py` — the `--measured-diff-size` bare-flag crash | **`PLAN-PR-058`** D7/D9 territory (ex-`PLAN-PR-051` D2/D1a) |
| `cuioss-review-bot.md`, `bot-participation-contract.md`, `branch-cleanup-rereview.md` | participation-contract surface of `PLAN-PR-056` / `PLAN-PR-057` |

⭐ **Corroborated first-party at `38af136ed`, not inferred from the narrative**: `git show --stat`
lists 28 files, and the `issue_comment` branch of `github_re_review.py` now calls the shared
`_verifies_head_sha` predicate. The docstring records the correction in its own words: *"an issue
comment carries no reviewed-commit SHA" was a premise, not an observation, and it is false.*

⛔ **This is the under-declaration residual class the disjointness gate is explicitly bounded by** —
and here it did not merely cost throughput, it **discharged a staged plan's deliverable without any
ledger row moving**. The gate compares DECLARED surfaces; a plan that lands twice its declaration is
invisible to it. ⚠ The remedy is recorded and unowned: `reconcile-scope` already detects the drift,
and **nothing in finalize calls it**.

## Metrics and anomalies

- **7.04M tokens, finalize 75.1%** — the fourth consecutive plan to miss the error anchor by ~5.4×.
  ⭐ The retrospective's own conclusion is that **the anchor measures the step roster, not the plan**,
  so per-plan tuning cannot close it. Carried as an epic-level cost signal, not as a plan defect.
- **120h41m wall against 6h20m worked** — 114h20m idle, dominated by three 90-minute CodeRabbit quota
  waits inside finalize.
- **Review reliability**: 6 self-review rounds (9 findings, 8 fixed, 1 refuted); 4 CodeRabbit rounds
  (5 actionable). ⛔ **3 of CodeRabbit's 5 inline findings were defects in the fixes for its own
  earlier findings** — recorded as candidate-lesson `-001`.
- `[LOOP_BACK]` headline at `loop_back_iteration: 5` is the template's documented precedence, not a
  failure state: the PR is merged and cleanup is complete.

## Routing / merge behaviour

Merge-queue landing, rebase deferred to the queue, corroborated post-merge, cleanup complete
(`cleanup_owed=false` — the key this plan itself introduced, on its own landing).

## Parallelization consequence

`PLAN-PR-033` ran concurrently with `PLAN-PR-046` under `parallelization_scope: 2`. **No collision
was observed between them.** ⚠ But the disjointness verdict that paired them was computed over a
declared surface this plan then doubled — so the clean outcome is **not** evidence the gate was right;
it is evidence the undeclared half happened not to intersect PR-046's. Recorded so the next pairing
decision does not read this as a passing gate.

## Reconciliation actions taken

1. Queue row `PLAN-PR-033` → `shipped`, `pr: 1473`, landing stamped.
2. `PLAN-PR-056` D6 recorded as **shipped by #1473**, with its claim's verdict stamped `contradicted`
   (the mechanism it names no longer exists at HEAD) — the deliverable is re-scoped to the audit half.
3. `PLAN-PR-058` D7/D9 flagged for re-grounding at outline against the shipped `--measured-diff-size`
   fix.
4. Carry-forward findings `852b0f` and `658eec` folded into `PLAN-PR-057` D1 and D10.
5. Candidate-lessons `-001`, `-007` promoted to the global corpus; `-006` transferred to
   `truthful-signals` (not this epic's charter); `-009` recorded as an Open Defect.
