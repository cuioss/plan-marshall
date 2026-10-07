envelope_version=1
sender_type=plan
sender_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:57:03Z

# Candidate lesson (recurrence): caller-side argparse rejections are one recurring defect, not N incidents — 10 distinct notations this run, 6 of them repeat offenders

**Routing note (read first).** This candidate was ALSO recorded into the global lessons
corpus during this plan's `lessons-capture` step, as a `## Recurrence` section appended to
lesson `2026-09-04-08-014`, because the dispatcher forwarded `orchestrated: false` in
error. The plan IS orchestrated by `truthful-signals`. Treat `2026-09-04-08-014`'s new
recurrence section and this message as ONE candidate; dedup on pickup rather than re-filing.

## Observation

The `lessons-capture` Signal Gate's Signal 3 counts distinct failing script notations across
three marker classes. On this run the count was **10**, and the marker breakdown is
uniform in a way that is itself the finding:

- `[FAILED]` work-log lines: **0**
- `voluntary_checkpoint -> error` reclassifications: **0**
- `[ERROR] ... script_failure` lines: **all 10**, and every one of them
  `failure_kind=argparse_rejection`

The ten notations:

| Notation | Rejection shape |
|---|---|
| `plan-marshall:plan-marshall:phase_handshake` | `script_internal_failure` (drift, not argparse) |
| `plan-marshall:manage-status:manage-status` | unregistered verb; `--get` vs positional on `metadata` |
| `plan-marshall:manage-findings:manage-findings` | undeclared flag on `list`; unregistered verb under `qgate`; missing required `--phase`; missing required `--source` |
| `plan-marshall:manage-solution-outline:manage-solution-outline` | verb paraphrase (`list-deliverables`); undeclared flag on `get-deliverable` |
| `plan-marshall:manage-tasks:manage-tasks` | undeclared flag on `list` |
| `plan-marshall:manage-references:manage-references` | missing required `--worktree-path`; unregistered verb |
| `plan-marshall:manage-architecture:architecture` | `--plan-id` placed AFTER the verb (it is a top-level router flag) — **4 separate occurrences** |
| `plan-marshall:workflow-integration-github:github_pr` | same router-scoped `--plan-id` misplacement |
| `plan-marshall:build-pyproject:pyproject_build` | verb paraphrase (`resolve-test-scope`) |
| `plan-marshall:manage-execution-manifest:manage-execution-manifest` | positional consumed by a sub-verb choice list |

## Why this is one defect and not ten

Every one of the ten is the SAME caller-side failure: a plausible-sounding verb or flag
transferred from surrounding prose rather than quoted from the live `--help` / executor
mapping. They cluster into exactly the recurrence signatures `agent-behavior-rules.md`
already enumerates — verb-paraphrase, verb-scoped vs router-scoped `--plan-id`, missing
required `--phase` / `--source`. Counting them as ten incidents inflates the signal and
hides that a single behaviour produced all of them.

## The load-bearing part

**Six of the ten notations are repeat offenders against `2026-09-04-08-014`'s original
list**: `manage-status`, `manage-findings`, `manage-solution-outline`, `manage-tasks`,
`manage-architecture:architecture`, `manage-execution-manifest`. Same surfaces, different
plan, different caller. Two consecutive plans have now produced a 9-then-10 cluster of this
shape **while the caller-side guidance was already in force**.

That is the epic-relevant conclusion: the existing remedy is caller-side prose, and
caller-side prose has now demonstrably failed twice in a row on the same six surfaces. The
`ARGUMENT_NAMING_*` plugin-doctor rule cluster is an edit-time structural guard on the
scripts, not on the callers, so it does not close this. Whatever closes it has to be
something a caller cannot skip — the argparse rejection envelope is already good (it names
the accepted set verbatim), so the gap is that nothing consults it BEFORE the call.

## Directive

- Treat a run's argparse-rejection cluster as ONE recurrence keyed on the behaviour, and
  report the distinct-notation count as a breadth measure, not an incident count.
- Before invoking any leaf subcommand whose exact flags are not already known this session,
  read the surface (`--help`, or the skill's leaf-command reference) rather than
  extrapolating from workflow prose.
- The router-vs-verb `--plan-id` placement is the single most repeated shape (4 of this
  run's occurrences on `architecture` alone, plus `github_pr`). It has an asymmetric fix —
  router flags go BEFORE the verb, verb flags AFTER — and getting it backwards is a silent
  exit-2 that bypasses the script body entirely.

## Evidence

- Signal 3 count 10, derived from `manage-logging read --plan-id ... --type work` over 576
  entries; marker classes counted separately (0 / 0 / 10)
- cross-ref `2026-09-04-08-014` (original 9-notation cluster, previous plan)
- theme match: an exit-2 that bypasses the script body while the caller reads the result as
  a completed call — confident-signal-hides-a-caveat
