envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T10:38:36Z

component=plan-marshall:workflow-integration-git
category=bug

# `prune-local-and-remote-ref` guards the remote ref's absence but not the local branch's, so it always errors on the documented cleanup order

`_cmd_prune_ref.cmd_prune_ref` deletes two things and treats their already-gone states
asymmetrically. Only the second one is guarded.

## Measurement

`marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py`:

**Local branch — no existence guard (lines 182-190):**

```python
rc, _out, err = run_git(['-C', str(project_path), 'branch', '-D', head_branch])
if rc != 0:
    return {
        **envelope,
        'status': 'error',
        'error_type': 'branch_delete_failed',
        'local_deleted': False,
        'message': f'git branch -D {head_branch} failed: {err.strip() or "non-zero exit"}',
    }
```

**Remote-tracking ref — guarded, and its absence is a graceful success (lines 201-217):**

```python
rc_sr, _sr_out, _sr_err = run_git(['-C', str(project_path), 'show-ref', '--quiet', ref_path])
if rc_sr != 0:
    # Remote-tracking ref is already absent — graceful no-op.
    return {
        **envelope,
        'status': 'partial',
        'local_deleted': True,
        'remote_ref_deleted': False,
        'remote_ref_warning': f'remote-tracking ref {ref_path} was already absent — no-op',
    }
```

The module docstring lists the guard as invariant §5.3.3 and scopes it explicitly to the
ref: *"Internal show-ref guard before `update-ref -d` (Drift 3 resolution)."* The local
branch has no counterpart invariant. `git branch -D` on a nonexistent branch exits non-zero,
so the unguarded path returns `status: error, error_type: branch_delete_failed`.

## Why it fires every time, not occasionally

On the documented cleanup order, `worktree-remove` runs first and deletes the feature
branch. By the time `prune-local-and-remote-ref` runs, the local branch is already gone —
so the verb's *normal* path is the one that returns an error. This is not a race or an edge
case; it is the ordinary sequence.

The result is a permanent false negative in the finalize signal: a `status: error` that
means "the thing I was asked to remove was already removed", which is the definition of a
successful idempotent cleanup. It is indistinguishable in the payload from a genuine
failure (a branch that exists, is checked out elsewhere, and could not be deleted).

## Solution

Mirror the guard the remote ref already has. Before `git branch -D`, probe with
`git show-ref --quiet refs/heads/{head_branch}` (or `git rev-parse --verify --quiet`) and,
on absence, return the already-done shape rather than the error shape:

```python
rc_lb, _out, _err = run_git(['-C', str(project_path), 'show-ref', '--quiet',
                             f'refs/heads/{head_branch}'])
if rc_lb != 0:
    # Local branch already absent (worktree-remove deleted it) — graceful no-op.
    # fall through to the remote-ref stage with local_deleted=False, already_absent=True
```

Two contract points worth settling in the same change rather than leaving implicit:

- **Do not collapse "already absent" into `local_deleted: True`.** The field means *this
  call deleted it*; reporting a deletion that did not happen swaps one false signal for
  another. Carry a distinct `local_already_absent: True` alongside `local_deleted: False`.
- **Decide what `status` an all-already-absent run returns.** The remote branch already
  uses `partial` for its own already-absent case, so `partial` is the consistent answer and
  needs no new vocabulary — but the caller in `branch-cleanup.md` must then treat `partial`
  as non-blocking, which is the actual behaviour change.

The safety invariants are unaffected: §5.3.1 (never delete the checked-out branch) still
runs first, and §5.3.2's force-delete rationale (post-merge squash merges make safe-delete
refuse) is about a branch that EXISTS.

## Impact

Every finalize run that reaches branch cleanup on the documented order — i.e. the normal
path, not an exceptional one. The observable cost is a recurring `branch_delete_failed` in
the finalize record that readers learn to ignore, which is the worst state for a signal to
be in: still emitted, no longer read, and therefore unable to report the real failure it
was built for.
