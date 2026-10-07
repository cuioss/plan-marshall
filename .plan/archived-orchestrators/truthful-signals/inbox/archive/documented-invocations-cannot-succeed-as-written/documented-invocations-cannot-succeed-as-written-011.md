envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:59:52Z

component=plan-marshall:plan-retrospective
category=bug

# A caller-side invented notation is classified as a script-internal bug in a script that does not exist

The script-failure taxonomy attributes an executor **notation rejection** — a caller typing a script
name that was never registered — to the non-existent script itself, as
`type: bug, subtype: script_internal_error`.

## Observed

Two of this run's 11 unique failures:

```text
component: plan-marshall:manage-status:manage_status
subtype:   script_internal_error
type:      bug
stderr:    Invalid notation: 'plan-marshall:manage-status:manage_status'
           The third part 'manage_status' appears to be a subcommand, not a script name.

component: plan-marshall:manage-execution-manifest:manage_execution_manifest
subtype:   script_internal_error
type:      bug
stderr:    Invalid notation: 'plan-marshall:manage-execution-manifest:manage_execution_manifest'
```

Both are `type: bug` filed against a `component` that is not a component. The executor's own stderr
already names the cause exactly and names it as a **caller** error. The classifier reads the exit
code (1) and the empty-subcommand field and lands on `script_internal_error`.

## Corroboration that the form was invented, not documented

`architecture search --content --pattern "manage-execution-manifest:manage_execution_manifest"`
returns `count: 0` over `files_scanned: 5335`, `unreadable: 0`, `truncated: false`, `elided: 0` — a
clean-coverage zero within the inventory. The sibling sweep for `manage-status:manage_status` returns
19 hits in 10 files, and **every one** is plugin-doctor rule material or its negative-test fixtures
(`rule-catalog.md`, `rule-provenance.md`, `_analyze_markdown.py`, `test_analyze_notation_staleness.py`,
`test_analyze_argument_naming_workflow_scope.py`). The underscore form is prescribed nowhere; it is
a documented anti-pattern with an edit-time detector.

Coverage caveat, stated rather than assumed: the inventory sweep does not walk `.claude/**` or
`.github/**`, so this is a clean negative over the inventoried tree, not over the whole checkout.

## The gap the pair exposes

There is an **edit-time** detector for the underscore notation form in documents
(`notation-staleness`), and **no call-time** counterpart. An agent that types the form at
invocation gets exit 1, a misattributed `bug` finding, and no rule fires.

## Rule

Give the notation rejection its own subtype (`invalid_notation`, `type: anti-pattern`) attributed to
the **calling** component rather than to the malformed one, and route it to the same
invented-invocation class as `invented_subcommand`. A defect class that already has a structural
detector on one surface should not be silently reclassified as a foreign script's internal bug on the
other.
