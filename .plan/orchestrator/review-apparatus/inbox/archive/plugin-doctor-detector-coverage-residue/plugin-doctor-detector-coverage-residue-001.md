envelope_version=1
sender_type=plan
sender_id=plugin-doctor-detector-coverage-residue
epic=review-apparatus
kind=finding
created=2026-08-25T07:26:39Z

# Findings from PLAN-TRUTH-094 (truthful-signals) — delegated to review-apparatus

Three findings from PR #1343's review cycle. Delegated rather than retained:
they concern automated PR review reliability, which this epic owns. All were
measured on the live PR, not inferred.

## 1. The required/optional bot split does not match measured yield (`5bdbb9`)

The strongest empirical result of the run, and it argues for reviewer diversity
over reviewer effort.

The merge candidate had passed a whole-tree quality gate (37 rules, 0 issues),
21957 module tests, a clean plugin-doctor whole-tree run, and **seventeen rounds
of dispatched self-review** that converged to two consecutive clean results.
CodeRabbit's re-review of that exact HEAD still found a **correctness defect in
shipped code**: `_analyze_argument_naming.py` counting an undecided site as
decided — the plan's own subject, introduced by the plan's own commit
`4ca2481a9` and missed by `77f493597`, whose subject reads "close four coverage
over-claims" (it closed four and left a structurally identical fifth).

Confirmed by prediction-then-measurement: `blind_spots` 292 → 304 (+12) with
`population_size` unchanged at 2792. The under-count was hiding a live corpus
defect — `scan-planning-inventory scan --format summary` is documented at four
sites and exits 2 with `unrecognized arguments: scan`.

**This was the SECOND time on this PR that CodeRabbit was the only reviewer to
read the diff.** Across both reviews:

| Bot | Manifest role | Round 1 | Round 2 |
|---|---|---|---|
| `pr-agent` (`cuioss-review-bot`) | **required** | "No major issues detected" | "No major issues detected" |
| `coderabbit` | *optional* | 8 actionable, 6 real | found the merge blocker |
| `sourcery` | *optional* | structural refusal (size) | structural refusal (size) |

The manifest marks the bot with zero measured yield on this PR as REQUIRED, and
the one that found real defects twice as OPTIONAL. Worth re-deriving the split
from measured yield across the corpus rather than from configuration order.

Two further conclusions: (a) self-review convergence is not a substitute for an
independent reader — 17 rounds of the same reviewer architecture converged clean
on a defect a different reader found immediately; (b) a plan that merges as soon
as its own review converges will ship this class of defect.

## 2. A re-fired `automatic-review` leaves its comments un-ingested (`a02741`)

`automatic-review` fired twice: round 1 at HEAD `981a3bc9` (15 pr-comment
findings ingested, all stamped `reviewed_commit_sha: 981a3bc9`) and round 2 at
the merged HEAD `98f8bc27` (12 new comments — `wait-for-comments` reported
`new_count: 12`, baseline 12 → final 24). **Only round 1's comments are in the
finding store.**

PR-comment ingestion is internal to `automatic-review`'s workflow body, and no
standalone verb backfills it (`manage-findings ingest` is finding-to-lesson
promotion and returned `skipped` for all 20 qgate findings when tried).

The consequence lands on `finalize-step-review-retrospective`, which declares
`order: 990` **specifically** so it runs after the merge gate has finished
filling the pr-comment store — its own SKILL.md says that ordered earlier it
"would compare reviewers over a store the gate had not finished filling and
report a confident verdict about evidence that did not exist yet." A re-fire
defeats that guard from the other side: the step runs late, as designed, over a
store missing the later round. Here that is not marginal — round 2 is where
CodeRabbit found the merge blocker, so a comparison over round 1 alone
understates the reviewer precisely where it performed best, in the flattering
direction.

**Remedy:** re-ingest on every `automatic-review` firing, or have
`review-retrospective` assert `max(reviewed_commit_sha) == merged HEAD` and
publish the gap when it does not.

## 3. The missing `pull_request` event was transient, not structural (`75cd64`)

Updates finding `22e8a6`, which diagnosed PR #1343 as having received no
`pull_request` event: 4 checks from one push-triggered run, no CodeRabbit check,
no `dependency-review`, no `auto-merge`.

After the settle band converged, a `force-push-with-lease` to the same PR produced
the **complete** fan-out: 10 checks, two Python Verify runs (push- and
pull_request-triggered, distinct run ids `32813186716` / `32813189371`), plus
`dependency-review`, `generate-check`, `auto-merge`, Sourcery and CodeRabbit.

So the event loss self-heals on the next push to the head ref. `22e8a6`'s
remediation analysis stands (the merge path was verified unaffected via
`merge_group: types: [checks_requested]`), but its implied permanence does not.
**A PR with a truncated fan-out should be re-pushed before the absence is treated
as a configuration or workflow-filter defect — a no-op push is the cheapest
diagnostic.** Note also that `automatic-review`'s `pull_request_run_count=0`
reading was correct when taken and would read differently now, which is exactly
the remote-state-vs-HEAD distinction finding `f36fa7` raises about HEAD-keyed
re-entry.
