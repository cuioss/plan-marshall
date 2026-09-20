envelope_version=1
sender_type=plan
sender_id=participation-credit-anchored-to-merge-candidate
epic=review-apparatus
kind=landing
created=2026-08-25T21:29:53Z

# Landing: PLAN-PR-024 — participation credit anchored to the merge candidate

## Outcome

**SHIPPED.** PR [#1349](https://github.com/cuioss/plan-marshall/pull/1349), squash-merged via the
platform merge queue, landed on `main` as `8025b2210`.

All 6 deliverables implemented. 12 tasks, 2 envelopes, 10 branch commits.

The D0 halt gate PASSED on real derivations: 16 participation sites scanned from
`marketplace/bundles/**` with all 7 seed symbols resolving, and the currency-subject bot population
derived from `bot_registry`. No hand-maintained fallback was used — which the spec forbade, because a
fallback would have reproduced the defect inside its own fix.

## Footprint

Declared 10, achieved 10, identical sets — derived from `git diff 8025b2210^ 8025b2210`, not copied
from `affected_files`, so the comparison is an independent check.

Two paths are collateral against the spec's Expected Surface and are reported as such:
`_github_ci.py` and `github_ops.py`, touched because deliverable 3 needed the merge-candidate commit's
own timestamp, which required a new `fetch_pr_head_committed_at` provider verb. The spec's own D2 text
requires that timestamp; its Expected Surface list simply did not enumerate the provider file.

## Verification

Whole-tree gates green at the merge candidate: 22,502 tests, quality-gate and test-compile clean.
CI green on `9d8c2d114`. Every new test recorded as failing against pre-change code, per test.

## Gap this landing leaves open, deliberately

`undecidable_participation_bots[]` ships with NO reachable consumer. Widening the
`review_completeness` taxonomy was explicitly out of scope — it is the contract's own vocabulary,
restated by every consumer doc. This PR lands the producer signal and the UNKNOWN routing, which is
that plan's prerequisite. Documented in both required locations; no test asserts a downstream
classification nothing can reach.

Two lessons in this epic's corpus independently flagged this shape (`2026-08-08-21-004`,
`2026-08-25-09-015`). It is bounded and known, not discovered late.

## Proposal recorded, not implemented

Extending the currency ledger to every bot declaring `participation_evidence`. Blast radius: it
changes the merge-barrier verdict for every consumer project whose `required_bots` includes an
append-per-review bot. It also raises an unanswered contract question — an in-place re-reviewer needs
the ledger because its comment identity never changes, whereas an append-per-review bot's comments are
already distinguishable but still carry no reviewed SHA, so anchoring them requires deciding what a
new comment's presence proves about the commit it was posted against.

## Reviewer coverage on this PR — a durable epic fact

The external reviewer set contributed **ZERO** actionable findings. The in-house
`pre-submission-self-review` gate found **FIVE** real contract-drift defects in the same diff, one of
them (`906944`) a hole in the merge barrier's own positive-validation enumeration.

- `pr-agent` (required): `participated_but_empty` — published, produced nothing actionable.
  `/improve` (piloted since #1334) returned "No code suggestions found for the PR."
- `coderabbit` (optional): `refused_awaitable`, quota. Its refusal body carried a usable ETA in plain
  text ("Next included review available in 46 minutes") that the classifier did NOT extract.
- `sourcery` (optional): `refused_structural`, cap "150000 diff characters" vs measured
  "2118 changed lines". **Structural, not transient** — on PRs of this size Sourcery refuses
  deterministically and waiting never recovers it.

`review_completeness` returned `participation_complete: true` / `proves: participation_only` on a
required set of exactly ONE, satisfied by a bot whose default output is contentless. A required set of
one, satisfied that way, cannot distinguish a reviewed PR from an unreviewed one.

## Cross-plan dependency this landing creates

`phase-6-finalize/scripts/review_commitments.py:59` carries a wrong pre-filter ordinal (the
cross-iteration dedup is stage 6, not 5) AND quotes the two-term dedup key verbatim as load-bearing
rationale. Deliverable 5 widened that key to three terms, so after this landing that sentence is stale
on BOTH axes. Out of surface; the operator declined fixing it here.

## Defects routed OUT of this plan — for the orchestrator to forward

All are outside this plan's Expected Surface and none was fixed here.

- `e5372d` (error) — `detect-artifacts` classified ~108,879 paths as safe-to-delete, including the
  RUNNING plan's own live `.plan/local/` build results and execution log, contradicting its own
  documented gitignore exclusion. Nothing was destroyed only because the executing agent declined to
  act on the list. A defect that needs an agent to DISOBEY the docs to be harmless.
- `e589e5` (warning) — the execution-tier table is non-monotonic over command containment:
  `module-tests plan-marshall` resolved orchestrator/688s while the strictly wider
  `verify plan-marshall` resolved per_task/493s. This nearly cost the run its evidence — routing on
  the narrower command's tier would have yielded with NO tests run and no discrimination proof.
- `58d817` (warning) — `finalize-step-deploy-target` and `finalize-step-sync-plugin-cache` both
  prescribe interpreters that fail on this machine (`uv` absent; system `python3` lacks `yaml`). The
  sync failure is shape-identical to a genuine staleness refusal (exit 2, `status: error`,
  `synced_count: 0`) and its remediation points back at the command that cannot run — the two compound
  into a loop with no documented exit. Worked via `.venv/bin/python`.
- `d60ebd` (warning) — `mark-step-done` refuses a `failed → done` transition without `--force`, and
  Branch A never says so. Structural: for a hard-fail gate, `failed → repair → done` IS the normal
  success path.
- `f2f281` (warning) — `branch-cleanup` recorded `done` while persisting neither `realized_footprint`
  nor `merge_commit_sha`, both of which its own frontmatter declares, so the retrospective's
  declared-vs-achieved check returned INCONCLUSIVE. Repaired post-hoc for this plan. Secondary:
  `_footprint_resolver` tier 4 reads `references.modified_files`, a key NO live plan writes —
  independently corroborated when `lessons-housekeeping` hit the same dead field.
- `3ed03b` (info) — the rename sweep is unverified against `.claude/**` and `.github/**` (outside the
  crawled inventory). No failure mode: deliverable 6's union read still reads the legacy filename, so
  any surviving reference is stale prose at worst.

## Run economics

4,040,890 tokens; 108,071,628 billing-weighted; 5h46m worked / 11h21m wall.

The merge mutex was contended for ~75 minutes by a live sibling plan
(`fold-pm-code-intelligence-into-core`, landed as #1348). It released cleanly (`reclaimed: false`) —
breaking it would have corrupted a real merge.
