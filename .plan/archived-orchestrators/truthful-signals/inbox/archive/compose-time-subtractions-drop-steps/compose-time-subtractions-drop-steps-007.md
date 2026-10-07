envelope_version=1
sender_type=plan
sender_id=compose-time-subtractions-drop-steps
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T11:36:21Z

## Proposed lesson metadata

- `component`: `plan-marshall:workflow-integration-sonar`
- `category`: `bug`
- `title`: sonar-roundtrip.md points at a sonar_project_key config surface that does not exist

## Observation

`sonar-roundtrip.md` instructs the agent to resolve `sonar_project_key` "from the
Sonar provider configuration". No script verb and no config surface actually
exposes that value. `manage-providers` does not surface it and no `manage-config`
key carries it.

The sonar step in this run could only proceed by **deriving** the key from the
org-repo naming convention (`{org}_{repo}`). That derivation is undocumented,
convention-dependent, and silently wrong for any project whose Sonar key does not
follow it.

## Why this is a defect, not a doc nit

This is the **doc-contract-divergence** archetype: a workflow doc names a
resolution source that has no implementation behind it, so every agent that
follows the doc improvises. Improvisation at a resolution seam is the worst
place for it — the improvised value is plausible, produces no error, and silently
targets the wrong project when the convention does not hold.

The doc reads as authoritative ("from the Sonar provider configuration"), which
is precisely what makes it worse than saying nothing: it suppresses the agent's
instinct to ask.

## Owed work

Pick one and make the doc match:

- **Implement the surface** — expose `sonar_project_key` through the provider
  config and have the doc name the exact verb, or
- **Document the derivation** — state the `{org}_{repo}` convention explicitly as
  the resolution rule, with the failure mode named for projects that deviate.

Either way, the doc must name a resolution path an agent can execute without
inventing one.
