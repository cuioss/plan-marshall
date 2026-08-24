# doc/plans

Git-tracked plans executed by the **standalone plan lane** — the working mode that runs *outside*
the `/plan-marshall` and `/plan-orchestrator` command lifecycle.

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

**Authoring a new plan has its own skill.** `cloud-plan-lane` governs *running* a plan; an
orchestrator *authoring* one loads
[`author-cloud-plan`](../../.claude/skills/author-cloud-plan/SKILL.md) instead — the authoring
judgement for a plan that must survive a runtime with no operator and no view of `.plan/`. It is
loaded locally at authoring time, not by the run; [`cloud-bridge.md`](cloud-bridge.md) § Path 1 is
where an author picks it up.

## Layout

One directory per epic — ledger-backed or standalone; one directory per plan inside it.

```text
doc/plans/
├── README.md                        # this file
├── cloud-bridge.md                  # create / sync / collect rule (ledger-backed epics),
│                                    # plus the standalone-epic carve-out
├── _template/
│   └── plan.md                      # authoring template for a new plan
├── truthful-signals/
│   ├── 010-{plan-name}.md           # authored, not yet run
│   └── 020-{plan-name}/             # a run has started on it
│       ├── plan.md                  # the plan
│       └── report-NN.md             # one run report per run
└── code-intelligence-substrate/
```

A new plan starts as a copy of [`_template/plan.md`](_template/plan.md) at
`doc/plans/{epic}/{NNN}-{plan-name}.md`. Step 3 of the contract moves it into its own directory as
`plan.md`, keeping the prefix on the directory. `_template/` is not an epic — the underscore marks it
as tooling.

The `{NNN}-` prefix is a **priority order**, so a listing of an epic directory is also the order the
operator hands plans over. It is numbered per epic starting at `010` and assigned sparsely in tens,
and it is fixed once a plan is handed to a cloud session. Strip the prefix to recover the
orchestrator plan's slug. [`cloud-bridge.md`](cloud-bridge.md) § "Path 1 — Create" holds the full
rule, including why plans authored before the scheme keep no prefix.

**Every plan opens with a mandatory first-instruction block** that loads the `cloud-plan-lane` skill
before anything else is read. It is part of the plan, not part of the template, and it survives into
every copy — a plan without it can be picked up by a session that never loads the contract, which
disables every gate the contract defines. The skill checks for the block at Step 3 and restores it
if missing, and checks again at Step 9.

Beyond that, the template carries the sections the lane's verification depends on: deliverables with
an explicit *done when* condition, an out-of-scope boundary, the expected surface, and
OBSERVED/HYPOTHESIS claim labels with a named confirm-refute artifact for every hypothesis. A plan
handed over without them gets built against a thinner brief than its author imagined.

## Relationship to the orchestrator epics

`truthful-signals`, `review-apparatus` and `code-intelligence-substrate` mirror the orchestrator
epics whose ledgers live under `.plan/local/orchestrator/`. Those ledgers stay machine-local and
authoritative for queue state; this tree carries only the plans handed off for standalone execution,
plus their reports.

An epic's directory therefore exists only while it has plans handed off. Once a wave is collected back
into its ledger the directory is removed, and it reappears on the next hand-off — an absent directory
means nothing is currently exported for that epic, never that the epic is closed.

A **standalone epic** has no orchestrator-ledger counterpart, because it was opened directly from its
own source material rather than derived from a staged orchestrator plan. Such an epic carries its
scoping brief in git alongside its plans — the census the plans were scoped from, the house style they
converge on, and the dependency graph saying which of them may run at the same time — so it needs no
ledger to be executable.

A standalone epic that outgrows the lane is **ingested**: its plans, reports and brief are absorbed
into `.plan/local/orchestrator/{slug}/` and removed from this tree, and it becomes ledger-backed from
that point on. The ingested tree is the audit record; nothing is lost, and the epic gains the queue,
the surface-disjointness check and the landing analysis the standalone lane does not have. An epic
reaches that point when its plan count and collision graph stop fitting in prose — which is what a
hand-maintained partition and collision matrix drifting across successive verification rounds looks
like from the outside.

For a ledger-backed epic the two halves cannot see each other — the orchestrator tree is git-ignored,
and a cloud session's working state dies with its VM — so **git is the only shared medium**.
[`cloud-bridge.md`](cloud-bridge.md) is the rule for authoring a plan here, running it, and
collecting it back into the orchestrator. Read it before doing any of the three. For a **standalone**
epic there is no orchestrator to collect back into, so only the first two apply; `cloud-bridge.md`
§ "standalone epic" states which of its paths are inert and which still bind.

**There is no status file.** The tree itself is the state: a flat `{NNN}-{plan-name}.md` is authored
and waiting, a `{NNN}-{plan-name}/` directory means a run has started, a `report-NN.md` inside it
names the PR, and a plan that has been collected is simply gone. In a standalone epic nothing collects,
so a landed plan's directory stays where it is, its report the durable record. Nothing has to be kept
in sync,
because nothing is stored twice.
