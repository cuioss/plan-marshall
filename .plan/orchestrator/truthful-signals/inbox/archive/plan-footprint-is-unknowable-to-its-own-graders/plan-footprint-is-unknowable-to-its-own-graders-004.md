envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T14:44:23Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# Aspect 12's capture supplies no base, so 4 of its 5 rules skip on every plan

## Context

`check-manifest-consistency`'s own canonical block states: *"Supply `--base-ref` whenever `--diff-file` is absent — it is how the script obtains a diff at all."*

The workflow's documented capture command for aspect 12 (`SKILL.md` § "Aspect 12 (manifest-decisions, conditional)") passes **neither**:

```
check-manifest-consistency run --plan-id {plan_id} --mode {live|archived} > work/fragment-manifest-decisions.toon
```

So the aspect records `base: unknown`, `diff_available: false`, and every diff-fed rule reports `indeterminate` or `skip` — on every plan, permanently.

Worse, `check-artifact-consistency` **forwards** its `affected_files_exact_match` set mismatch into this aspect: `forwarded_to_manifest: true`, message *"Set mismatch — deferred to manifest aspect (see check-manifest-consistency)"*. The deferral target structurally cannot receive it.

## Root cause

The aspect is a footprint consumer that was never wired to the shared footprint resolver, and its documented capture supplies no substitute. `retro_sections.py` already records that it "publishes no footprint-degradation verdict at all" and is deliberately excluded from the `FOOTPRINT_CONSUMING_ASPECTS` roster for that reason — but the reason it publishes nothing is that it is handed nothing.

## Proposed action

Either wire `check-manifest-consistency` to `resolve_footprint` like its three siblings, or pass `--base-ref` in the documented capture. Then reconsider its roster membership on the test `retro_sections.py` already states: *"Add it here the moment it grows a degradation verdict, not before."*

Separately: `check-artifact-consistency` should not defer a real finding to a consumer that reports `indeterminate` unconditionally.

## Evidence

- This run's fragment: `base: unknown`, `files_total: 0`, `diff_available: false`, `summary: passed 1, skipped 4`. The four skips are `docs_only_diff`, `early_terminate_diff`, `tests_only_diff`, `branch_cleanup_changes`.
- The same run's three sibling aspects all resolved the footprint (33 paths) through the shared chain, so the evidence was available and simply not handed over.
- The forwarded mismatch was real: `outline_only[1] = collect-fragments.py`, `references_only[1] = logging-gap-analysis.md`.
