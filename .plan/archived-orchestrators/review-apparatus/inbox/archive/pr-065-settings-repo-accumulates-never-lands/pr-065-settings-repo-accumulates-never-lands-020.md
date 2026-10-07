envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:54Z

component=plan-marshall:manage-architecture
category=improvement
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate finding edd1fa (2-refine, accepted); work-log WARNING 54e3c2 (2026-09-14T11:10:50Z), 9b511f (16:53:07Z)

# A footprint path under `.github/**` resolves to no module, and that silently widens every scoped gate to whole-tree

`architecture which-module --path .github/workflows/pr-agent-packs-publish.yml`
returns `module: null` with attributors
`[documentation, plan-marshall, pm-plugin-development]`. `.github/**` sits
outside the crawled inventory by design, and the multi-attributor answer is what
every marketplace path returns, so the result carries no discrimination.

The consequence is not confined to the refine phase where it was first noticed.
`pre-push-quality-gate` warned twice in this run:

```text
Footprint paths resolved to no registered module: .github/workflows/...
- proceeding whole-tree; scoped coverage for these paths is not determinable.
```

and the execute-exit freshness gate refused a transition with
`build_scope_narrow`, citing `divergence_possible=true via unresolved path
.github/workflows/pr-agent-packs-publish.yml` and demanding one whole-tree
verify at orchestrator tier (`bash_timeout_seconds=2157`).

## The signal

One unresolvable footprint path escalates the run's build cost from module-scoped
to whole-tree, at orchestrator tier, and does so correctly — the gate is
fail-closed and that is right. But the escalation is driven by a path class the
inventory deliberately excludes, so it is structural rather than incidental: any
plan touching a workflow file pays it.

## Candidate knowledge / rule

This is durable project knowledge rather than a defect: a `.github/**` (or any
dotfile-tree) path in a plan's footprint means whole-tree verification, at
orchestrator tier, and a plan that touches CI config should be planned with that
cost assumed. Whether the inventory should attribute `.github/**` to a module
(making the coverage determinable) is a separate, larger question this note does
not settle.
