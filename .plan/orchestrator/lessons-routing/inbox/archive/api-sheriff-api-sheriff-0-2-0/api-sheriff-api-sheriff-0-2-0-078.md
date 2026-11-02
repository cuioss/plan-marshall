envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-30T16:41:00Z

## Findings from API-Sheriff plan-v02-48-adr-corpus-cleanup-part-2

### 1. `loop-back close --waive-refire` is not honoured by `pre_merge_gate merge`

`manage-status loop-back close --step code-review --waive-refire functional-review --waive-refire finalize-step-simplify` recorded a `refire_waiver` carrying the head and basis on both steps. `pre_merge_gate merge` then refused with `merge_candidate_not_gated`, naming exactly those two steps, and its message says only a re-run clears it. So an operator waiver accepted by one verb dead-ends at the merge. The refusal arrived after CI, bots and Sonar had finished, and the run had to go back to the operator. Either the gate should honour a waiver bound to the candidate head, or `loop-back close` should refuse the waiver up front and say the merge gate will not accept it.

### 2. Freshness gate passed on a narrow test row labelled whole-tree

The pre-push freshness check passed on a test row covering 5 tests whose label said whole-tree. A targeted run can therefore satisfy a check whose wording claims the whole tree.

### 3. Merge-queue squash message

`branch-cleanup.md` § Squash-message composition tells the run to set the repository's merge-commit-message default when the queue cannot take a per-enqueue message. That is a repository-wide setting, and this repository's default is `PR_BODY`. The run left it unchanged, logged the limitation, and the landed commit carries the PR body. The instruction looks too broad for a single plan to act on without asking.
