envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:08:48Z

component=plan-marshall:phase-6-finalize
category=bug

# branch-cleanup.md prescribes --measured-diff-size with an empty value that argparse rejects

## Observation

`phase-6-finalize/standards/branch-cleanup.md` Predicate 2 prescribes the `review_completeness check` invocation with `--measured-diff-size "{measured_diff_size}"`, and states the scalar "defaults to the empty string when the producer emitted none, or the field was absent or malformed — the empty fallback, never a hard failure".

On this run `fetch_findings` returned `measured_diff_size: ""` (no refusal), so the documented substitution yields `--measured-diff-size ""`. The generated executor strips empty-string arguments before argparse sees them, and — unlike the sibling LIST flags — `--measured-diff-size` does NOT declare `nargs='?'` with `const=''`; it takes a required value. The call was rejected with argparse exit 2: `argument --measured-diff-size: expected one argument`.

The document's own quoting note explains the executor's empty-arg strip and the `nargs='?'` defence for the list flags, and then prescribes the same empty-substitution shape for a scalar flag that lacks that defence.

## Recommended rule

Either give `--measured-diff-size` `nargs='?'` with `const=''` like its sibling list flags, or state in the prescription that the flag is OMITTED ENTIRELY when `measured_diff_size` is empty. A documented invocation must be one argparse accepts on every value the document itself says the field can take — including its own documented empty fallback.

Generally: when a doc explains a quoting/stripping hazard and names the defence some flags carry, it must not then prescribe the hazardous shape for a flag that lacks the defence. The explanation is where the mismatch becomes invisible.

## Recurrence signature

Same class as the `q-gate-validation --component` mismatch reported earlier in this same plan: **a documented invocation that argparse rejects**. This is the standing "never invent script subcommands / flags" failure mode arriving from the opposite direction — the doc, not the agent, supplies the invalid shape, so agent-side discipline cannot prevent it.

## Workaround applied in-run

The flag was omitted entirely rather than passed empty; `review_completeness check` then returned `participation_complete: true`.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`)
- Q-Gate finding `2b85dc`, phase `6-finalize`, type `bug`, component `plan-marshall:phase-6-finalize`
- Resolution: `taken_into_account` — held for a follow-up plan owning `phase-6-finalize/standards/branch-cleanup.md`
- Paired script-failure record: `[ERROR] (plan-marshall:execute-script:2) script_failure notation=plan-marshall:automatic-review:review_completeness exit_code=2 failure_kind=argparse_rejection` at 2026-09-03T10:23:04Z
