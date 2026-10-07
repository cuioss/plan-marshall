envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:55:25Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# compile-report renders 13 script-failure findings as 13 empty bullets

The `Script Failure Analysis` section of this plan's retrospective report renders as:

```
## Script Failure Analysis

- [INFO]
- [INFO]
- [INFO]
   ... (13 identical empty bullets)
```

The underlying fragment is intact and rich — thirteen deduped argparse/internal-error findings, each
naming a component, subcommand, exit code, stderr excerpt and occurrence count. The JSON block below
the bullets carries all of it.

The cause is a schema mismatch the compiler does not detect. `script-failure-analysis` emits
`findings[]{type,subtype,component,subcommand,exit_code,first_timestamp,stderr_excerpt,occurrence_count}`
— deliberately, per `references/script-failure-analysis.md`, because the script does not judge and
therefore emits no `severity` and no `message`. The compiler's bullet renderer reads
`finding.severity` (defaulting to `info`) and `finding.message` (defaulting to empty), so every row
degrades to `- [INFO] ` with nothing after it.

Consequences:

- The human-readable half of the section conveys **zero** information while looking populated.
- Thirteen bullets of visible noise crowd out the sections around them.
- `compile-report` reports `sections_written: [... Script Failure Analysis ...]` and
  `status: success`. Nothing distinguishes "rendered thirteen findings" from "rendered thirteen
  blanks".

## Solution

- **Render the script-failure fragment with its own row shape** — one bullet per finding along the
  lines of `[WARNING] {component} {subcommand}: {subtype} (exit {exit_code}, x{occurrence_count})`,
  mapping `type` (`bug` / `anti-pattern`) onto severity.
- **Fail loud on an unrenderable row.** A findings row that produces an empty bullet body should
  route the section to `sections_dropped`, not sit in `sections_written` — the same
  present-but-unrendered rule the Conditional Rule already specifies for whole sections, applied at
  row granularity.
- **Add a fixture test** pairing each aspect's declared `findings[]` schema with the compiler's
  bullet renderer, so a schema that carries neither `severity` nor `message` is caught at build time
  rather than in a report.

## Impact

Every retrospective on a plan with at least one script failure — the section is conditional on
`errors_script > 0`, so it fires exactly when there is something to say and then says nothing.
Same family as the sibling report on `sections_omitted` mis-classification: the compiler's
three-valued outcome tracks headings, not content, so a section can be fully hollow and still ride a
clean `status: success`.
