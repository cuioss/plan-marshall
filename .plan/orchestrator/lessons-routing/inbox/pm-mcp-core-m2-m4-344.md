envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:49Z

# Change ledger has no sha remap after rebase; attribution degrades to declared_only

**Component (foreign):** plan-marshall:manage-change-ledger (consumer: plan-marshall:phase-6-finalize review_support attribution)
**Category:** improvement
**Source plan:** plan-14-operator-and-question-stores (PR #93, squash 3323ce7)

## Observation

The change ledger is pure-append and keyed by commit sha. A pre-merge rebase (forced twice here, because origin/main moved and conflicted) rewrote every sha of the branch. `review_support attribution` then could no longer match ledger rows to the branch commits, fell back to `declared_only`, and listed the renumbered ADRs and other legitimately-changed files as unrequested candidates.

The only repair was manually re-appending ledger rows for the rebased commits: 10 appends after the first rebase, 27 after the second. There is no remap verb (old sha -> new sha, e.g. via patch-id or `git range-diff` correspondence).

## Suggested corrective action

- Add a `remap` (or `rebase-sync`) verb to manage-change-ledger that maps rows of rewritten commits onto their rebased counterparts by patch-id / range-diff, keeping the ledger append-only by appending mapped rows.
- Or have the branch-sync / rebase step call that remap automatically after any history rewrite, so attribution never silently degrades to declared_only.
- At minimum, `review_support attribution` should report "ledger shas not on branch (history rewritten?)" instead of presenting files as unrequested.
