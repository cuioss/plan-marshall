envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:59:44Z

component=plan-marshall:manage-solution-outline
category=bug

# Unanchored bullet regex in _extract_scope_field mangles prose into phantom file paths

`_plan_parsing._extract_scope_field`'s bullet regex carries **no start-of-line anchor**. When a
bullet fails to match at its own start, the scan finds an *interior* hyphen instead and harvests the
fragment after it as if it were a path.

## Observed

Q-Gate finding `eb52b1` (3-outline, resolution `taken_into_account`). Step 7 `sync-affected-files`
parsed 39 bullets across 8 headings in 4 deliverables and admitted **4 non-path strings** into the
plan's persisted footprint:

- `affected_files` (the MUTATION set) gained `none - this deliverable is read-only by construction`
  and `site pin sweep names` (mangled from `...plus any test the per-site pin sweep names`).
- `read_intent_files` gained `every path returned by the prescription-derivation query named in
  Change per file below` and `site remedy is resolved)` (mangled from
  `pyproject.toml (read - the alias table from which the per-site remedy is resolved)`).

Two consequences the finding names:

- Deliverable 1 declared it mutates **nothing**, yet its own no-mutation prose contributed a phantom
  entry to the mutation set. The declaration of no-mutation *became* a mutation.
- Deliverable 3's `Files to survey:` block lost **three of its four bullets** entirely
  (`.claude/skills/finalize-step-deploy-target/SKILL.md`, `pyproject.toml`, `test/**` were not
  extracted at all), so the survey declaration was simultaneously corrupt and incomplete.

## Why this is the residue, not a closed item

The finding was resolved by editing **this plan's outline prose** so the regex could not
mis-parse it, plus a `set-list` repair of the two footprint keys. The root cause was diagnosed
precisely in the resolution text — *"the bullet regex in `_extract_scope_field` has no start-of-line
anchor"* — and then **not fixed**. The parser is unchanged, so every future plan whose scope block
contains a hyphenated word (`per-site`, `read-only`, `write-new`) inside a bullet is exposed to the
same silent corruption. The verb reported `status: success` throughout.

## Rule

Anchor the bullet pattern to start-of-line (after leading indent) so a bullet that does not match at
its own start is **reported as unparsed** rather than re-scanned from an interior hyphen. A scope
extractor that silently drops 3 of 4 bullets and invents 4 paths must publish `bullets_parsed`
against `bullets_seen` and fail the phase when they disagree — the count is already computed
(`bullets_parsed` moved 39 → 38 during the repair), it is simply not gated on.
