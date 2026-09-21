envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:44:14Z

# Candidate lesson: widening a set stranded seven restated counts across six documents; the remedy that stuck was deleting the count

**Source records:** Q-Gate `b0f7dc`, `d4ebf1`, `64165f`, `7d84ca` (all fixed), `pr-comment` `53a438` (partially accepted, TASK-17), plus the contract-drift siblings `6fc38c`, `d26dd0`, `27d292`, `53d842`, `afcca1`.

## The observation

The taxonomy went from five members to seven. The change updated the closure count in two places. **Seven other sites across six documents still asserted a number**, and they did not all assert the same wrong number:

| Record | Site | Claim | Truth |
|---|---|---|---|
| `b0f7dc` | `manage-config/standards/data-model.md`, `manage-config/SKILL.md`, `marshall-steward/SKILL.md` | "five-member failure taxonomy" | seven |
| `d4ebf1` | `branch-cleanup.md:800` | "two of the seven blocking members" | six blocking |
| `64165f` | `automatic-review/SKILL.md:665` | "two of the seven blocking members" | six blocking |
| `7d84ca` | `workflow-integration-github/SKILL.md:511` | "the three caller obligations" | four |

Two distinct failure modes, and the second is worse:

- **Stale.** The three `five-member` sites are simply out of date. Each is a *closure claim that names the contract as its source of truth*, so it misstates the size of the very set it defers to. A reader who trusts the deferral is told the enumeration is smaller than it is.
- **Actively misleading.** "Seven blocking members" was never true at any point. Seven is the size of the FULL taxonomy; the blocking subset is six, because `participated_but_empty` is accounted-for and never blocking. A reader enumerating remedies looks for a seventh blocker and lands on `participated_but_empty` — which the contract itself names as "the member most often misread", and whose misreading turns a successful clean review into a completeness failure. The `64165f` site is the sharpest: the *correct* enumeration sits three lines above it in the same document, so the document contradicts itself inside one bullet.

## The remedy that was actually applied

Not "update the number". **Delete the number and let the owning document carry the size.** That was applied at all three `five-member` sites, at both blocking-count sites, and at the `7d84ca` cross-reference. A restated count is a duplicated fact with no mechanical link to its source; correcting it merely re-arms the same trap for the next widening.

## The residual, recorded rather than closed

`53a438` was **partially** accepted. One site was fixed (`automatic-review/SKILL.md:122-126` enumerated all seven members and then closed with "this document consumes that contract rather than restating it" — a self-contradiction inside one sentence). Two sites were **declined on purpose**: `SKILL.md:659-662` enumerates at the point of use inside enforcement-critical procedure, and `create-pr.md:201-210` records its own rationale in the adjacent sentence. Replacing either with a pointer costs a context switch for no correctness gain.

The residual that survives with them: the tree-wide guard in `test_bot_participation_contract.py` pins count prose and the contract's taxonomy table, so an **added or removed** member is caught — but a member **renamed** in a consumer document's inline enumeration is guarded by nothing. Two enumerations survive by design, so that gap survives with them. If it bites, the fix is to extend the tree-wide guard to member names, not to strip point-of-use prose.

## Companion mode: asymmetric update

Four sibling findings (`6fc38c`, `d26dd0`, `27d292`, `53d842`, `afcca1`) are the same edit-blast-radius failure without a number: a sentence updated in one document and left standing in its sibling. `d26dd0` is the canonical shape — the parallel sentence in the sibling consumer doc WAS qualified by the same change, so the omission is asymmetric update rather than deliberate scoping. `27d292` and `afcca1` are the same file contradicting itself: a verb summary at line 15 and a module docstring still carrying the pre-change scoping the commit had rewritten elsewhere in the same file.

## Why it is routed here

The taxonomy, its consumer documents, and the tree-wide guard are all `review-apparatus` surface. The transferable rule — *when a set is widened, the restated counts are the blast radius, and the fix is deletion not correction* — is a candidate for wider promotion.
