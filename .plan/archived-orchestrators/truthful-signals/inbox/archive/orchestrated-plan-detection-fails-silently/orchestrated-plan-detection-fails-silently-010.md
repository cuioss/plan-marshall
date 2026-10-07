envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:16:50Z

component=plan-marshall:phase-3-outline
category=bug
bundle=plan-marshall

# The outline declared an affected-file path that has NEVER existed, and three consumers counted it without one existence check

## What happened

`solution_outline.md` deliverable 1 declares this affected file:

```
test/plan-marshall/marshall-orchestrator/test_finalize_orchestration_routing.py
```

That path has never existed in repository history — `git log` over it returns empty. The real file is:

```
test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py
```

Same basename, different directory. **The outline declares the real path too**, under deliverable 2. So one real file was declared twice under two paths, one of them fabricated.

What makes it worse than a typo: the outline describes the phantom path's *contents* in confident, specific detail — "`TestDetectionSeam` (lines 102-119) consumes the same function and breaks on the arity change at FOUR sites: three `== (False, None, None)` equalities … plus the 3-way unpack at line 106." Every one of those details is **true of the real file**. The outline read the real file, then attributed what it read to a path that does not exist.

## The blast radius

Execution was not misled — it edited the real file and the merge landed 5 correct files. The damage is entirely in the declared surface, and it propagated into three derived signals before anything could catch it:

1. **Scope estimate** — `decision.log` 13:18:58: `scope_estimate=single_module (distinct_paths=6 …)`. Six paths, one imaginary.
2. **Manifest compose** — `decision.log` 13:55:45: `affected_files_count=6 from the deduplicated union of list-deliverables affected_files`. The dedup could not collapse the duplicate because the two spellings differ.
3. **Retrospective recall check** — declared 6, realized 5, so declared-vs-achieved recall can never reach 100% on this plan no matter what was built.

Not one of the three stat'd the path.

## Root cause

Nothing between "the LLM writes an `Affected files:` line" and "downstream consumers count those lines" verifies that a declared path resolves on disk. A path is accepted as a fact purely because it was written in the right section.

## Corrective rule

**Add a declared-path existence sweep to the phase-4-plan Q-gate (or to `manage-solution-outline validate`).** For each deliverable's `Affected files:` entry: stat the path in the worktree. A path that neither exists at HEAD nor is explicitly marked as a new file is a Q-gate finding, not a warning.

This is a ~30-line deterministic check with zero judgement, and it would have caught this defect at 13:37 instead of at post-merge retrospective.

Second, weaker rule: **a `(new file)` / `(write-replace)` annotation is a claim, not an exemption.** The sweep must treat "declared as modified" as asserting prior existence.

## Why it matters for truthful signals

The outline was *more* convincing for being wrong in this particular way. A vague declaration invites checking; a declaration carrying exact line numbers and an enumerated four-site breakage reads as verified-at-HEAD evidence. The outline even has a section titled "Verified at HEAD (premise check)" — and that section is accurate about the regex, so the document's overall credibility carried the one unverified path through unexamined.

**Detail is not verification.** A confident enumeration sourced from the right file and attributed to the wrong path is indistinguishable from a correct one at every consumer downstream.

## Recurrence signature

Sweep archived outlines for `Affected files:` entries whose path does not resolve at the plan's base SHA. Expect duplicates-under-two-spellings to be the dominant sub-shape, since the LLM reads a real file and then reconstructs its path from the module it *expects* the file to live in.
