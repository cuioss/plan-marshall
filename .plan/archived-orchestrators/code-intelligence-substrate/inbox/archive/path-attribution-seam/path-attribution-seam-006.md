envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T18:34:11Z

component=plan-marshall:phase-3-outline
category=bug
bundle=plan-marshall

# A deliverable's `domain` copied from its siblings can contradict its own `module` — and skill resolution masks it, so only domain-KEYED routing exposes the error

## What happened

PLAN-CIS-023's deliverable D7 was the documentation deliverable in a set of seven. Six siblings correctly declared `module: plan-marshall` / `domain: plan-marshall-plugin-dev`. D7 declared `module: documentation` but kept `domain: plan-marshall-plugin-dev`, inherited verbatim from the siblings.

The architecture inventory contradicts it outright:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture suggest-domains --module documentation
```

returns exactly **one** applicable domain — `documentation` (confidence high, signals `doc directory in doc` and `build_systems=documentation`).

D7's own change text made the mismatch self-evident: it mandates that the SVG re-layout conform to `pm-documents:ref-svg-diagrams`, a skill that belongs to the documentation domain, not to `plan-marshall-plugin-dev`. Caught by the 3-outline Q-Gate (`architecture_constraints`) and corrected to `domain: documentation`.

## Why it survives casual inspection

**Skill resolution is unaffected**, and that is precisely what hides the defect. Phase-4 resolves skills through the **module's** `skills_by_profile`, and the `documentation` module already carries `pm-documents:ref-svg-diagrams` and `pm-documents:ref-asciidoc` under the implementation profile. So the right standards load, the deliverable executes correctly, and every observable behaviour during planning and execution is indistinguishable from a correct declaration.

The single exposed surface is **domain-keyed finding routing**. A finding raised against D7 would resolve `pm-plugin-development:ext-triage-plugin` instead of `pm-documents:ext-triage-docs` — triaging an AsciiDoc/SVG defect through the marketplace-plugin triage extension. The failure is latent: it costs nothing until a finding is actually raised against that deliverable, and then it silently routes to the wrong triage logic rather than erroring.

## The rules

**Do X — validate a declared `domain` against the declared `module`'s inventory, per deliverable.** `architecture suggest-domains --module {module}` is the authority and it is a single cheap call. When a deliverable's `module` differs from its siblings', its `domain` must be re-derived, never inherited.

**Do X — treat "my module differs from my siblings' module" as the trigger.** That divergence is mechanically detectable at outline time across the deliverable set, without understanding any deliverable's content.

**Not Y — do not use "the right skills loaded" as evidence the metadata is correct.** Skill resolution routes through `module`; finding triage routes through `domain`. Two different keys, and only one of them is exercised on the happy path. A deliverable can execute flawlessly end-to-end with a wrong `domain` and nothing will report it.

**Not Y — do not copy a metadata block across deliverables and edit only the field you came to change.** `module` was correctly updated to `documentation`; `domain` was left at the inherited value. Partial edit of a copied block is the mechanism.

## Generalisation worth checking

The shape is *paired metadata fields where only one is exercised on the happy path*. Any such pair will drift silently. It is worth asking whether other deliverable-level or task-level field pairs in the planning artifacts have the same property — a validator that asserts `domain ∈ suggest-domains(module)` for every deliverable at outline close would make this class structurally impossible rather than Q-Gate-dependent.
