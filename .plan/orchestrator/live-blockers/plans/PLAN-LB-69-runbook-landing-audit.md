# PLAN-LB-69: The orchestrator audits every runbook-lane landing adversarially, and names each deliverable's skills when it stages a spec

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-69-runbook-landing-audit.md` and is queued as one row file,
> `queue/PLAN-LB-69.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-18 by operator instruction. **Emit after PLAN-LB-66 lands**, alongside PLAN-LB-67
> (disjoint surfaces: PLAN-LB-67 is the lane skill, this plan is the orchestrator). **Each
> deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do
> not merge them.**

## Objective

Since PLAN-LB-61, the orchestrator has audited every runbook-lane landing by hand, using the same
method each time:

- two independent read-only audit leaves, one for spec fidelity and one for process compliance;
- the runbook version in force at the run's last read;
- a list of report contradictions;
- orchestrator spot checks of the leaves' strongest claims;
- a process grade and a Model Watch row.

The method keeps finding what the runs do not report:

- fixes that are met on paper and inert in production (PLAN-LB-63 D2);
- high regressions hidden behind doc placeholders (PLAN-LB-65 D1);
- a fabricated operator decision (PLAN-LB-65);
- false statements in merge questions (PLAN-LB-63, PLAN-LB-65);
- edits in the main checkout (PLAN-LB-52, PLAN-LB-66).

PLAN-LB-66 D3 only names the evidence set, and it uses the session store "to corroborate a claim
the progress file states thinly". The audit itself, its depth and its harness dependence live
nowhere but in the orchestrator's habit.

The operator's rule: **runs on a harness without the plan-marshall lifecycle (OpenCode,
Antigravity) get the thorough audit.** This plan makes the method the `analyze` contract and
gives it a sanctioned, read-only session-store reader.

## Deliverables

1. **`analyze.md` carries the runbook-lane audit as a mandatory, harness-tiered step.**
   - For a runbook-lane landing, `analyze` dispatches two read-only `execution-context` leaves
     under the Dispatch Decision Rule. No leaf writes the ledger.
     - **Fidelity leaf:**
       - grade each Done-when met, partial or unmet, with `file:line`;
       - check end-to-end reachability on the documented production path;
       - check fail-first logs against commit and edit timestamps;
       - find weakened, removed or relaxed assertions;
       - find docs made false;
       - check files outside the Expected Surface;
       - grade regressions by severity, each with a concrete failure scenario.
     - **Process leaf:**
       - the lane-contract version in force at the run's last read of it; only rules in that
         version are debited;
       - every read of the lane contract with its time, set against each restart, resume and
         skill-list change notice: a run that read it once and never again after a restart is a
         process finding of its own (PLAN-LB-68 read it once in 37 hours while three lane changes
         landed);
       - models per phase, cost, compactions;
       - every shell call;
       - writes outside the worktree;
       - the review-trigger cadence against the quota policy;
       - the head each required reviewer reviewed;
       - each operator question's text and options checked against the facts at that time, with
         the selection;
       - main re-fetched and merged before enqueue;
       - cleanup;
       - every report claim the evidence contradicts.
   - The orchestrator **spot-checks** the strongest claim of each leaf, and every high or critical
     finding, before recording it. The landing names what was spot-checked.
   - **Depth by harness** (read from the landing's `harness` fact and the resolved `guard` state):
     - `opencode`, `antigravity`, or any run with `guard: none`: **full** — both leaves plus the
       session-store read;
     - `claude` on the plan-marshall lifecycle: the existing analysis, with the leaves optional.
   - The leaves' instructions include the session-store reader (D2), and **never** read
     permission or approval data.

   *Done when:* doc tests assert that `analyze.md`:
   - names both leaves and every checklist item above;
   - makes the spot-check step mandatory and recorded;
   - states the depth table with `opencode`, `antigravity` and `guard: none` mapped to full;
   - forbids ledger writes from the leaves and any permission-data read.

   Each fails against PLAN-LB-66's merged `analyze.md`.

2. **A read-only session-store reader returns a run's facts for each harness.**
   - A script verb takes a session id, or a lane sender and time window, and returns:
     - the root and sub-agent sessions;
     - model id and variant per message;
     - cost and compactions;
     - every shell command with its timestamp;
     - every edit or write path;
     - each read of the lane contract, with the content's length or hash so the version can be
       matched;
     - question-tool calls with options and selections;
     - operator free-text messages.
     The host verb is chosen at outline (platform-runtime or plan-orchestrator) and recorded.
   - **OpenCode:** the `opencode.db` session tables, opened `mode=ro`.
     **Claude:** the session JSONL.
     **Antigravity:** whatever store exists. If none is readable, the reader returns
     `store: unavailable` and never guesses.
   - It never opens, reads or returns permission or approval tables or columns. It never returns
     secrets: no message bodies beyond the tool arguments listed above, and no environment or
     credential text.
   - It has no write path.

   *Done when:* fixture tests show:
   - an OpenCode fixture DB yields the listed facts for a root session and its sub-agents;
   - a Claude JSONL fixture yields the same shape;
   - an unknown harness returns `store: unavailable`;
   - the reader opens the DB read-only;
   - a fixture `permission` table is never queried.

   All of these fail before the verb exists.

3. **The landing template and payload carry the audit's outputs.**
   - `templates/landing-analysis.md` gains these sections for a runbook-lane landing:
     - **Lane contract in force**: the version or hash at the last read, and the rules judged new;
     - **Report contradictions**: a numbered list, each item with its evidence, including a failing gate
     the run's own progress file records and the landing omits (PLAN-LB-76's landing listed `4a5e8f1ff`
     among the heads with no `test-compile` run while its progress file recorded one that failed), and
     any ordered claim the run assembled from a progress file that is not in time order (PLAN-LB-45's
     question list came out in the wrong order and missed an aborted call; the order is rebuilt from the
     transcript), the pushed-head list set against the build logs rather than against the progress file or the
     landing's table (PLAN-LB-77's landing called a red `test-compile` at `be7937fd6` "not run" and omitted the
     pushed head `125617b3d`; neither document recorded the red run), and any quoted timestamp in an operator
     question checked against the PR (PLAN-LB-77's merge question named review triggers at 15:04Z and 15:05Z
     that do not exist);
     - **Spot checks**: what the orchestrator verified itself;
     - **Process grade**: with credits and debits;
     - **Model Watch row**: one line, appended to the epic's table.
   - `landing-payload-spec.md` documents that the run's own `model`, `steps` and rule-check claims
     are leads that the audit verifies, and that a contradiction is recorded, never silently
     corrected.

   *Done when:* template and spec doc tests assert the five sections and the "leads, recorded
   contradictions" sentence. Each fails against PLAN-LB-66's merged template and spec.

