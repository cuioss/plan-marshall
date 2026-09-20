# WS-01: Await and participation detection

epic: review-apparatus

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-await-and-participation-detection.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns the plan-marshall consumer side of the review apparatus: the machinery that triggers a
review, waits for it, and decides whether a bot participated. Its outcome is that a loop-back
detects a genuine pr-agent re-review as soon as it happens instead of burning the full await
timeout and escalating to the operator. The defining property of this surface is that every
observable it keys on must match how the bot actually publishes — a detector that watches the
wrong observable produces a confident wrong answer, never an error.

## Scope

The await/detect seam and the participation classifier — the surfaces that PRODUCE a review verdict.
Widened on 2026-07-30 when `truthful-signals` PLAN-116 was released here and **split into four
slices**, all of which land in this workstream.

- In scope: the `pr wait-for-comments` completion predicate and the participation derivation in
  `workflow-integration-github/scripts/{_github_pr,github_pr}.py`; the participation taxonomy in
  `automatic-review/standards/bot-participation-contract.md`; the per-bot registry records in
  `automatic-review/scripts/bot_registry.py` and its `standards/{pr-agent,coderabbit,sourcery}.md`;
  their tests.
- Out of scope: what CONSUMES the verdict — the pre-merge barrier, the merge path, and the landing
  channel (WS-04); the org reusable workflow (WS-02); config-repo work and ingestion contracts
  (WS-03); the plan-less-PR seam in `tools-integration-ci` (`truthful-signals` PLAN-115, launched
  and retained there).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PR-001-wait-for-comments-counts-rows | staged | PLAN-116 **Defect A**. Watch the row, not the count. LIVE on every loop-back |
| PLAN-PR-007-absent-names-two-states-with-opposite-remedies | staged | PLAN-116 **Defect F**. ⭐ THE COMMON PATH — add the `stale` member; no merge verdict moves |
| PLAN-PR-013-participation-credited-from-a-superseded-commit | staged | ⭐ Staged 2026-07-30 from two independent inbox sightings. **The false-POSITIVE polarity — the only plan in this epic that MOVES a merge verdict.** Confirmed on merged `#1063` |
| PLAN-PR-005-participation-derived-from-a-lossy-view | staged | PLAN-116 **Defects C+E**. One root cause seen twice: credit derived from a lossy projection |
| PLAN-PR-006-canned-no-op-indistinguishable-from-a-review | staged | PLAN-116 **Defect D**, split out on that spec's own advice — a different observable |

## Sequencing and Surface Notes

- ✅ **The PLAN-116 collision is RESOLVED, not merely noted.** That plan was released here and its
  row in `truthful-signals` is `transferred` (verified against that epic's live queue). There is no
  longer a competing owner, so PLAN-PR-001's earlier "narrowed to avoid serialization" framing is
  superseded — the narrowness now serves the split, not a boundary dispute.
- ⛔ **PLAN-PR-006, PLAN-PR-007 and WS-03's PLAN-PR-011 D2 all touch the same participation
  classifier**, each adding a distinct state (`stale` / canned-no-op / absent-vs-in-progress).
  **They must land as ONE coherent taxonomy, sequenced — never paired.** PLAN-PR-007 goes first so
  the others extend a settled taxonomy instead of racing one.
- ⭐ **The workstream now carries BOTH polarities of the same question, and they must not be confused.**
  PLAN-PR-001 / -005 / -006 / -007 are all **false negatives** — a real review that fails to be
  credited, worst case a needless loop-back. **PLAN-PR-013 is the false positive** — credit granted for
  a review of a superseded commit, worst case an unreviewed tree merging. ⛔ PLAN-PR-007 forbids itself
  from moving any merge verdict and PLAN-PR-013 exists to move one; **folding them together would set
  their safety properties against each other.** Sequence PR-007 → PR-013.
- ⛔ **PLAN-PR-013 has the widest collision footprint in the epic** — it touches the participation
  classifier (with -005/-006/-007/-011-D2) *and* `branch-cleanup.md` (with WS-04's -008/-009). Never
  pair it with any of them.
- ⚠ **PLAN-PR-001, PLAN-PR-005 and PLAN-PR-013 share `_github_pr.py`** — three different functions, and
  the three-way boundary is **plausible but unverified**; PR-013's D1 confirms it before anyone assumes
  disjointness. Sequence, do not
  pair, until both surfaces are re-verified at outline.
- This workstream's output is an input to WS-04: PLAN-PR-007 must land before WS-04's PLAN-PR-008,
  because a false `absent` and a true `absent` are indistinguishable at the barrier.
- No plan here waits on `truthful-signals` PLAN-115 — its surface is `tools-integration-ci`, which
  this workstream does not touch. (WS-04's PLAN-PR-009 does.)
- `parallelization_scope = 1`, so nothing runs concurrently regardless of disjointness.
