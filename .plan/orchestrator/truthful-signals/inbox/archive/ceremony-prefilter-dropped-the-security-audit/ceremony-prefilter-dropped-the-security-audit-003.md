envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:46:31Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
created=2026-07-29

# A completeness claim is scoped, and the scope is the part everyone skips

Every "that's all of them" claim in this workflow carries an implicit scope, and the claim is
routinely read as unscoped. The claim is *true*; the reader's inference from it is false. This is
the same archetype as "a reviewer's list of call sites is a SAMPLE, not an enumeration" — this run
produced three fresh instances in a single plan, which is why it is worth reinforcing rather than
re-deriving.

## Evidence from PLAN-112

**Partial-rename residue recurred THREE times in the same file, across three separate review
passes, after two fixes each believed to be complete:**

1. Self-review pass 2 found item 2 of a list, three lines below the renamed item 1. The pass-1 fix
   had been **line-scoped** — it repaired the line the check flagged, not the construct the line
   belonged to.
2. An orchestrator whole-tree grep found two more occurrences in `test/`, **outside** the
   reviewer's stated scope. The self-review's verdict — "the only stale occurrence anywhere in
   `marketplace/` or `doc/`" — was literally true and operationally misleading.
3. PR triage then found the same file's **opening summary** still stale. Prose that restates a
   renamed identifier is residue too, and it lives in the one place a diff reader never looks.

**And from the review bots:** CodeRabbit named **two** `_resolve_footprint` call sites. The real
count is **three** (line ~686 in `_apply_canonical_verify_inactive`, still deferred).

## Solution

- **A rename is a whole-tree operation, always.** After renaming any identifier, sweep the entire
  repository for the old token — including `test/`, fixtures, docs, and prose — before declaring
  the rename done. Never fix only the flagged line; fix the construct and re-sweep.
- **Read every completeness verdict with its scope attached.** "Clean" from a scoped surfacer means
  *clean within that surfacer's scope*. Restate the scope out loud when quoting the verdict; if the
  scope excludes `test/`, the claim has not covered the change.
- **A reviewer's enumeration is a lower bound.** Treat every named-call-site list as "at least
  these", and derive the true population yourself (population-derived detection, per the existing
  `test/_shared/_dispatch_roster.py` pattern).

## Impact

Applies to the pre-submission self-review surfacer, to all review-bot findings, and to any rename
or signature change. The concrete tooling gap: the self-review surfacer's stated scope
(`marketplace/`, `doc/`) is narrower than the repository's actual footprint, so `test/` residue is
structurally invisible to it — a fix at the tool layer, not a habit to be remembered.
