envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T15:49:16Z

component=plan-marshall:manage-architecture
category=anti-pattern
bundle=plan-marshall
source_plan=inventory-blind-spot

# A discriminator over a derived collection's keys cannot separate "unknown" from "empty"

## Observation

Deliverable D2 of `inventory-blind-spot` specified two rules for `architecture files --category X`
that the outline presented as distinguishable:

- (a) "when `--category` names a key **absent from the module files block**, return `status: error`"
- (b) "an in-taxonomy category that is **genuinely empty** for this module keeps returning
  `status: success` with an empty list"

Q-Gate proved these are the **same condition** on identical input. Verified in
`_cmd_manage.py::build_module_files_inventory` (line 447): the files block is built with

```python
categorised.setdefault(category, []).append(...)
```

so **only categories that actually have files ever become keys**. An in-taxonomy but empty category is
therefore absent from the block — making (a) and (b) mutually exclusive on the same input. The
deliverable was **not implementable as written**, and both its success criterion and its test spec
required the two answers to be distinguishable.

## Root cause

**No category-vocabulary constant existed anywhere in `manage-architecture`.** The category names were
bare string literals returned by `_classify_marketplace` and `_classify_generic`. With no declared
vocabulary, the only set the author had to hand was the derived collection's keyset — and a derived
collection built by `setdefault(...).append(...)` structurally cannot represent an empty member.

## Solution

Introduce an explicit vocabulary constant and discriminate against **that**, never against the derived
collection:

```python
# _architecture_core.py
FILE_CATEGORIES = frozenset({...})   # the set the classifiers can emit
```

- `X not in FILE_CATEGORIES` → `status: error` (unknown category), regardless of module.
- `X in FILE_CATEGORIES` but absent from the module block → `status: success`, empty list.

A test asserts the error payload's published vocabulary **equals the constant**, so the documented list
(`standards/client-api.md`) cannot drift from the code again. That drift was already live: the
published list carried a `config` category neither classifier could ever emit.

## Generalisation

Whenever a verb must answer "is this name wrong, or is this name right but the answer is empty?", the
authority for *right* must be a **declared vocabulary**, not the keyset of a lazily-populated
aggregation. `setdefault`/`defaultdict`/`groupby` accumulators all share this shape: absence and
emptiness are the same state. The absence of a vocabulary constant is itself the smell — if the
category names only exist as return-statement string literals, no correct discriminator can be written.

## Impact

Applies to any `manage-*` script whose CLI takes a `--{dimension}` selector over values produced by a
classifier. The pattern to look for: a validation branch that tests membership in a computed dict
rather than in a module-level constant.
