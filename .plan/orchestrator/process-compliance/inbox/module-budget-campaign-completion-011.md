envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-25T14:46:00Z
revision=1

# Process-rule issue: the pre-push gate's only input path is a hand-transcribed footprint CSV, so at 434 paths the caller feeds it a fabricated path set

Reporter: plan `module-budget-campaign-completion`, `default:pre-push-quality-gate` (order 10).

## The chain, and where it breaks

The step's own document is explicit that the footprint is derived, never persisted, and is the
single source of truth:

> **Read the live footprint** — `manage-references compute-footprint --plan-id … --worktree-path …`
> Extract the `files` array. This is the live footprint derived from the worktree … so it already
> reflects only what is actually modified now.

That array is then handed to the deterministic bundle-derivation seam:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:derive_gate_bundles \
  derive --files "{comma_separated_files}" --globs "{comma_separated_globs}" \
  --marketplace-root {worktree_path}
```

`--files` is the **only** input form. Verified against `--help`:

```
derive_gate_bundles.py derive [-h] --files FILES --globs GLOBS [--marketplace-root MARKETPLACE_ROOT]
  --files FILES  Comma-separated live-footprint paths (repo-relative).
```

No file path, no stdin, no alternate format. And the producer offers no matching escape either —
`compute-footprint --help` exposes only `--plan-id`, `--worktree-path`, `--base-ref`, with no
CSV/file emission. So the *only* way to get the true footprint into the gate is for the caller
to **retype it**, path by path, into a shell argument.

## What that costs, measured on this run

`compute-footprint` returned `files[434]`. Composing that list into the `--files` argument
produced a string that was **not the footprint**: it introduced at least 15 paths that do not
exist, among them

- `test/plan-marshall/manage-execution-manifest/test_refire_report_can_masense.py`
- `test/plan-marshall/manage-execution-manifest/test_refire_execution_manifest_fi_datetime_targets.click.o`
- `test/plan-marshall/manage-execution-man-archistest/manage-execution-manifest/…`
- `test/-marshall/manage-execution-manifest/…`
- `test/plan-marshall/manage-execution-manifest/test_manage_execution-manifest/test_…`
  nested roughly twenty levels deep, several times over

The shell then refused the command outright (`unexpected EOF while looking for matching quote`),
so nothing executed and no bundle set was derived. The point is not the syntax error — it is
that the fabricated paths are **plausible-looking test filenames of exactly the shape the real
ones take**, which is what makes the failure mode dangerous rather than merely clumsy.

## Why this must be fixed rather than worked around

The tempting workarounds are all false greens:

- **Pass a hand-picked subset.** The seam's output (`bundles`, `unresolved`) is a function of the
  input population. A narrowed list derives a narrower bundle set, the per-bundle loop gates
  fewer bundles, and Branch A's precondition — a clean whole-tree `quality-gate` — is then
  satisfied by a run over a population that is not the footprint. The step's own coverage
  discipline (`_gate_coverage`, the PARTIAL/UNKNOWN verdicts, "a run that established nothing at
  all" must be distinguishable from one that passed) exists precisely to forbid reading that as
  green.
- **Re-derive the bundle set by hand.** The document names `derive_gate_bundles` as the single
  derivation seam and says the rule "lives in exactly one place". A hand-derivation is a second
  implementation of it.
- **Re-try the transcription.** The failure is not bad luck; it is a property of retyping 434
  paths, and nothing in the current surface detects a wrong list. A retry that happens to
  succeed is not evidence of correctness.

The only honest dispositions are the two already available: report the input as unreadable and
let the step STOP (what this run did), or give the seam a faithful input channel.

## Requested

One of:

1. `derive_gate_bundles derive --files-file <path>` (and/or `-` for stdin), so the caller can
   pipe `compute-footprint`'s output through rather than through its fingers; **or**
2. `compute-footprint --format csv` (or a `--files-out <path>`) so the producer emits exactly the
   form the consumer takes; **or**
3. a single seam call that takes `--plan-id` + `--worktree-path` and performs the
   footprint→bundles derivation itself, removing the string hand-off entirely.

Option 3 removes the class rather than the instance: the two verbs already exist, they already
share the same repo-relative vocabulary, and the only reason a string crosses between them is
that neither can call the other.

## Secondary observation (separate, same surface)

The 271-entry `uncertain` list from `detect-artifacts` (filed as
`module-budget-campaign-completion-010`) is the same shape of problem at a different point: a
deterministic script produces a correct result whose *transport to the decision* is prose the
caller must retype. Two occurrences in one finalize pass is a pattern, not a coincidence.

## Evidence

- `manage-references compute-footprint` → `files[434]`, `live_count: 434`.
- `derive_gate_bundles derive --help` → `--files FILES` only.
- `manage-references compute-footprint --help` → no format/output flag.
- The rejected shell invocation, whose echoed argument contained the non-existent paths listed
  above; bash reported `Zeile 1: Dateiende beim Suchen nach »"« erreicht`.
- Cross-check of the fabricated names against the `compute-footprint` output: the real tree
  contains `test_refire_report_{an,cli,error,malformed,non,outer,seven,skipped,three,token}.py`
  and no `can_masense`, no `.click.o`, no `manage-execution-man-archistest`, no `-marshall/`.
