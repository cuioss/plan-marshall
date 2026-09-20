envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:13:32Z

# worktree-remove reports one boolean for two dirty states with opposite dispositions

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 1 lesson (`2026-08-24-16-001`) — `standalone`, not folded. **Suggested fold
target:** yours; it is small.

## ⛔ Read the scope limit first

The lesson's own words: **"The cause is unknown. This lesson records an observation, not a
diagnosis."** Four tracked files vanished from one worktree after a clean push, and the
worktree was force-removed at operator direction after investigation, so **the only instance
is gone**.

**Do not stage a plan to find the cause.** The routable part is the `worktree-remove` payload
change, which does not depend on the cause being found. That separation is why this is
routed at all rather than parked as a watch.

## What happened

During `phase-6-finalize`, four tracked files disappeared from the plan's worktree:

```text
 D LICENSE.md
 D build.py
 D pw
 D pw.bat
```

`git worktree remove` then refused — *"contains modified or untracked files"* — blocking
`branch-cleanup` **after the merge had already landed**. The step's constraints forbid
`--force` and require surfacing to the operator, so the run halted at cleanup **on deletions
it did not make**.

## What was established, and what was refuted

**Established:** scoped to the one worktree (both siblings and the main checkout clean);
ordinary tracked files (`100644`, and `100755` for `pw`); **post-push** (the last
`git status --porcelain` immediately before `git push` returned empty); exactly four files,
no other residue; fully recoverable from the index.

⭐ **A hypothesis was raised and refuted by its own test.** The obvious candidate was the
first `worktree-remove` call, which timed out at the script's internal 60s git bound and is
the only file-deleting operation in the window. **Refuted:** had removal begun deleting, the
`.plan/temp/` scratch written earlier would be gone. It is fully intact.

⚠ The four are a *coherent set* — the pyprojectx wrapper pair, the build entry point, the
licence — which suggests something treating them as a group rather than a filesystem sweep.
No ordering (index, alphabetical, top-level-first) accounts for sparing `AGENTS.md`,
`CLAUDE.md`, `README.md`, `pyproject.toml` and all of `.plan/`. **No evidence was found for
what.**

## The actionable half

⭐ **`worktree-remove` reports a single boolean `clean` for two dirty states whose
dispositions are opposite:**

| Dirty state | Correct disposition |
|-------------|---------------------|
| dirty with **uncommitted work** | refuse and preserve — there is work to save |
| dirty only with **deletions of tracked, index-clean files** | recoverable; preserving the tree saves nothing |

⛔ The step's own hint — *"Pass `--force` only after verifying the worktree is clean"* — is
**self-defeating on this path**: the verification it asks for is exactly what has already
failed.

⇒ Distinguish the two in the returned payload, and **report WHAT makes the tree dirty** (the
porcelain lines), so the operator decision does not require a separate manual probe.

**Matched pair required**, because the two states carry opposite dispositions: a worktree
dirty with uncommitted work must still refuse and preserve, AND one dirty only with
recoverable tracked deletions must be distinguishable from it in the payload. ⛔ A check
reporting a single boolean cannot tell them apart — which is the state that made this
incident require a manual investigation.

## A second, smaller conflation in the same lesson

The 60s internal git bound produced a **timeout** on the first call and the real refusal only
on the second. A transient timeout and a substantive refusal reach the caller as the same
`error: worktree_remove_failed`.

## The operator-facing rule, if nothing else is taken

**If a worktree shows unexplained tracked-file deletions at cleanup, do not force first.**
Establish scope (siblings + main checkout), timing (last known-clean observation), and
whether ignored/untracked content survived — those three discriminate a partial removal from
an external deletion cheaply, and they are what made the refutation above possible.

## Claim labels

- **OBSERVED** — the deletion, the blocked cleanup, the five established facts, and the
  refuted timeout hypothesis. All first-hand from the filing plan's own run.
- **OBSERVED (negative)** — that the cause is unknown. The lesson states this itself; this
  router did not weaken it into a suspicion.
- **HYPOTHESIS** — that the payload change is sufficient to make the class survivable
  without knowing the cause. This router's framing of the lesson's proposal. Confirm/refute
  at `workflow-integration-git` § `worktree-remove`'s return contract. Verify-at-outline.
