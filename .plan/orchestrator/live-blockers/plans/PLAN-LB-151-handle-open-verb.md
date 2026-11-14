# PLAN-LB-151: A `handle-open` verb walks every open defect, watch and question of an epic, decides what it is confident about and puts the rest to the operator one by one in plain text

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-151-handle-open-verb.md` and is queued as one row file, `queue/PLAN-LB-151.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-14 (the operator asked for a plan that generalises the standing instruction they pass by hand:
> go through every open issue, question and watch in the ledger, analyse each thoroughly, recommend a solution, decide when more than 90
> percent confident, and put the others one by one in plain text with numbered proposals, a recommendation, its confidence and why; the
> threshold configurable; a new sub-command `handle-open` with a sub-document like the other verbs; land and emit). Grounded by the
> orchestrator against `main` at `72ef749af` by reading `workflow/cleanup.md`, `templates/epic.md`, `manage-config/scripts/_cmd_orchestrator.py`,
> `test/plan-marshall/plan-orchestrator/test_cleanup_contract.py` (head), the persona skill, the standard (lines 1-317) and the resume anchor,
> and by a content sweep of the inventory for the `auto_emit` knob, the verb enumerations and `AskUserQuestion`. The standard's lines 318-555
> (the Cleanup Contract and the lessons-handling contract), `doc/concepts/orchestration.adoc`, `_config_defaults.py` and the four
> manage-config tests were NOT read; claims about them are HYPOTHESIS entries. Every Done-when below fails at `72ef749af` (the verb does not
> exist there) unless it says "holds at". No Sonar. No token or measurement work. This is operator-requested tooling, not a blocker.

## Objective

The operator has been steering the orchestrator with one standing instruction: go through every open issue, question and watch in the
ledger, analyse each thoroughly, recommend a solution, decide when more than 90 percent confident, and put the rest to the operator one at a
time in plain text, each with numbered proposals, a recommendation, a confidence and the reason. This plan makes that a verb of its own,
`handle-open`, with a binding contract in the standard, a workflow document in the shape of the other verbs, and a configurable confidence
threshold. The threshold is one scalar knob of the orchestrator block, `decision_confidence_threshold`, readable and settable through
`manage-config orchestrator`, and the verb takes an optional per-run override.

## Deliverables

1. **The standard carries the binding Handle-Open Contract, the persona carries its one exception, and the verb enumerations stay in agreement.**
   - Skills: pm-documents:ref-documentation, pm-plugin-development:plugin-architecture
   - Persona: documenter
   - `persona-plan-orchestrator/standards/orchestration-model.md` gains a `## Handle-Open Contract` section, placed beside the Cleanup Contract
     and in the same register (the workflow xrefs it and restates nothing). It states, once:
     - **Subject.** The inventory is a closed set of four sources and nothing else: the entries of `epic.md` `## Open Defects`, the entries of
       `epic.md` `## Watches`, the open operator questions (`OPERATOR DECISIONS` in the resume anchor not marked settled, and any `## Decisions`
       entry that ends awaiting the operator), and, only through the entries that carry them, the unowned residue of landings. Each item has a
       kind from a closed set (`defect`, `watch`, `question`, `candidate`), a source pointer and a number for the run.
     - **Confidence.** An integer percent the ORCHESTRATOR assigns inline after re-reading every load-bearing claim of its own analysis at
       `file:line` in this run (or settling it through a recorded verdict). A claim carried from a leaf report, from the ledger's own prose or
       from a HYPOTHESIS and not re-read caps the item's confidence at the threshold, so it can never be decided without the operator. A leaf's
       number is a lead and is never copied.
     - **Threshold.** An item is decided by the orchestrator only when its confidence is STRICTLY GREATER than the threshold. The threshold is
       an integer 0 to 100; 100 means nothing is decided without the operator. The effective value is the per-run argument when given, else the
       knob, whose unset read carries the seeded default; the contract does not restate the default's value. A threshold that cannot be read, or
       a per-run argument that is not an integer 0 to 100, resolves to 100 for the run and the report says so: an unreadable setting never
       licenses a decision.
     - **Decision acts.** The orchestrator's own decisions are bounded: record the decision (decision log and the `## Decisions` narrative),
       mark the item in place as decided with a pointer, retire a watch or defect only on a positive account of what closed it (the commit, the
       PR or the named symbol that now carries the behaviour), and answer a factual question. It NEVER stages a plan, emits a command,
       transitions a queue row, edits the spec of a running row, relocates settled narrative (that stays `cleanup`'s, which needs its own
       positive account and operator confirmation), or lands. A decision whose consequence is a plan is recorded as decided with the follow-up
       named, and the staging stays an act the operator words.
     - **Presentation.** Items below the threshold are put to the operator in PLAIN TEXT, ONE ITEM PER TURN, each with numbered proposals, one
       marked recommended with its confidence and the reason, and a final "leave it open" proposal. The orchestrator waits for the answer before
       the next item and does not use the question tool for this verb. This is a bounded exception to the default of surfacing genuine forks
       through the question tool, and the contract states why: the operator asked for it, and a plain-text turn carries the analysis the tool's
       option cards cannot.
     - **Reporting.** Every count rides with the population it was computed over (per source, per kind), so a source holding nothing and a
       source that could not be read are different lines, and the report names every decided item with who decided it, at what confidence and
       against which threshold.
     - **Dispatch.** At most ONE read-only analysis envelope iterating over the items, on the existing `orchestrator.analyze` effort surface,
       returning a proposal the orchestrator adjudicates; the confidence, the decision, every write and every operator turn stay inline.
   - The standard's Terminal-Title enumeration ("All {count} verbs — {list} — carry the obligation") gains `handle-open`, and its count word
     is corrected to the length of the list.
   - `persona-plan-orchestrator/SKILL.md` identity attribute 9 names the one exception in a sentence and xrefs the contract.

   *Done when:* each of these fails at `72ef749af`: the standard has a section whose heading is `Handle-Open Contract` and the persona's
   attribute 9 names `handle-open`; the Terminal-Title sentence's list contains `handle-open` and its count word equals the list's length.
   These hold at `72ef749af`: `test/plan-marshall/plan-orchestrator/test_cleanup_contract.py` group (b) passes against the edited standard
   and no marketplace file other than the standard defines the confidence-cap rule.

