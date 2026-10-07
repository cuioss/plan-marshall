envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=finding
created=2026-09-02T06:45:44Z

# Enforcement matrix for `askuserquestion-prompt-quality` is a hand-maintained mirror

Raised by CodeRabbit on PR #1378 (thread `PRRT_kwDOQ3xasM6eYroJ`, Maintainability /
Minor). Triaged during PLAN-05 finalize and deliberately NOT fixed in that plan —
routed here because the remedy is a design change wider than the plan's declared
surface.

## The finding

The set of obligations the rule mechanically checks (1, 2, 5) and the set it declares
as blind spots (3, 4) is stated independently in four places:

- `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/askuserquestion-patterns.md`
  — per-obligation `Enforced by:` markers, plus the `What this document does not enforce` section
- `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/SKILL.md`
  — the reference-table coverage summary
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md`
  — the check-to-obligation mapping and the blind-spot bullet
- `test/pm-plugin-development/plugin-doctor/test_analyze_askuserquestion_prompt_quality.py`
  — the tests validate provenance registration, not the documented coverage contract

None of the four derives from `_analyze_askuserquestion_prompt_quality.py`. A change to
the analyzer's checks can therefore leave all three documents asserting coverage the
code no longer provides, with nothing failing.

CodeRabbit cites the repository's own path instruction: *"Treat a hardcoded list that
must mirror a set defined elsewhere as a defect unless it is derived from that source
at build or run time."*

## Why it is credible rather than speculative

PLAN-05's own pre-submission self-review ran five full-surface rounds and filed eleven
findings, every one `contract_drift` — prose claiming more than the code delivers, in
exactly these files. Each was fixed by deleting the over-claim. That converged the
PROSE but left the STRUCTURE that produced it: four independent restatements of one
set, none derived. This finding is the structural form of the defect those rounds kept
hitting one instance at a time, which is the evidence that the class recurs rather
than a prediction that it might.

## Why PLAN-05 did not fix it

Deriving the documentation sections from an analyzer-owned coverage definition means
introducing a generation-or-verification step and a new source of truth, then wiring
three documents and a test to it. That is a new mechanism, not an amendment to the one
PLAN-05 shipped, and it lands outside the plan's declared Expected Surface. Fixing it
inline would have widened the plan's footprint at finalize time, after its gates had
already validated the narrower one.

## Suggested shape, not a decision

Two directions worth weighing before either is chosen:

1. **Derive** — an analyzer-owned coverage constant, with a plugin-doctor rule (or a
   test) asserting the documents agree with it. Closes the class; costs a new
   generation/verification seam and another mirror-checking rule.
2. **Collapse** — reduce the four statements to one authoritative site and have the
   others cross-reference it rather than restate it. Cheaper, no new mechanism, and it
   matches the deletion-over-correction convergence PLAN-05's self-review rounds
   established. Does not mechanically prevent recurrence.

The generalisable question is whether the marketplace wants a standing derived-doc
mechanism for rule coverage, since this rule is not the only one that publishes an
enforcement boundary in prose. That is an epic-level call.

## Disposition

Recorded here, unfixed, by operator instruction. PR #1378 merges without it; the
finding is not a merge blocker (Minor, maintainability, no incorrect behaviour today).
