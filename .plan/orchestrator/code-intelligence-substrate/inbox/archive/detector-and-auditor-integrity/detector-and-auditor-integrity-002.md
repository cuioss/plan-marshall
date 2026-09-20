envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=finding
created=2026-08-30T20:49:18Z

# phase-3-outline normatively promises a phase-4-plan Q-Gate guard for bucket `unknown` that phase-4-plan does not implement

## The divergence

`phase-3-outline/SKILL.md:480` states, normatively, in the bucket→profiles table:

> `unknown` → BLOCKS the deliverable. [...] Phase-4-plan emits a Q-Gate finding
> requiring the user to correct the affected-files list, or to have the owning
> build system's `BuildExtensionBase` declare a route for the unclaimed path(s).

No such guard exists. Three independent reads against HEAD `24c8ec5ee`:

1. `phase-4-plan` carries no `unknown` predicate and no Q-Gate action keyed on
   the classification bucket. The single occurrence of the word "bucket" in
   `phase-4-plan/SKILL.md` is line 423, inside the unrelated missing-profile
   guard — that guard's predicate is "deliverable enumerates existing test files
   AND `module_testing ∉ profiles[]`", and it names `test_only` / `mixed_code` /
   `mixed_with_docs` only.
2. `_check_declared_bucket` (`manage-solution-outline.py:236-358`) warns only on
   a declared value OUTSIDE the vocabulary. `unknown` IS inside the vocabulary
   (it is a member of `CLASSIFICATION_BUCKETS`), so it produces no signal there.
3. Consequently a deliverable whose resolved bucket is `unknown` — a genuinely
   undeclared file type, which is exactly what the classifier returns for paths
   no extension claimed and no owner-less rule recognized — proceeds to task
   creation unblocked, while the outline contract says it is blocked.

## Why it is not fixed in the originating plan

The divergence is PRE-EXISTING and lives wholly on `main`: `git diff main...HEAD`
over both `phase-3-outline` and `phase-4-plan` is empty for PR #1370. Closing it
means editing `phase-4-plan/SKILL.md`, which is outside that plan's Expected
Surface — the same out-of-surface class already escalated as qgate findings
`3e7381`, `00d481` and `08a140`.

Within PR #1370 the only in-surface action was taken: the docstring clause in
`_manifest_core.py` that asserted the non-existent enforcement ("`unknown` [...]
blocks the deliverable downstream in phase-4-plan") was DELETED, per that plan's
standing decision `a80dc5` (resolve an over-claiming clause by deletion, not by
rewriting). Deleting the false claim does not close the underlying gap — it only
stops the code asserting an enforcement that is absent.

## Remedy options (record only, not decided)

- **Option A — implement the guard.** Add an `unknown` predicate to phase-4-plan
  that emits the Q-Gate finding `phase-3-outline:480` already promises, routed
  back to phase-3-outline through the existing Q-Gate auto-loop (the same shape
  the missing-profile guard at `phase-4-plan/SKILL.md:423` already uses). Makes
  the normative sentence true.
- **Option B — retract the promise.** Rewrite `phase-3-outline:480` to state what
  actually happens (the bucket is recorded, nothing blocks), removing the
  unimplemented enforcement claim.

RECOMMENDATION: Option A. The blocking behaviour is the substantive intent — an
`unknown` bucket means a genuinely undeclared file type reaching task creation,
which is a real planning defect the outline contract was written to catch — and
the Q-Gate auto-loop it needs already exists and is already used by a sibling
guard in the same file. Option B would make the docs honest at the cost of
dropping a guard the contract's author intended.

Either option must land in one change with the other document, so the promise and
the implementation cannot diverge again.

## Detection note

This gap was found by a review bot reading the docstring, not by any check.
Nothing in the repository cross-checks a normative "phase-N emits a Q-Gate
finding" sentence against phase-N's actual emit sites, so this class of
promise-without-implementation is currently undetectable.