2. **The `handle-open` workflow document and its routing.**
   - Skills: pm-documents:ref-documentation, pm-plugin-development:plugin-architecture
   - Persona: documenter
   - `plan-orchestrator/workflow/handle-open.md`, in the shape of `workflow/cleanup.md`: an intro that xrefs the contract and restates none of it,
     the exit-code convention section, `Inputs` (`slug` required; `threshold` optional, an integer 0 to 100 overriding the knob for this run),
     `Dispatch`, the steps below, `Idempotence`, `Output`.
     1. Push the terminal title and resolve the epic tree, as every epic-scoped verb does.
     2. Resolve the effective threshold: the per-run argument, else `manage-config orchestrator get --field decision_confidence_threshold`; the
        source of the value (argument, knob, unset default) goes into the report; the fail-closed reading of the contract applies.
     3. Inventory the four sources by direct reads of the ledger documents (the carve-out allows reads) and number the items. Publish each
        source's population; a source that cannot be read is named and never counted as empty.
     4. Analyse every item (the one dispatchable read-only envelope, or inline for a small inventory) and return, per item, a recommendation,
        the alternatives, the evidence and the claims NOT checked.
     5. Verify inline: re-read each load-bearing point at `file:line`, run the existing check before saying a fix is possible, and assign the
        confidence under the contract's cap.
     6. Decide every item above the threshold: log it, write the `## Decisions` entry, mark the item in place. An item whose decision changes
        another item's analysis makes that item re-analysed before it is decided.
     7. Present the remaining items one per turn in the contract's plain-text shape, most consequential first; record each answer the same way
        as step 6 before the next item; an operator answer of "stop" or "skip" leaves the item open and says so.
     8. Log, rewrite the resume anchor and regenerate the view, and commit the ledger paths as `git -C {store_checkout}` (never a land). The anchor
        write replaces the whole value, so the step reads the current anchor first and checks the written value with a word-diff against the
        committed one before the view is regenerated.
     9. Report.
   - The routing table of `plan-orchestrator/SKILL.md` gains the row `handle-open` to `workflow/handle-open.md`, the Usage block gains
     `/plan-orchestrator handle-open slug={slug} [threshold=N]`, and no other part of that file restates the contract. The sub-command set of
     `orchestrator.py` is unchanged: the verb is prose, as `cleanup` is.
   - `doc/concepts/orchestration.adoc`, only if it carries a verb enumeration, is brought into agreement.

   *Done when:* each of these fails at `72ef749af`: `workflow/handle-open.md` exists; the routing table references it and every document the
   table references exists, in both directions; the Usage block lists `handle-open`; the document's fenced blocks contain no `AskUserQuestion`
   block; the document names the knob and states no default value for it; it carries the eight prohibitions of the contract's decision-acts
   bullet by name. This holds at `72ef749af`: the router-closure, verb-enumeration and canonical-invocation groups of
   `test_cleanup_contract.py` pass.

