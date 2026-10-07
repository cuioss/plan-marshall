envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:47:19Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug

# A content class no detector targets produced zero candidates, and zero candidates read as clean

One of the five content classes the self-review swept — AsciiDoc prose in `doc/user/configuration.adoc` — is covered by **no detector at all**. The surfacer therefore returned zero candidates for it, and zero candidates is indistinguishable, in the verdict, from "swept and clean."

Re-firing the step could never change this signal. The file was ultimately fixed only because the operator opened it by hand and read it — twice.

## Evidence

`8b8895` (6-finalize, resolved `accepted` by operator override): "may_close fails cond-3: round disclosed 1 of 5 content classes swept by no detector (`doc/user/configuration.adoc`), plus 17/82 structural/prose skew. Operator investigated the zero-candidate file directly and applied a real fix (added the minimal-deviated lessons-housekeeping step to the minimal-floor enumeration, matching sibling docs this plan already corrected)."

The acceptance rationale states the structural nature plainly: "no detector targets AsciiDoc bullet-list content, so **re-firing cannot ever change this signal**."

The defect found by hand was real and was of exactly the class the plan was sweeping for — a floor enumeration left stale by this plan's own reclassification, in a user-facing document.

## Rule

A per-class candidate count of zero must state **which kind of zero it is**:

- *swept by a detector, found nothing* — a clean zero, and evidence.
- *no detector covers this class* — an UNSWEPT zero, and evidence of nothing.

The surfacer should report detector coverage per content class alongside the candidate count, so the verifier can distinguish them and so a class with no detector is visibly a gap rather than a pass. Without that, the review's headline verdict silently averages swept and unswept surfaces together — a confident signal over a surface no instrument examined.

The credit here belongs to the verifier's cond-3, which DID disclose the uncovered class rather than absorbing it. The gap is that disclosure had no route to a remedy except operator override, and the fix had no route except manual reading.

## Note on routing

The run's own resolution text records this was filed as global lesson `2026-09-19-12-001` during execution. As this plan is orchestrated (`epic post-run-quality`), it is re-transmitted here so the epic holds it with the cross-plan context; the orchestrator should reconcile the two rather than carrying both.
