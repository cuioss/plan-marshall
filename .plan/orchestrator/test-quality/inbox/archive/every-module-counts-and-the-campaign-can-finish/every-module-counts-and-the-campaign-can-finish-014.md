envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:34:13Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Self-review found the same defect twice in the same regex and twice across sibling instruments, one round apart each

## Context

The four 6-finalize self-review findings are two pairs, and both pairs are the same shape: a defect found in round N whose twin was sitting in plain view and was only found in round N+1.

**Pair one — the same regex, twice.**

- Round 1 (finding ecfe90): `_INLINE_HEADING`'s `[-=~_*]{2,}` lower bound admits ordinary prose comments as banners; `# --plan-id is forwarded to every child call` matches. 209 comments across `test/` and `marketplace/bundles/` were admitted as banners on the two-character bound alone. Remedy: raise to `{3,}`. Fixed in 5f032c50.
- Round 2 (finding 6931ed): with `{3,}` in place, `# -*- coding: utf-8 -*-` matches, because `-*-` is a 3-character run drawn from that class. Verified by executing `collect_banners` against a synthetic module: the PEP 263 cookie becomes a banner titled `coding: utf-8` at line 1, `scan_module` misattributes `collection_size` under it, and deleting only the cookie line drops the finding to zero. Remedy: require a HOMOGENEOUS run. Fixed in 1ce6ec55.

The round-1 fix changed a magic number in a heterogeneous character class. The round-2 finding notes that the lines 76-82 comment's own stated rationale for `{3,}` does not hold against a real Python comment form.

**Pair two — the same string, two sibling instruments.**

- Finding c3cc4b: `_banner_attribution.py:327` `--after-ref` help reads "the ref to compare against", which names the yardstick role `--before-ref` actually holds. An operator who acts on that reading swaps the refs, and the swap INVERTS the gate: `introduced` becomes the set the change removed, so `main()` exits 0 on a change that introduced a misattribution.
- Finding 751796: `_definition_duplication.py:216`, byte-identical defect. Lower blast radius (that `main()` always returns 0, so a swap misleads rather than inverting), but the same two readings.

The third sibling, `_fidelity_diff.py:254`, already carried the unambiguous form ("the ref the refactor produced"), and `_banner_attribution.py`'s own docstring says all three instruments follow it.

## Root cause

Round-scoped review. Each finding is judged and fixed on its own, so a defect class is not swept: a fix to a boundary constant is not followed by re-asking the boundary question, and a defect in one member of a documented sibling set is not followed by checking the other members — even when the module's own docstring names the set and one member already holds the correct form.

Both pairs did carry a `defect_class` tag in the finding text (`regex_overfit: 1 finding(s) in this class this round`, `ambiguous_wording: 2 finding(s) in this class this round`), so the class is already computed. It is scoped to the round.

## Proposed action

1. When a finding names a member of a set the source itself documents (sibling instruments, a shared docstring contract), extend the check to every member in the SAME round rather than waiting for the next one. The `ambiguous_wording` pair shows this works — both were caught together once the class was looked at across files.
2. When a fix changes a threshold or a character class in a regex, re-run the detector's own rationale against the new value before accepting it. Round 2 exists because `{3,}` was adopted without asking what else `[-=~_*]{3,}` admits.

## Evidence

- qgate findings ecfe90, 6931ed, c3cc4b, 751796 (6-finalize, `pm-plugin-development:ext-self-review-plan-marshall`, warning), all `fixed`
- Landed changes 5f032c5077b3154fd7f2bcb0451148deaccd1065 and 1ce6ec55a5d3430a1b1356e1e7fd8b89504614bb
- Round 2 ran roughly four hours after round 1 on the same file