3. **The threshold is a validated, seeded, documented orchestrator knob.**
   - Skills: pm-dev-python:python-core, plan-marshall:ref-code-quality
   - Persona: implementer
   - `manage-config orchestrator get|set --field decision_confidence_threshold`: the field joins the known scalar fields
     (`ORCHESTRATOR_SCALAR_FIELDS` in `_cmd_orchestrator.py`), so every unknown field still fails closed. `set` coerces to an integer and
     accepts 0 to 100 inclusive; a bool, a non-integer string, a float, a negative number and a number over 100 are refused with a message naming
     the range and nothing is written. `get` on an unset field returns the seeded default with `set: false`, as `auto_emit` does.
   - The seeded default lives in ONE place, `DEFAULT_ORCHESTRATOR` in `_config_defaults.py`, and is 90 (the operator's standing figure). No
     other file restates the number except the data-model table that documents defaults.
   - Documentation: the knob is added where `auto_emit` is documented — `manage-config/SKILL.md`, `manage-config/standards/api-reference.md`,
     `manage-config/standards/data-model.md`, `extension-api/standards/marshal-json-reference.md`, `doc/user/configuration.adoc` and the help
     text of `manage-config.py` — each in the existing register, with the strictly-greater semantics and the 100 setting stated once and
     cross-referenced elsewhere.
   - Existing projects: the seeded default changes the config seed, so the PR states that a `sync-defaults` reconcile (the steward's
     `upgrade`) is how an existing `marshal.json` gains the field, and the sync-defaults and seed tests cover it.

   *Done when:* each of these fails at `72ef749af`: `orchestrator set --field decision_confidence_threshold --value 0` and `--value 100` persist
   and read back; `--value 101`, `-1`, `true`, `90.5` and `ninety` are refused with nothing written; `orchestrator get` on a fresh seed returns
   the seeded default with `set: false`; `orchestrator get --field decision_confidence_thresholds` (a typo) is refused as an unknown field;
   `sync-defaults` backfills the field into a `marshal.json` that lacks it without touching an operator's set value. This holds at
   `72ef749af`: every existing `auto_emit`, `parallelization_scope` and `use_worktree` case in the four manage-config test files passes unchanged.

4. **The verb's contract is pinned by population-derived tests with matched controls.**
   - Skills: pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester
   - `test/plan-marshall/plan-orchestrator/test_handle_open_contract.py`, in the form of `test_cleanup_contract.py` (the governed sets are
     enumerated at test time, every count carries its population), pins: the workflow document's step order; that it reads the threshold
     through the knob and carries the fail-closed sentence; that it has no `AskUserQuestion` block and names the plain-text, one-per-turn
     presentation; that it names every prohibition of the contract's decision-acts bullet; that the report carries the per-source population
     lines; that the confidence-cap rule is defined in the standard once and xref'd by the workflow; and that the dispatch names the
     `orchestrator.analyze` surface and the `--workflow` document the dispatch-pin test expects.
   - Each pin has a matched control that plants the violation in a temporary tree (an `AskUserQuestion` block, a hard-coded default, a dropped
     prohibition, a second definition of the cap, a missing population line) and shows the detector fires. A detector with no control fails the
     plan.
   - The knob cases of deliverable 3 are added to `test/plan-marshall/manage-config/test_orchestrator_scope.py`,
     `test_orchestrator_seed.py`, `test_config_defaults.py` and `test_sync_defaults.py` in their existing style, using the `PLAN_MARSHALL_HOME`
     fixture so no test reads or writes a real `marshal.json`.
   - `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` is brought into agreement if it enumerates the dispatching
     verb documents and the new document dispatches.

   *Done when:* the new module fails at `72ef749af` (it does not exist) and passes after the plan, and each matched control fails when its
   planted violation is removed. These hold at `72ef749af`: `test_cleanup_contract.py`, `test_orchestrator_dispatch_workflow_pin.py` (unless
   edited under the last bullet) and the existing manage-config tests pass unchanged.

Split guard: four deliverables, one theme. D1 is the contract, D2 the document, D3 the knob and D4 the tests. D3 is a separate surface and could
ship alone; the plan stays whole because D2 reads the knob D3 creates and D4 pins both, and one landing keeps the verb and its knob from existing
apart. If the lane finds the knob's seed change needs more than the listed files, it splits D3 out and the PR records it.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- One definition per concept: the contract lives in the standard, the workflow xrefs it, and the default lives in `DEFAULT_ORCHESTRATOR`. The
  workflow states no threshold value and no confidence rule of its own.
- Fail closed: an unreadable threshold, an out-of-range argument and an unread source never produce a decision or a count of zero; they are
  named in the report.
- The verb decides nothing about work: no plan is staged, no command emitted, no queue row transitioned, no running spec edited, nothing
  relocated and nothing landed by it. These are the operator's words or other verbs' acts.
- ⛔ The lane NEVER runs `handle-open` against the real ledger, and never edits a real `marshal.json` or the machine-local run configuration:
  the verb writes the epic's ledger. Verification is by tests with temporary trees and the `PLAN_MARSHALL_HOME` fixture.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour. The documentation standards of
  `CLAUDE.md` apply: no duplication, cross-reference instead; AsciiDoc where the file is AsciiDoc.
- Tests state their purpose, are population-derived, and are shown red where a Done-when says so.
- The PR states: whether an executor regeneration is owed (none if no verb or flag is added to a script's argparse surface; the `--field` value
  is checked against the whitelist, not an argparse choice, which the lane verifies), that a harness sync is owed (bundle files are edited), and
  that a `sync-defaults` reconcile is how existing projects gain the knob.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: the router, the Usage block, the standard's Terminal-Title enumeration (its stated count word and its list) and `doc/concepts/orchestration.adoc` are held in agreement with the verb set derived from the routing table, and the routing table's referenced documents are held equal to the `workflow/*.md` files in both directions — read at `test/plan-marshall/plan-orchestrator/test_cleanup_contract.py` (module docstring, groups (a) and (b), and the regexes at L115-118)
- OBSERVED: the Terminal-Title sentence the test parses has the form "All {count} verbs — {list} — carry the obligation" and currently says twelve — read at `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` § Terminal-Title Repaint Contract (L187) and `test_cleanup_contract.py` L117; `architecture search --content --pattern "twelve verbs"` found it in that one file only
- OBSERVED: `cleanup` is a prose workflow with no script sub-verb of its own; it dispatches only the verdict half of one step on the `orchestrator.analyze` surface (reusing `analyze.md` Step 2's `corroborations[N]{claim,verdict,evidence}` return), keeps every write inline, and requires operator confirmation for narrative relocation — read at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md` § Dispatch, Step 3, Step 8
- OBSERVED: the epic template defines `## Open Defects` ("when a defect is folded into a plan spec, move it out of this list and note the owning PLAN-NN") and `## Watches` ("retire a watch when it resolves or graduates into a defect/plan"); `## Decisions` is "narrative — no script writes it" beside `logs/decision.log` — read at `marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/epic.md`
- OBSERVED: the live epic orders `## Decisions` newest first (the resume anchor says "top entries newest first") while the template says "newest last", so the verb follows the order the section already uses — read at `.plan/orchestrator/live-blockers/resume_anchor.md` and `templates/epic.md` L34
- OBSERVED: the orchestrator scalar knobs are a whitelist `ORCHESTRATOR_SCALAR_FIELDS = ('parallelization_scope', 'auto_emit', 'use_worktree')`, every get and set is rejected against it fail-closed, `get` falls back to `DEFAULT_ORCHESTRATOR.get(field)` with `set: false` when unset, and `parallelization_scope` is validated as an int >= 1 with a bool rejected explicitly — read at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_orchestrator.py` L70, L77-87, L229-259, L284-301
- OBSERVED: the `auto_emit` knob is declared or documented in 16 files — `_cmd_orchestrator.py`, `_config_defaults.py`, `manage-config.py`, `manage-config/SKILL.md`, `standards/api-reference.md`, `standards/data-model.md`, `extension-api/standards/marshal-json-reference.md`, `persona-plan-orchestrator/standards/orchestration-model.md`, `plan-marshall/standards/effort-roles.md`, `plan-orchestrator/workflow/analyze.md`, `workflow/orchestrate.md`, `doc/user/configuration.adoc` and four manage-config tests — `architecture search --content --pattern auto_emit` (inventory only)
- OBSERVED: persona identity attribute 9 says genuine forks are surfaced "via `AskUserQuestion`, with the outcome logged as an interaction" — read at `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/SKILL.md` § Identity Attributes
- OBSERVED: the operator's standing rule of 2026-11-12 is "decide directly above 90 percent confidence, guide the operator one by one in plain chat for the rest", and the working rules say a leaf report is a lead whose checked points are re-read at `file:line` — read at `.plan/orchestrator/live-blockers/resume_anchor.md` (OPERATOR RULE 2026-11-12 (decisions); WORKING RULES LEARNED)
- OBSERVED: the verb is epic-scoped and so carries the terminal-title obligation, and the dispatch rule allows ONE envelope that iterates internally, read-only, with the write staying inline — read at `orchestration-model.md` § Terminal-Title Repaint Contract and § Dispatch Decision Rule (L302-317)
- HYPOTHESIS: `doc/concepts/orchestration.adoc` either defers to the router or carries a verb enumeration the contract test requires to agree — confirm/refute at that file (not read; verify-at-outline, D2)
- HYPOTHESIS: the dispatch-pin test enumerates the verb documents that carry a `--workflow` dispatch from the live tree, so the new document is either picked up or must be added — confirm/refute at `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` (not read; verify-at-outline, D4)
- HYPOTHESIS: adding a seeded default to `DEFAULT_ORCHESTRATOR` changes the config seed fingerprint, and `test_config_defaults.py`, `test_sync_defaults.py` and `test_orchestrator_seed.py` pin the seeded block as a literal — confirm/refute at `_config_defaults.py` § `DEFAULT_ORCHESTRATOR` and those tests (not read; verify-at-outline, D3)
- HYPOTHESIS: `manage-config orchestrator --field` is validated by the whitelist in the handler and is not an argparse `choices` set, so no executor regeneration is owed — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` § orchestrator subparser (not read; verify-at-outline, D3)
- HYPOTHESIS: `plan-marshall/standards/effort-roles.md` needs no change because the verb reuses `orchestrator.analyze` — confirm/refute at that file's orchestrator role group (one mention found by the sweep; not read; verify-at-outline, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/README.md` does not enumerate the orchestrator verbs — confirm/refute at that file (not read; verify-at-outline, D2)
- Verify-first clause: before scoping D1, read the standard's lines 318-555 (the Cleanup Contract and the lessons-handling contract) so the new section matches their register and duplicates none of them. Before scoping D3, read `_config_defaults.py` and the three seed tests and state which literals pin the orchestrator block. Before scoping D4, read the dispatch-pin test.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — new `## Handle-Open Contract`, the Terminal-Title enumeration (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/SKILL.md` — identity attribute 9 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/handle-open.md` — new file (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — Usage block and Verb Routing table (D2)
- HYPOTHESIS: `doc/concepts/orchestration.adoc` — only if it carries a verb enumeration (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_orchestrator.py` — whitelist, validation, docstring (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — `DEFAULT_ORCHESTRATOR` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` — help text (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — knob documentation (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/api-reference.md` — knob documentation (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` — knob and default (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md` — knob documentation (D3)
- OBSERVED: `doc/user/configuration.adoc` — knob documentation (D3)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_handle_open_contract.py` — new file (D4)
- OBSERVED: `test/plan-marshall/manage-config/test_orchestrator_scope.py` — knob cases (D3, D4)
- OBSERVED: `test/plan-marshall/manage-config/test_orchestrator_seed.py` — seeded default (D3, D4)
- OBSERVED: `test/plan-marshall/manage-config/test_config_defaults.py` — seeded default (D3, D4)
- OBSERVED: `test/plan-marshall/manage-config/test_sync_defaults.py` — backfill (D3, D4)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py` — only if it enumerates the dispatching verb documents (D4; verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. The orchestrator surfaces it extends are on `main`.
- Overlaps with: none expected. PLAN-LB-136 declares the Antigravity runtime and manifest surface, PLAN-LB-148 the runbook lane and review-gate surface and PLAN-LB-150 the `apply-changes` entry points, its parity test and three documents; none of them declares a file of this plan. The cross-check names any exact file.
- Adjacent to: `workflow/cleanup.md` and `workflow/analyze.md`, which stay unedited (the verb reuses their dispatch shape by reference); the `orchestrator.py` sub-command set and its `## Canonical invocations`, which do not change; `manage-config`'s effort resolver, which is not touched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-151-handle-open-verb.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
