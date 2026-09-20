envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T03:21:39Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
bundle=pm-plugin-development
confidence=high
source_plan=self-review-resweeps-full-surface-every-round
source_aspects=request-result-alignment,log-analysis,plan-efficiency
corroborates=2026-08-08-21-003

# Delete a restated count claim, do not correct it - correction failed three rounds running

Six `pre-submission-self-review` rounds on a 19-file diff found 5, 5, 2, 3, 4, 0 findings and cost **1,528,196 tokens**. **Rounds 2, 3, 4 and 5 each found defects the PREVIOUS round's own fix had introduced or left.** The recurring class was one thing throughout: *a restated count / range / endpoint / closure claim about a set that is declared elsewhere*.

The correction attempts, in order:

- **Round 1 → round 2.** The round-1 fix re-anchored four occurrences of a hard-coded "twenty" to registry-derived phrasing and **missed a fifth** (`96f00f`). The same fix also **strengthened** a closure claim ("one candidate sub-list per registry entry, as enumerated below") over an enumeration it left at 20 of 22 — before the fix the prose said "the twenty candidate sub-lists below", which at least agreed with the 20 blocks actually present (`4b475a`).
- **Round 2 → round 3.** The round-2 fix replaced "nineteen numbered detection rules … through worked-example clause pairs" with a structural claim, "one numbered rule per registry key". It **dropped the wrong count and kept the wrong endpoint, and the replacement structural claim was also wrong** (21 rules vs 22 keys) (`2f03eb`).
- **Round 3 → round 4.** The round-3 fix removed the explicit "Two entry shapes" count; **the replacement prose restated the same cardinality in words and carried the identical undercount** ("one adds a second navigational coordinate" — two do) (`6f98d3`). Digits to number-words is not a remedy.
- **Round 4 → round 5.** The round-4 fix wrote a *justification* into the standards document — "three consecutive self-review rounds each found this cross-reference stale". **The count was wrong** (the store shows two: `2dd0c0` in round 2, `2f03eb` in round 3), it was transcribed from round 3's own mistaken "THIRD consecutive round" self-assertion, it is itself a restated cardinality about a set that lives elsewhere and grows every round, and the sentence self-negates by declaring "no count is stated here" and then stating one (`b40170`, `41ae9f`). It also violated the project's "No version history" / "Current state only" documentation standards by recording transitional edit history in a standards doc.

## Solution

**Delete the restated claim. Do not correct it.** State no count, no range, no endpoint, and no per-key structural correspondence about an enumeration whose declaring source is another file or another section. Cross-reference the section and stop; point at the schema as authoritative rather than counting exceptions.

That is what converged. Round 6 was clean at 76 candidates on the full surface.

## Impact

Four independent correction attempts by four independent reviewers, each with the prior round's finding in hand, all failed. The failure mode is not carelessness — a restated cardinality is *correct at the moment it is written* and goes stale silently, so every corrected value is a fresh instance of the same defect with a fresh expiry date. Only removing the claim removes the class.

Corroborates lesson `2026-08-08-21-003` first-party. The delta this run adds, which the lesson did not carry: **correction is not a remedy for this class; deletion is** — established over three consecutive failed corrections rather than argued.
