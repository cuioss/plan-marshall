# Identifier Validation Contract

This document is the single source of truth for the canonical identifier-validator contract across the marketplace. The validator foundation in `input_validation.py` provides regex constants, raising validators, `add_<id>_arg(parser)` builders, and the `parse_args_with_toon_errors()` helper. The canonical identifier vocabulary and its builders are listed in the SKILL.md Canonical Identifier Registry; this document records the deliberate breaking-compat edge cases and the adoption pattern for new scripts.

## Edge cases

These breaking-compat behaviours deviate from the strict pre-canonical contract. Each is intentional and documented here as the source of truth.

- **`sonar_rest.py` — canonical `COMPONENT_RE` rejects uppercase / path-shaped keys**: SonarQube allows component keys with uppercase letters and embedded path-like delimiters (e.g., `org:src/Main.java`). The canonical `COMPONENT_RE` `^[a-z0-9-]+(:[a-z0-9-]+)*$` is stricter and rejects such keys at the CLI boundary. SonarCloud projects with non-canonical keys receive `status: error / error: invalid_component`. This is the intended behaviour per the canonical-form contract.
- **`manage-tasks.py` — `--task-number` int coercion after validation**: The canonical `TASK_NUMBER_RE` is `^[0-9]+$`. The validator checks the raw string against `TASK_NUMBER_RE` first, then coerces to int, preserving the int-typed `args.task_number` downstream while gaining the canonical rejection-path semantics.
- **`manage-lessons.py` — `--lesson-id` with `action='append'` validates each element**: The flag is repeatable (`--lesson-id A --lesson-id B`). Each appended element passes through `validate_lesson_id` independently; a single malformed value in the list fails the entire invocation with `error: invalid_lesson_id`.
- **`parse_args_with_toon_errors()` foundation behaviour**: This helper centralises the argparse-to-TOON error path so consumer scripts get `status: error / error: invalid_<field>` output without per-script try/except boilerplate. It patches the root parser AND every subparser recursively, with prefix-anchored matching so `add_<id>_arg(parser)` works even on deeply-nested subparser trees (e.g. `ci.py`'s issue / pr / pr-prepare-body chain). `add_plan_id_arg(parser)` wires `type=validate_plan_id` directly so the validator runs at parse time (fail-fast) rather than via a deferred `require_valid_plan_id` call.

## Adoption pattern

When adding or migrating a script that accepts identifier-shaped flags:

1. Use the matching `add_<id>_arg(parser)` builder for every in-scope identifier instead of a raw `add_argument('--<id>')`.
2. Import the canonical regex from `plan-marshall:tools-input-validation:input_validation` rather than declaring an inline regex constant.
3. Wrap the parse / `main()` entry with `parse_args_with_toon_errors()` (or a single `try/except ValueError`) that emits `status: error / error: invalid_<field>` TOON before any filesystem, subprocess, or output side-effect.
4. Audit all three identifier-handling families per file end-to-end: argparse-only, parse-then-rebuild, post-parse-normalize.
5. Extend pytest with 6-axis rejection-path coverage (empty / path-separator / glob-meta / traversal / overlong / happy-path) for every newly-validated argument, exercised at the script-level CLI entry point — not at inner resolvers.
