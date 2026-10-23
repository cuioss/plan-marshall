# `format_toon` is a second projection: fields added to `to_dict` are silently dropped from default output

Severity: high. Bundle: **plan-marshall** (`script-shared` build result projection, `build-maven`). Filed under RULING 2026-10-09 (a).

## Sources

- corpus `2026-10-11-06-001`

## Consolidated statement

Two new fields on the Maven build result, `by_runner` and `population` (the latter carrying an `unmeasured` marker for runs whose test counts cannot be attributed), were added to the result's `to_dict` (JSON) representation only. `format_toon` in `script-shared/scripts/build/_build_format.py` projects the `tests` section to a fixed key list (`passed` / `failed` / `skipped` / `duration_seconds`), so both fields were silently dropped from the **default** TOON output of `run`, `parse`, and the timeout/killed evidence path.

That contradicted two documents at once: `build-maven/standards/maven-impl.md:110-112`, which describes the new fields, and `build-execution.md`'s "Both formats return the same fields".

Why it matters: the failure is an absence that reads as a fact. An agent running the default-format `maven run verify -pl core -am` sees no `by_runner` and reads the absence as a parallel/unmeasured build; a failing `-q` run's TOON `tests` block shows summed, ambiguous counts with no `population: unmeasured` marker, which is read as a measured result. The drift cost one self-review loop-back round; no reviewer or test caught it — the pre-submission self-review did.

## What is asked

- Treat `format_toon` as a second, independent projection that must be updated in the same change as `to_dict`: project the field in the relevant TOON section, document it in `build-execution.md`'s result structure, and assert it on the TOON path.
- Add a parity test asserting that every key `to_dict` emits for the `tests` section also appears in the `format_toon` output, so a JSON-only addition fails at build time. (Cheaper than the alternative guard, and it survives the planned removal of the self-review surfacers.)

## Evidence

As recorded by the sender. Not re-verified against HEAD in this run.
