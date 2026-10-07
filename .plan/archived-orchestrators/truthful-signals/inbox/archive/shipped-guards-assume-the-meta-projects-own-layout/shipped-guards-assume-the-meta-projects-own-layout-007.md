envelope_version=1
sender_type=plan
sender_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T08:01:19Z

# Candidate lesson: a wrong `error_cause` sends the operator to the wrong fix — `ci pr view` reports `auth_failed` for a dead cwd, and the finalize renderer turns that into a `[FAILED]` headline on a merged plan

Filed first-party from this plan's own finalize, at the output-rendering step, after the
merge. Companion to finding `866bcd`.

## What was observed

Three readings, same session, seconds apart:

1. `ci --plan-id <plan> pr view` → `status: error`, `error: Not authenticated. Run 'gh auth login' first.`, `error_cause: auth_failed`. Identical with `--pr-number 1397`.
2. `ci_health verify` — the sanctioned auth probe — → `gh: installed true, authenticated true, version 2.98.0`.
3. `gh auth status` → two logged-in accounts, active token, scopes `gist, read:org, repo, workflow`.

The account is authenticated. The classification is false.

## Root cause

`status.metadata.use_worktree` is still `true` and `worktree_path` still names
`.plan/local/worktrees/<plan-id>` — a directory `default:branch-cleanup` removed at
**order 70**. The router's `--plan-id` arm resolves through that persisted path and hands
it to the `gh` subprocess as `cwd`. The subprocess cannot start in a nonexistent directory,
and the resulting failure is funnelled into the `auth_failed` arm.

Proof by control: the identical call routed `--project-dir <main checkout>` returns
`status: success`, `state: merged`, `merge_commit_sha 28b578f1e…`. Same PR, same
credentials, same second — only the routing differs.

## Why this is worse than an ordinary misclassification

`output-template.md` Snapshot step 4 classifies `auth_failed` as **UNANSWERED**, stores
`state=unread`, and Emission step 1 item 1 routes `unread` to a **`[FAILED]`** headline.
So every worktree-using plan renders its terminal finalize summary as `[FAILED]` after a
successful merge, unless the renderer happens to route around the plan id.

And the classification is load-bearing in the *wrong* direction. An honest
`provider_call_failed` — or a new `cwd_unresolvable` — would still be UNANSWERED and would
still produce `[FAILED]`, which is the correct conservative behaviour. What `auth_failed`
adds is a **specific, confident, wrong instruction**: it tells the operator to run
`gh auth login`, which is not the problem, cannot fix it, and costs a credential re-issue
before anyone looks at the routing. The error envelope did not merely fail to help; it
actively pointed away from the cause.

That is the epic's theme at its sharpest. The two other findings this run filed under it
(`cb3735`, `1a1031`) are guards that report a clean verdict over an empty population — a
signal too confident about *nothing being wrong*. This one is the mirror: a signal too
confident about *what is wrong*. Both are the same failure to distinguish "I observed X"
from "I inferred X from the shape of a failure I did not actually diagnose".

## Directive

- **An `error_cause` is a claim about the cause, and it needs the same evidentiary
  discipline as a verdict.** A handler may only emit `auth_failed` if it observed an auth
  failure. A subprocess that failed to *start* has not reached the point where auth is
  testable, so its cause is unknown to that handler — `provider_call_failed`, or a typed
  `cwd_unresolvable`, not a guess dressed as a discriminator.
- **A persisted path is not a resolved path.** `resolve_plan_context` already raises
  `WorktreeResolutionError` for an *empty* `worktree_path`. A path that is non-empty but no
  longer exists on disk is the same class with the existence check missing. Check
  existence, then fall back to the main checkout or refuse with a typed error — never
  proceed with a dead cwd.
- **A phase that deletes a resource must retire the metadata that points at it.**
  `branch-cleanup` removes the worktree at order 70 and leaves `use_worktree: true` /
  `worktree_path: <deleted>` behind for every consumer at orders 80–1100 to resolve
  through. Clearing both at removal fixes this class at the source.
- **When two sanctioned readings disagree, the disagreement is the finding.** `ci_health
  verify` and `ci pr view` gave opposite answers about the same credential. Neither is
  authoritative over the other by convention, so a consumer that reads only one cannot
  detect the contradiction — which is how this reached the terminal output block.

## Evidence

- finding `866bcd` — full three-way observation, root cause, control experiment, and two
  independent remedies
- `output-template.md` § Snapshot Procedure step 4 (the `auth_failed` → UNANSWERED arm) and
  § Emission Procedure step 1 item 1 (`unread` → `[FAILED]`)
- observed on this run at the renderer's own snapshot, i.e. the last read before archive
