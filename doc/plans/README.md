# doc/plans

Git-tracked plans executed by the **standalone plan lane** — the working mode that runs *outside*
the `/plan-marshall` and `/marshall-orchestrator` command lifecycle.

This tree exists because `.plan/` is git-ignored: the plan-marshall lifecycle's state lives only on
the machine that created it, so a cloud session at [claude.ai/code](https://claude.ai/code) clones
the repository and gets none of it. Everything a plan in this tree needs — the plan, the rules, and
the run report — is in git.

## The rules

**The complete working contract is the `cloud-plan-lane` skill.** It is the first thing every run
loads, before reading the plan:

```text
Skill: cloud-plan-lane
```

It covers: which skills to load, the plan directory lifecycle, the conditional Python build gate,
the pre-PR verification sub-agent, the branch/PR/review-comment cycle, the merge gate, the persisted
run report, and the closing self-check against the contract.

The skill lives at `.claude/skills/cloud-plan-lane/SKILL.md`. It is a project skill, so it is part of
the clone and loads in cloud sessions without any further configuration. `CLAUDE.md` § "Standalone
Plan Lane" records which of its hard rules the lane supersedes.

## Layout

One directory per orchestrator epic; one directory per plan inside it.

```text
doc/plans/
├── README.md                        # this file
├── truthful-signals/
│   └── {plan-name}/
│       ├── plan.md                  # the plan
│       └── report-NN.md             # one run report per run
├── review-apparatus/
└── code-intelligence-substrate/
```

A new plan starts as a single file — `doc/plans/{epic}/{plan-name}.md`. Step 2 of the contract moves
it into its own directory as `plan.md`.

## Relationship to the orchestrator epics

The three epic directories mirror the orchestrator epics whose ledgers live under
`.plan/local/orchestrator/`. Those ledgers stay machine-local and authoritative for queue state; this
tree carries only the plans handed off for standalone execution, plus their reports. A plan executed
here reports back through its PR, exactly as a plan-marshall plan does.
