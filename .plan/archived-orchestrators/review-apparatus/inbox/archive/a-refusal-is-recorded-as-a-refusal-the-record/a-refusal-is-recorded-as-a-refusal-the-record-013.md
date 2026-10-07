envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=finding
created=2026-08-31T08:25:43Z

# `ci pr view` reports `auth_failed` while `gh auth status` shows an active authenticated account

**Component:** `plan-marshall:tools-integration-ci`
**Category:** bug
**Observed:** 2026-08-31, during the post-merge finalize tail of
`a-refusal-is-recorded-as-a-refusal-the-record` (PR #1368, already merged).

## What was observed

The output-template Snapshot Procedure step 4 read failed:

```
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id a-refusal-is-recorded-as-a-refusal-the-record pr view
->  status: error
    operation: pr_view
    error: Not authenticated. Run 'gh auth login' first.
    error_cause: auth_failed
```

A live `gh auth status` in the same shell, immediately afterwards, contradicts it:

```
github.com
  ✓ Logged in to github.com account cuioss-oliver (keyring)
  - Active account: true
  - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
  ✓ Logged in to github.com account cuioss (keyring)
```

## What was ruled out

- **Not a sandbox artifact.** The call was re-run with the harness sandbox disabled and
  returned the identical envelope.
- **Not the `--plan-id` position.** Both the router-first documented form
  (`ci --plan-id X pr view`) and a form carrying `--pr-number 1368` return the same envelope.
- **Not a genuinely absent PR.** #1368 is merged; the squash landing
  `31d42db871eb1ed6095868b42af85e8162ef4a8e` is on `main`.
- **Not a stale token.** The same finalize run made many successful `gh`-backed `ci` calls
  earlier (automatic-review, branch-cleanup's merge, review-retrospective) with this account.

## Why it matters

`error_cause: auth_failed` is one of the three UNANSWERED arms in
`phase-6-finalize/standards/output-template.md` § Snapshot Procedure step 4. The renderer is
required to store `state = unread` and route the headline to `[FAILED]` (Emission Procedure
step 1 item 1) — because a finalize summary that cannot say whether a PR exists is not a green
one. So a **false** `auth_failed` turns a completely successful, merged run into a `[FAILED]`
headline. That is the fail-closed behaviour working as designed on top of a producer that
reported a state it did not have.

This is the same defect shape the plan that observed it was written to close: a signal
reported on the wrong axis. The barrier/renderer consumer is correct; the producer's
auth probe is what needs deriving from the real `gh` auth state rather than asserting it.

## Suggested next step for the epic

Establish what `ci_base`'s auth probe actually tests (an env-var token? a `gh auth status`
exit code? a cached credential read?) and why it disagrees with a keyring-backed logged-in
`gh`. A matched control is cheap here: assert the probe returns authenticated for a shell in
which `gh auth status` exits 0, and `auth_failed` only when it does not.
