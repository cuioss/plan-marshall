envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:35:30Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=plan-04-autonomy-gate-defaults

# Two documented invocations in automatic-review do not survive their own runtime

## Context

Both defects were found by review leaves during this run and recorded together in
the decision log at `11:18:35Z`. Both are cases where following the document
verbatim produces a runtime rejection.

### (1) Branch A's mark-step-done omits `--force`

`automatic-review/SKILL.md:990-994` is the terminal clean-pass snippet:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step plan-marshall:automatic-review --outcome done \
  --display-detail "..." \
  --head-at-completion {sha}
```

There is no `--force`. Every terminal pass that follows a loop-back iteration is
therefore writing over an existing step record and returns `error: conflict`.
Hit twice this run, at iterations 3 and 5 — the step's `firing_count` is 5 with
three recorded `loop_back` firings.

The overwrite is the *documented intent*: the Resumability table immediately
below (SKILL.md:1020-1024) states that a `loop_back` record is treated as
no-record on re-entry. Only the snippet is wrong.

### (2) The review_completeness template rejects on its own common path

`08:57:05Z`, `exit_code: 2`:

```
args: check --plan-id ... --refused-causes sourcery:quota --refusal-size-caps --measured-diff-size
error: argparse rejection
```

The caller wrote `--measured-diff-size` bare, as the trailing flag with no value —
exactly as it wrote `--in-progress-bots`, `--stale-participation-bots`,
`--declined-bots`, `--unrecognised-refusal-bots` and `--refusal-size-caps` on the
same line. Those five are `nargs='?'` and accepted. `--measured-diff-size` is not,
and rejected.

## Root cause

Defect (1) is a plain snippet omission against a contract the neighbouring
paragraph states correctly.

Defect (2) is **not** a documentation error in the naive sense — the doc says the
right thing in one place. `SKILL.md:1044` states plainly: "`--measured-diff-size`
is **not** a list flag: it takes a required value and is a single scalar ... Omit
it when unmeasured", and the canonical block renders it as
`[--measured-diff-size MEASURED_DIFF_SIZE]` without the inner brackets its ten
siblings carry.

The defect is a **coupling between two doc sites 330 lines apart**:

- `SKILL.md:710-718` gives the invocation TEMPLATE, and it interpolates
  `--measured-diff-size "{measured_diff_size}"` **unconditionally**, as the
  eleventh line of a block whose other ten lines are list flags.
- The paragraph immediately under that template argues the empty case is safe,
  and its argument is explicitly scoped: "The generated executor strips every
  empty-string argument before argparse sees it (`script_args = [a for a in
  script_args if a]`) ... What makes the empty case safe is that **every list
  flag** declares `nargs='?'` with `const=''`."
- `--measured-diff-size` is not a list flag and has no `nargs='?'`
  (`review_completeness.py:1878-1892`, `default=''` only).

So the executor's empty-argument stripping — the very mechanism the safety
argument relies on — converts the template's empty interpolation into precisely
the bare form this one placeholder cannot accept. On the common path (nothing
refused for size, so `measured_diff_size` is empty) the documented template
fails with exit 2.

The generalisable shape: **an interpolated-placeholder template whose
empty-value safety rests on a parser property that one of its own placeholders
does not have.** The template and the carve-out are both correct in isolation and
contradict each other in composition, and the caller reading top-to-bottom sees
the template first.

## Proposed action

1. Add `--force` to the Branch A snippet at SKILL.md:990-994, with a one-clause
   note pointing at the Resumability table for why the overwrite is intended.
2. For the template: either give `--measured-diff-size` `nargs='?'` with
   `const=''` so it matches its ten visually-identical siblings and the template
   becomes correct as written, or remove it from the unconditional template and
   state at the template site (not 330 lines later) that it is appended only when
   a size refusal was observed. The first is preferable — it removes the
   asymmetry rather than documenting it.
3. Whichever is chosen, the empty-value safety paragraph must name its scope at
   the template, since that is where a caller composes the call.

## Evidence

- decision.log `11:18:35Z` — both defects recorded contemporaneously, including
  "hit twice in this run alone (iterations 3 and 5)".
- script-execution.log:1281-1284 — the verbatim rejected `args` line and stderr.
- `review_completeness.py:1878-1892` — `--measured-diff-size` declared with
  `default=''` and no `nargs`.
- `automatic-review/SKILL.md:710-729` (template + scoped safety argument) vs
  `:1044-1046` (the carve-out).
