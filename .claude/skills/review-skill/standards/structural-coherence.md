# Structural Coherence Review

## What to look for

**Hierarchy violations** — SKILL.md should be the entry point (overview, workflow, references to sub-documents). Standards files should be self-contained within their topic. If a standards file refers back to SKILL.md for essential context, the split is wrong.

**Missing cross-references** — Documents that logically depend on each other but don't reference each other. The LLM would not know to load both.

**Orphaned documents** — Files in `standards/`, `references/`, or `assets/` not referenced from SKILL.md or any sibling document. The LLM would never find them.

**Wrong directory placement** — Content that belongs in a different directory:
- Prescriptive rules in `references/` (should be `standards/`)
- Background/explanatory material in `standards/` (should be `references/`)
- Templates not in `templates/`

**Section ordering within documents** — Does the document put the most actionable information first? A common anti-pattern: 200 lines of background before the actual rules. The LLM loads content sequentially — front-load what matters.

**Granularity mismatch** — One standards file covering 5 unrelated topics while another covers a single narrow aspect. Suggest splitting or merging when the imbalance hurts discoverability.

## Reordering recommendations

When suggesting reorder, state:
1. Current order (by section heading or filename)
2. Proposed order
3. Why — what becomes easier to find or act on
