envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T15:19:45Z

component=plan-marshall:phase-6-finalize
category=bug
title=A shared-namespace identifier collision is invisible to textual conflict detection - baseline-reconcile said no_overlap

# A shared-namespace identifier collision is invisible to textual conflict detection

Found live during PR #1067's merge attempt. Corrected in-run by renumbering; the detection
gap is not remediated.

## What happened

While PR #1067 sat in the merge queue, upstream PR #1066 landed
`doc/adr/012-Plan-scoped_operator_answers_overlay….adoc`. PR #1067 held its own
`doc/adr/012-A_capability_spanning_both_extension_hierarchies….adoc`, allocated by
`adr-propose` at 11:56 against a corpus scan that counted 11 ADRs.

Both signals said the branch was clean:

- `baseline-reconcile` reported `classification=no_overlap`;
- the rebase applied cleanly, no conflict.

Both were **correct** — and both were measuring the wrong thing. The two files have
different names, so there is no textual overlap and no conflict to raise. The collision is
in the **number**, which is a semantic property of the filename prefix, not of the bytes.

Had it shipped, `main` would carry two distinct documents both claiming to be ADR-012.

## How it was actually caught

Manual inspection at merge time, after the merge lock was already held (13:08:51) and one
minute before the merge would have completed. The corrective action — abort, release the
lock, rebase onto the new `origin/main`, renumber 012/013 → 013/014, re-verify, re-push,
re-acquire — cost roughly 90 minutes of the plan's wall clock.

It was caught by vigilance, not by a gate. Nothing in the pipeline would have stopped it.

## Root cause

`adr-propose` allocates a number by scanning the corpus **at proposal time**, on the
pre-rebase base. Between allocation (11:56) and merge (15:02) the base moved three times.
No step re-validates the allocation against the base it will actually land on.

More generally: the freshness machinery this project has built is keyed on
`worktree_sha` and on textual diff overlap. Neither can see a monotonic-namespace
collision, because the colliding artifacts do not touch the same bytes.

## The class, not the instance

ADR numbers are one member of a family. The same property holds for anything drawn from a
shared monotonically-allocated namespace where two branches can each take the next value:

- ADR numbers (this instance);
- database migration numbers / timestamps;
- reserved error or exit codes;
- lesson ids allocated `YYYY-MM-DD-HH-NNN` — two plans finalizing in the same hour can
  collide identically;
- any `NNN`-prefixed ordered document set.

Every one of them is invisible to `git` conflict detection and to `no_overlap`.

## Proposed action

1. Add a **namespace-collision probe** to the pre-merge barrier (not to `adr-propose`,
   which runs too early): after the final rebase, re-scan `doc/adr/` on the actual merge
   base and refuse a number already claimed. Cheap, deterministic, scriptable.
2. Generalize it: the probe should take a namespace descriptor (directory + filename
   prefix pattern) so migration numbers and lesson ids can register the same check without
   new code.
3. Standing rule for the epic's collection: **`no_overlap` from a textual reconciler is a
   statement about bytes, not about meaning.** A clean rebase is not evidence that two
   branches did not claim the same name in a shared namespace.

## Evidence

- `logs/decision.log:84` — the full abort record, including the explicit observation that
  `baseline-reconcile reported classification=no_overlap because the two ADR filenames
  differ, so the collision is invisible to textual conflict detection`.
- `logs/decision.log:81` — the 12:06 freshness-reconcile entry still referring to
  `doc/adr/012 and doc/adr/013`, i.e. the pre-renumber allocation.
- `status.json` `phase_steps[6-finalize].adr-propose` — `2 ADR(s) proposed
  (ADR-013,ADR-014 after collision renumber)`.
