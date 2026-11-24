envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=finding
created=2026-11-24T12:15:21Z

# CHANGE REQUEST — priority: HIGH — plan-orchestrator: route plan-marshall-owned lessons and findings to the lessons-routing inbox by itself

Requested by the operator of epic `libraries-initial-implementation` (repository git-document-repository), 2026-11-24, plugin 0.1.2184.
Class: change request for the `plan-orchestrator` skill (verbs `analyze`, `lessons`) and for `manage-lessons`. Priority: high.

## Problem

An epic that orchestrates a project other than plan-marshall collects, at every landing, lessons and tooling observations whose subject is plan-marshall itself
(components `plan-marshall:*` and the domain bundles `pm-*`). Today they stay in the project's lessons store, its inbox drain (`Promote`) and its Open Defects, and moving
them to the framework repository takes an explicit operator instruction every time. In this epic the operator had to ask twice (2026-11-24) and 76 lessons plus one
finding were moved by hand; the project's lessons store had mixed the project's own lessons (8 `git-store`, 1 `git-core`) with 76 framework lessons, and the
recurrences of framework lessons were appended to project-local files that only the framework can act on.

Mechanics that made the hand move awkward, each a defect of the tooling:
1. `inbox write` resolves its destination through the store seam keyed on the CWD, so a write into another repository's `lessons-routing` inbox only works when the verb is run
   from that repository (`cd {framework_repo}` and the foreign payload path). Nothing names or validates the framework repository.
2. `manage-lessons remove` has no verdict for "moved to another repository": `completely_covered` demands a covering clause, `superseded` was used with a free-text reason
   naming the message. The tombstone therefore cannot be told from a lesson superseded by another lesson.
3. The `lessons` verb's cross-repo pass (`remote_lessons_dir`) is a PULL from a sibling checkout into the current repository; nothing pushes from a project to the framework.
4. The `analyze` inbox drain (Step 5b) has four dispositions (`promote`, `fold`, `stage`, `discard`), none of which says "forward to the framework", so a framework-owned
   `candidate-lesson` is promoted into the project's store.

## Requested change

1. **A framework home.** One resolvable setting naming the plan-marshall checkout that owns `lessons-routing` (a config key of the orchestrator tier, or a derivation from the
   installed plugin's source), validated on use: the path exists, `corpus epics` there lists `lessons-routing` in `active[]`, and its `status.json` phase is not `closed`
   (a closed or unreadable epic is not written to; the item is held and reported, as Step 4 of the `lessons` workflow already requires for a sibling).
2. **An ownership predicate** `framework-owned(component)`: true for `plan-marshall:*` and for every bundle of the installed marketplace (derived from the plugin inventory, not a
   hard-coded list of `pm-*` names). One implementation, used by every caller below.
3. **`analyze` inbox drain:** a new closed disposition `forwarded` (counted inside `messages_archived`, so the closure equation holds) for a `candidate-lesson` or `finding` whose
   subject is framework-owned: write it into the framework home's `lessons-routing` inbox (kind kept: `candidate-lesson` for a lesson body, `finding` for an observation), then archive
   the source message; `Promote` is not offered for it. A message that is partly the project's (a defect in the project that is also a tooling gap) is split by the orchestrator:
   the project part stays, the tooling part is forwarded.
4. **`analyze` landing analysis:** a tooling gap found while analysing a landing (a read that is `undecidable`, a landing fact left `unknown`, a figure that disagrees with the
   retrospective) is forwarded as a `finding` in the same pass; the evidence stays in the landing report.
5. **`lessons` verb:** the same predicate selects, in the local corpus, the framework-owned lessons; they are forwarded as `candidate-lesson` messages (one per lesson, body and
   recurrences included, header keys `component`, `category`, `title`, `source_lesson`, `source_repo`, `source_created`) and retired locally ONLY after the write returned success.
6. **`manage-lessons remove`:** a verdict `relocated` (or `moved`) whose required evidence is the destination, `{repo}:{epic}/inbox/{message}`, recorded in the tombstone.
7. **Idempotence:** a forwarded lesson is never written twice: the destination message carries `source_lesson` and `source_repo`, and the verb refuses (or returns the existing
   message) when a message with the same pair is already present in the destination's `inbox/` or `inbox/archive/`.
8. **Record:** every forward is a decision-log line and a row in a `lessons-moved.md` of the sending epic (lesson id, component, destination message). The sender id is the sending
   epic's slug, the sequence is the destination's allocation. The orchestrator never touches the framework repository's git state (the files sit untracked in its ledger worktree
   until it lands its own ledger).

## Acceptance

- A candidate lesson with component `pm-dev-java:junit-core` drained in a project epic ends in the framework home's `lessons-routing` inbox, archived at the source, with no
  `manage-lessons add` in the project store; one with component `git-store` is promoted locally as before.
- With the framework epic closed, nothing is written, the item is reported and the local copy stays.
- A second drain or sweep of the same lesson writes nothing.
- A `lessons` sweep over a store holding 76 framework lessons forwards 76 messages and retires 76 lessons; a run that fails after the 40th write leaves the remaining local lessons in place.
- The tombstone of a retired lesson names the destination; `drained[]` and the closure equation account for `forwarded`.

## Evidence

This epic, 2026-11-24: messages `libraries-initial-implementation-001` to `-077` in this inbox (74 `plan-marshall:*` lessons, one finding, two `pm-dev-java` lessons), the mapping
`lessons-moved.md` and the Decisions entry "STANDING RULE: everything about plan-marshall leaves this epic" in the epic's `epic.md`. The rule is applied by hand until this change ships.
