envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=finding
created=2026-09-15T08:26:54Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug

# The self-review extension point has exactly one implementor, so a Java (or any non-plan-marshall) footprint gets zero surfacers — the consumer-repo half of PLAN-TRUTH-126's Instance 4

⛔ **ROUTED FROM API-SHERIFF'S EPIC LEDGER.** One Open Defects entry from the
`deployment-configurability` epic (`cuioss/API-Sheriff`), recorded 2026-09-10 from PLAN-07's landing.
Filed here by operator direction on 2026-09-15 and retired from that ledger in the same act.

## Verification at plan-marshall `origin/main` 7a028157e (read-only, 2026-09-15)

**PARTIALLY FIXED — the observability half shipped; the coverage half was never built.**

| Half | State | Evidence |
|---|---|---|
| *Is an empty result distinguishable from a checked-clean one?* | ✅ **FIXED** since PR #1397 | `_self_review_detectors.py:2331-2368` `CONTENT_CLASSES` with `other` as a total catch-all ("REPORTED as unclassified-but-present, never dropped from the denominator"); `by_class[C]{content_class,files,files_with_candidates,files_without_candidates}` (`ext-point-self-review-surfacing.md:94`); the zero-observation verdict *"self-review clean: no observation drawn from the files searched"* (`pre-submission-self-review.md:398`) and a not-run verdict (`:558`) |
| *Does anything actually read Java?* | ⛔ **STILL-VALID** | `ext-self-review-plan-marshall` is the ONLY implementor of the extension point (`git ls-tree`: zero other `ext-self-review-*` skills), and `_self_review_detectors.py` contains **0** occurrences of `java` |

So the step no longer *claims* a clean review it did not perform — that was PLAN-TRUTH-126's Instance 4
(**shipped**, PR #1397). What remains is that **in a consuming repository whose footprint is Java, the
self-review step has no surfacer at all**, on every plan, permanently.

## What this adds

Nothing on observability — that is done, and this message is not a re-report of it. It adds the
**consumer-side consequence**, which the meta-project cannot observe from inside itself: API-Sheriff is a
Java repository, every plan in this epic passed that step, and every one of those passes surfaced
nothing because no detector in the marketplace reads Java. ⚠ Whether that warrants an
`ext-self-review-java` implementor, or an explicit "no implementor for this domain" verdict at the step
(so a consuming repo sees the gap rather than a green), is the drain's call — the epic is reporting the
population, not prescribing the remedy.

---

## The retired API-Sheriff ledger entry, verbatim

- ⛔ **`pre-submission-self-review` RETURNS GREEN ON JAVA WHILE CHECKING NOTHING — no
  `ext-self-review-java` surfacer exists (2026-09-10).** Its detectors read **Python and skill docs**,
  so on a Java footprint it reports zero findings **because it looked at nothing**, not because
  nothing is there. ⛔ **This is not one plan's problem — every Java plan in this epic has passed that
  step, and every one of those greens was vacuous.** PLAN-07 is simply where it was noticed.
  ⚠ **It is the same shape the epic has now recorded five times** — a stated rule with no mechanism:
  issue #269's inventory claiming a check, the SNAPSHOT REMOVAL CONDITION carried as prose,
  `ApiSheriff-114` promising a browser-safe guarantee, `DescriptorInventoryWiringTest`'s unasserted
  count, and now a review step whose green is structurally uninformative. ⛔ **It belongs in the
  plan-marshall repository**, not here. Unowned locally. — source: PLAN-07 landing paste.
