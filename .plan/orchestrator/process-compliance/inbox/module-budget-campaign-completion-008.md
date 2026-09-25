envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-25T13:57:00Z
revision=1

# Process-rule issue: the opencode target drops `workflow/`, so the plan-marshall skill's own Action Routing table is unsatisfiable on that target

Reporter: plan `module-budget-campaign-completion`, `/plan-marshall action=finalize` entry.

## Observation

`plan-marshall:plan-marshall` SKILL.md § "Action Routing" routes every action to a workflow
document by relative path:

| Action | Workflow Document |
|--------|-------------------|
| `finalize` | `Read workflow/execution.md` |
| `outline` | `Read workflow/planning-outline.md` |
| `init` / `lessons` / `list` | `Read workflow/planning.md` |

The installed opencode skill copy has no such file:

```
$ ls ~/.config/opencode/skills/plan-marshall-plan-marshall
SKILL.md  references  scripts  standards
```

`workflow/execution.md` is absent, so the documented `Read` fails and the run cannot follow
the routing table. This run had to read the tree source
(`marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md`) instead.

## Root cause, verified

`marketplace/targets/opencode/emitter.py:76`:

```python
VERBATIM_SKILL_SUBDIRS = ('standards', 'references', 'templates', 'scripts')
```

`workflow/` is not in the tuple, so it is not emitted. The generated tree confirms the
asymmetry is one-sided — the claude target carries it:

```
$ ls target/claude/plan-marshall/skills/plan-marshall/
SKILL.md  references  scripts  standards  workflow
$ ls target/opencode/skill/plan-marshall-plan-marshall/
SKILL.md  references  scripts  standards
```

So the SKILL.md body is emitted **verbatim, including its workflow-routing table**, while the
document that table routes to is silently dropped. The instruction is shipped; its target is
not. On the opencode target the routing step is a dead end that reads as a missing file rather
than as a target-emission gap.

## Siblings in the same family (close in one change)

Any other skill whose SKILL.md routes by relative path into a subdirectory outside
`(standards, references, templates, scripts)` is in the same class. The two confirmed
members in this bundle: `plan-marshall:plan-marshall` (`workflow/`, 8 documents) and
`plan-marshall:phase-5-execute` (`workflow/`, plus its step dispatch templates name
`phase-6-finalize/workflow/*.md` targets). A sweep for `Read workflow/` and
`workflow/{name}.md` across `marketplace/bundles/*/skills/*/SKILL.md` should establish
whether the family is larger than these two before the fix is scoped.

## Consequence if unfixed

Every orchestrator action on the opencode target degrades from "follow the routing table" to
"guess where the workflow lives", which is exactly the improvisation the
`Skill workflow: No improvisation` hard rule forbids — the rule is being violated by the
skill's own installation, not by the agent.

## Evidence

- `ls ~/.config/opencode/skills/plan-marshall-plan-marshall` (above).
- `marketplace/targets/opencode/emitter.py:76`.
- `target/claude/plan-marshall/skills/plan-marshall/` vs
  `target/opencode/skill/plan-marshall-plan-marshall/` (above).
- Related, still open and NOT closed by this finding: the opencode skill cache's flat
  layout also shadows the marketplace source for shared-script imports, which killed every
  `manage-config` verb in this plan's earlier phases (finding
  `module-budget-campaign-completion-005`).
