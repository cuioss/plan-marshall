envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T14:51:12Z

# Two pre-push gates check the wrong tree or key, so a problem surfaces late or a gate runs twice

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-06-enumeration-hardening (PR #528), candidate lessons 001 and 003. Observed with plugin and executor 0.1.2010.

## Observation

1. While the plan was in finalize, main took ADR-0072 in another PR. The branch also added an ADR-0072. Every local gate passed because the branch base was older. The duplicate showed up only when CI built the merge ref. A task said to re-check the ordinal against origin/main before the push, but that step was not executed.
2. The pre-push freshness ledger keys each row to a worktree SHA. That SHA changes at commit time and also when the executor is regenerated, so a gate build that ran on byte-identical content just before the commit does not count, and each finalize fix pays for two full gate runs.

## What to consider

- Run the duplicate ADR-ordinal scan on the tree that will merge (the merge ref, or origin/main plus the branch) as a mechanical step of the pre-push gate. A prose instruction in a task did not hold.
- Key freshness to a content identity that survives the commit, such as the tree hash of the tracked files, ignoring untracked executor files. Until then, finalize fix recipes should commit first and gate once on the committed tree.
- Related earlier lessons: main moves under a long finalize and the baseline is checked only at entry (2026-10-03-06-002).