4. **The orchestrator names each deliverable's domain skills and persona when it stages a spec.**
   Operator decision (2026-10-18): skill selection happens at the orchestrator, not inside the
   run. PLAN-LB-67 D4 makes the lane load what is named.
   - `templates/plan-spec.md` gives every deliverable a `Skills:` line (domain skills) and a
     `Persona:` line (implementer, module-tester, integration-tester, security-expert or
     documenter; code-reviewer is implied for review).
   - `decompose` and every staging path fill the lines with a script call, not by hand:
     - an `orchestrator` verb (for example `spec-skills --spec PATH`) maps each deliverable's
       Expected Surface paths to modules through `architecture which-module`;
     - it returns the domain skills from the project's configuration (`marshal.json`
       `skill_domains` and the architecture data; the source is chosen at outline and recorded);
     - it suggests a persona from the path kind (source, test, doc);
     - the orchestrator reviews the result and writes it into the spec.
   - An unmapped path is reported as `unmapped`, never guessed. The orchestrator then names
     skills explicitly or records `none`.
   - `next` refuses to emit a spec whose named skills or persona do not exist in the installed
     bundles. That catches names that went stale while the spec waited.
   - `cleanup` (corpus review) flags staged specs that are missing the lines.
   - **Done-when authoring rule (folded from `landings/PLAN-LB-72.md`).** A Done-when may say
     "fails at `{sha}`" only for behaviour that is new at that sha. A preservation clause ("still
     docs-only") or a coverage clause ("a flat fixture resolves X", where X already resolves) says
     "holds at `{sha}`", so a run is never asked to observe a failure that cannot exist. The rule
     lives in `templates/plan-spec.md` and in `workflow/decompose.md`, and `cleanup` flags a staged
     Done-when that carries a "fails at" clause beside the words "still", "keeps" or "unchanged".
     Two Done-whens of PLAN-LB-72 were unmeetable by construction, and its run reported them
     "not met as written".
   - **Second clause (folded from `landings/PLAN-LB-74.md`).** A Done-when is never labelled "holds at
     `{sha}`" while a claim it rests on is still a HYPOTHESIS in the same spec's Claim Labels. PLAN-LB-74's
     D3 said the owning verbs "still write those keys (holds at `a297ea762`)" while its Claim Labels
     listed "`loop-back close` is the only writer" as a HYPOTHESIS; the hypothesis was false and the
     Done-when could not hold. The clause lives beside the first in `templates/plan-spec.md` and
     `workflow/decompose.md`, and `cleanup` flags a staged Done-when labelled "holds at" whose
     bullet names a symbol that a HYPOTHESIS claim in the same spec also names.

   *Done when:*
   - template and workflow doc tests assert the two lines and the script-filled staging step;
   - template and workflow doc tests assert the "fails at" / "holds at" rule and its second clause, and
     a `cleanup` fixture test flags a Done-when that says "fails at … still …" and one that says "holds
     at" over a HYPOTHESIS-labelled claim;
   - `spec-skills` fixture tests show a pyproject spec yields this repository's Python domain
     skills, a Maven spec touching a Java module yields the Java domain skills, and an unmapped
     path yields `unmapped`;
   - a `next` test refuses a fixture spec naming a nonexistent skill.

   Each fails before the change.

5. **`next` refuses to emit a spec that is not what main carries.** (Folded from `landings/PLAN-LB-59.md`.)
   A runbook run reads the main-checkout copy of its spec. PLAN-LB-59 started on a copy without the
   `Skills:`/`Persona:` lines that existed in the ledger worktree and reached main only with a ledger land
   mid-run; nobody re-read the spec afterwards.
   - `orchestrate.md` Step 5 (`next`) checks, before emitting a runbook-lane command, whether the staged
     spec in the store checkout differs from the copy at `origin/{base_branch}`, and when it does states
     that a `land` is owed first; it does not emit the command for that plan until the operator has
     landed or declined. A spec absent from the base branch is the same case (the runbook lane already
     asks the operator about it at run start).
   - The check is a script call, not a prose rule, and reports `unmeasured` when the base branch cannot
     be read, never a clean pass.

   *Done when:* fixture tests show:
   - a staged spec identical to the base-branch copy emits;
   - a spec edited since the last land does not emit and names the land;
   - a base ref that cannot be read reports `unmeasured` and does not emit.

   Each fails before the change.

Split guard: five deliverables.

## Claim Labels

- OBSERVED: PLAN-LB-66's `analyze.md` addition names the progress file, `guard.log`, the PR and the
  "harness session store, READ ONLY … to corroborate a claim the progress file states thinly"
  (PLAN-LB-66 worktree diff, before merge).
- OBSERVED: the method in use: `landings/PLAN-LB-61.md`, `-62`, `-54`, `-64`, `-63`, `-65`. Each has
  two leaves, a contradictions list, spot checks and a grade.
- OBSERVED: `opencode.db` tables `session_v2` and `session_message(id, session_id, type, seq,
  time_created, time_updated, data)`, with model, variant, cost and tool calls in `data` JSON
  (orchestrator reads, `mode=ro`).
- HYPOTHESIS: a Claude session JSONL carries model, tool calls and timestamps per line in a stable
  shape (verify-at-outline).
- HYPOTHESIS: Antigravity keeps a readable local session store (verify-at-outline; `unavailable` is
  an acceptable answer).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`, Dispatch Decision Rule cross-reference (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/` or `plan-orchestrator/scripts/`, the session-store reader, with SKILL.md canonical invocations (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md`, `workflow/decompose.md`, `workflow/orchestrate.md` (`next`), `workflow/cleanup.md` (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` and `SKILL.md`, the `spec-skills` verb and the `next` existence check (D4)
- OBSERVED: `test/plan-marshall/plan-orchestrator/` and the reader's test module (D1, D2, D3, D4)

## Dependencies and Sequencing

- Depends on: **PLAN-LB-66** (running), which ships the runbook-lane rows, the sender matching and
  the evidence-set paragraph this plan extends.
- Overlaps: none with PLAN-LB-67 (the lane skill and resolve verb). If D2 is hosted in
  platform-runtime, it shares that directory with PLAN-LB-68, but not a file. The emit gate
  decides.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-69-runbook-landing-audit.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
