# PLAN-LR-08: A framework-owned lesson or finding is forwarded to the framework's `lessons-routing` inbox instead of being promoted into the project's store

epic: lessons-routing
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

An epic that orchestrates a project other than plan-marshall collects, at every landing, lessons and tooling observations whose subject is plan-marshall itself (components `plan-marshall:*` and the `pm-*` domain bundles). Today they stay in the project's lessons store, its inbox drain (`Promote`) and its Open Defects, and moving them to the framework repository takes an explicit operator instruction every time. This plan gives the destination a resolvable home and the routing an owner: a framework-owned `candidate-lesson` or `finding` is written to the framework home's `lessons-routing` inbox and archived at the source, and the tombstone of a forwarded lesson names where it went. Source: change request `libraries-initial-implementation-078` (operator of that epic, priority high; staged here on the operator's word during the 2026-11-24 drain).

⛔ **This is a shared marketplace skill.** Every project running `plan-orchestrator` gets this change. It touches the destination of a finding, which is this epic's Inbound Routing subject, and it supersedes none of the parked `PLAN-LR-02` / `PLAN-LR-03`; re-read both at outline and fold the overlap rather than re-deriving their ownership predicate and upstream route.

## Deliverables

Six deliverables, grouped from the request's eight points.

1. **Framework home and ownership predicate.** One resolvable setting naming the plan-marshall checkout that owns `lessons-routing` (a config key of the orchestrator tier, or a derivation from the installed plugin's source), validated on use: the path exists, `corpus epics` there lists `lessons-routing` in `active[]`, and its `status.json` phase is not `closed`. A closed or unreadable epic is never written to; the item is held and reported. One implementation of `framework-owned(component)`: true for `plan-marshall:*` and for every bundle of the installed marketplace, derived from the plugin inventory and not from a hard-coded list of `pm-*` names.
   - Skills: none
   - Persona: implementer
2. **`analyze` inbox drain: the `forwarded` disposition.** A new closed disposition `forwarded`, counted inside `messages_archived` so the closure equation holds, for a `candidate-lesson` or `finding` whose subject is framework-owned: write it into the framework home's `lessons-routing` inbox (kind kept), then archive the source message. `Promote` is not offered for it. A message that is partly the project's is split by the orchestrator: the project part stays, the tooling part is forwarded. A tooling gap found while analysing a landing (an `undecidable` read, an `unknown` landing fact, a figure that disagrees with the retrospective) is forwarded as a `finding` in the same pass.
   - Skills: none
   - Persona: implementer
3. **`lessons` verb: push framework-owned lessons.** The same predicate selects, in the local corpus, the framework-owned lessons; each is forwarded as one `candidate-lesson` message (body and recurrences included; header keys `component`, `category`, `title`, `source_lesson`, `source_repo`, `source_created`) and retired locally ONLY after the write returned success. A run that fails after the 40th write leaves the remaining lessons in place.
   - Skills: none
   - Persona: implementer
4. **`manage-lessons remove`: a relocation verdict.** A verdict `relocated` (or `moved`) whose required evidence is the destination, `{repo}:{epic}/inbox/{message}`, recorded in the tombstone, so a moved lesson is told apart from one superseded by another lesson.
   - Skills: none
   - Persona: implementer
5. **Idempotence and record.** A forwarded lesson is never written twice: the destination message carries `source_lesson` and `source_repo`, and the verb refuses (or returns the existing message) when the same pair is already present in the destination's `inbox/` or `inbox/archive/`. Every forward is one decision-log line and one row in a `lessons-moved.md` of the sending epic (lesson id, component, destination message); the sender id is the sending epic's slug and the sequence is the destination's allocation. The orchestrator never touches the framework repository's git state.
   - Skills: none
   - Persona: implementer
6. **Tests and doc sync.** Tests for the acceptance cases below, and the verb docs (`analyze.md` Step 3 and Step 5b, `lessons-handling.md`, `SKILL.md`, `inbox-envelope.md`) updated so the closed disposition set is stated once.
   - Skills: none
   - Persona: module-tester

Acceptance, from the request: a candidate lesson with component `pm-dev-java:junit-core` drained in a project epic ends in the framework home's inbox, archived at the source, with no `manage-lessons add` in the project store, while one with component `git-store` is promoted locally as before; with the framework epic closed nothing is written, the item is reported and the local copy stays; a second drain or sweep of the same lesson writes nothing; a sweep over a store holding 76 framework lessons forwards 76 messages and retires 76; the tombstone names the destination and `drained[]` accounts for `forwarded`.

## Standing Constraints

- `inbox write` resolves its destination through the store seam keyed on the CWD, so a write into another repository's inbox works today only when the verb runs from that repository. The framework-home write must name and validate the target explicitly instead of relying on the CWD; check the seam's contract at outline before choosing the mechanism.
- Nothing in this plan edits another repository's git state, and the lesson store of another repository is never mutated through the current repository's `manage-lessons` (a cross-repo removal happens only with `git -C {remote_repo}` after the local integration is persisted).
- Re-ground every claim in the request against HEAD before scoping: the four "mechanics" of the request (CWD-keyed `inbox write`, the missing "moved" verdict, the pull-only `remote_lessons_dir` pass, the four-member disposition set) are the sender's reading at plugin 0.1.2184.

## Claim Labels

- OBSERVED: `analyze.md` Step 5b lists exactly four dispositions (`promote`, `fold`, `stage`, `discard`) and none forwards — read at `plan-orchestrator/workflow/analyze.md` § Step 5b.
- HYPOTHESIS: `inbox write` resolves the destination through the CWD-keyed store seam, so a write to another repository's inbox needs a `cd` — confirm or refute at `plan-orchestrator/scripts/_orchestrator_inbox.py` § write and `tools-file-ops` § store seam (verify-at-outline).
- HYPOTHESIS: `manage-lessons remove` has no relocation verdict — confirm or refute at `manage-lessons/scripts/` § remove verdict set (verify-at-outline).
- HYPOTHESIS: the `lessons` verb's cross-repo pass is a pull only — confirm or refute at `plan-orchestrator/workflow/lessons-handling.md` § cross-repo pass (verify-at-outline).
- Verify-first clause: `PLAN-LR-02` and `PLAN-LR-03` are parked as superseded; settle at outline whether this plan absorbs their ownership predicate and upstream route or leaves them parked.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/lessons-handling.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-lessons/**` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/**` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-lessons/**` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-LR-02`, `PLAN-LR-03` (parked; same destination subject), `PLAN-LR-09` (same `analyze.md` and `orchestrator.py`; serialise, do not merge edits), and the `plan-orchestrator` surface other epics declare (`corpus cross-check` at emit time).
- Adjacent to: `PLAN-LR-07` (shipped; the `lessons` verb's fixed epic target).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/lessons-routing/plans/PLAN-LR-08-framework-owned-lessons-are-forwarded-to-the-framework-home.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.
