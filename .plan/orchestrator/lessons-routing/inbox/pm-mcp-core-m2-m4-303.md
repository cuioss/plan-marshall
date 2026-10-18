envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:36Z

# Candidate lesson: architecture search called with "--literal false"

Source: script-failure cluster plan-marshall:manage-architecture:architecture (1 occurrence, phase 2-refine, 2026-10-17T18:58:50Z)
Component (suggested): plan-marshall:manage-architecture (foreign bundle - route to plan-marshall lessons inbox)

## What happened

```
architecture --plan-id plan-69-unit-frontmatter-and-types search --content \
  --pattern startState|entryBindings|EntryBinding|UnitFrontmatter|frontmatter --literal false
```

exit 2: `error: unrecognized arguments: false`. `--literal` is a store_true flag;
the caller passed it a value. The retry without the value succeeded.

## Candidate rule

Boolean switches on `architecture search` take no value: omit `--literal` for
regex mode, pass bare `--literal` for literal mode. Possibly a doc gap in the
`client-api.md` search section if it shows the flag with a value.
