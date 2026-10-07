envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:28Z

component=plan-marshall:phase-6-finalize
category=bug

Relayed from Token-Sheriff PLAN-11 (PR #718 / `4e1e88db`). ⛔ **This is the harness half of a two-sided defect.** The project half — that `-Ppre-commit` runs `rewrite:run` before its own `assert-no-rewrite-changes` dryRun, so the gate cannot fail by construction — is being fixed in Token-Sheriff as PLAN-12. ⚠ **Fixing only the project side leaves the harness still believing the command is non-mutating**, so this is not superseded by that plan. Observed on this run: the gate wrote a used-undeclared dependency into a POM, and no code path was prepared to own the diff.

component=plan-marshall:phase-6-finalize
category=bug
proposed_by=carry-refresh-token-through-code-exchange
signal_source=signal_script_failure_clusters_count

# pre-push-quality-gate declares mutates_source: false while the project's gate command mutates the tree

`pre-push-quality-gate` declares `mutates_source: false` in its frontmatter. The dispatcher reads
that declared fact FIRST and, on `false`, skips its commit instrumentation entirely — no staging, no
commit, no owner for any diff the step produced.

In this project the gate the step runs is Maven's `-Ppre-commit` profile, and that profile **writes
to the tree**: during this run it added a used-undeclared dependency to a POM. So the step produced
tracked-source changes that, by construction, no code path was prepared to own.

## The failure the declaration creates

- The step mutates tracked source.
- The dispatcher, trusting `mutates_source: false`, never instruments a commit.
- The dirty tree survives to `push`, where it either blocks the push or rides along uncommitted and
  unattributed.

The declaration is not merely inaccurate; it is the input that disables the machinery that would
have handled the mutation.

## Why "the project's gate is unusual" is not the answer

The step's frontmatter is a **fixed** fact, while the command it runs is **project-resolved**. A
per-project command can mutate or not mutate, so a single hard-coded declaration cannot be true for
every project the step runs in. Any step whose behaviour is delegated to a project-resolved command
cannot honestly declare a fixed `mutates_source` value.

## Corrective rule

Either:

1. `mutates_source` for a project-command-delegating step is **derived, not declared** — the
   dispatcher observes the tree after the command and routes on what it sees; or
2. the declaration is treated as a claim to be **checked**, exactly as the `post_run_review` band
   guard already checks `mutates_source: false` steps for a dirty tracked tree — a dirty tree under
   a `false` declaration is a loud finding, never a silent pass.

The second is the cheaper fix and already has a precedent in the same dispatcher; the first is the
structurally correct one for this step class.

## Provenance

Observed during the `6-finalize` run of plan
`carry-refresh-token-through-code-exchange` (PR #718). Related repository history: the
`-Ppre-commit` gate's fail-loud / zero-diff behaviour was itself the subject of PR #713, so the
mutating character of this gate is established, not incidental.
