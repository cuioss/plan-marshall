envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T17:09:55Z

# A case-exact question asked with an existence check gets a filesystem's answer, not the repository's

component: plan-marshall:phase-5-execute
category: bug
confidence: high
source_signal: signal_qgate_pending_count

## Context

One fact — path resolution is case-**insensitive** on macOS and Windows and case-**sensitive** on Linux — surfaced independently at three gates in this plan, in three different representations. The change fixed it in exactly one of the three. The other two were caught only because a gate happened to run.

**Representation 1 — Python, fixed deliberately.** The plan added `resolve_doc_file` to `marshall-steward/scripts/determine_mode.py` precisely because, in its own words, `Path.exists` is a filesystem-level question that macOS and Windows answer case-insensitively while Linux answers case-sensitively, so a lowercase `agents.md` reads as a present `AGENTS.md` on a developer Mac. This is the plan's own reasoning, written into its own diff.

**Representation 2 — markdown workflow prose, NOT fixed (`5faf79`, 6-finalize).** `commands/tools-sync-agents-file.md:30` was changed by a single-token swap (`agents.md` → `AGENTS.md`) and then read "Use Read to check whether `./AGENTS.md` exists (creation vs update mode)". That is the *identical* question, asked with a tool whose lookup **is** the filesystem, in the same change that fixed it in Python. The consequence chains: on a case-insensitive filesystem holding a legacy lowercase `agents.md`, Step 2 resolves to update mode, Step 5 ("Write for creation or Edit for update") edits the mis-cased file in place, and Step 7's legacy cleanup removes only `doc/ai-rules.md`. The command therefore silently violates its own Critical Rule on line 70 — *"This command emits the uppercase name ONLY — there is no lowercase fallback and no dual-name write"* — and leaves the tree in exactly the state `check_docs` now reports as `wrong_case` with the remedy "rename it", a remedy no step in the command performs.

**Representation 3 — a task precondition, caught by a mechanical gate (`e5b5bd`, 4-plan).** TASK-011 declared `/Users/oliver/git/TokenSheriff/AGENTS.md` with intent `write-new`; the `files_exist` check found the target already present, because the repo's tracked `agents.md` resolves to that path on this filesystem. Remodelled to `write-replace` with a two-hop `git mv` through an intermediate name (the only rename that lands on a case-insensitive filesystem). API-Sheriff was verified by direct read to have neither casing, so `write-new` was confirmed correct there — the two foreign repos needed **different** operations for the same declared intent.

## Root cause

Two distinct causes, and the second is the interesting one.

1. **Wrong primitive.** An existence check answers *"does the filesystem resolve this name?"*. The question being asked was *"does the repository contain an entry spelled exactly this way?"*. Those differ on two of the three supported platforms. The correct primitive is a directory **listing** plus byte-for-byte basename comparison — never `Path.exists`, never a `Read` probe.

2. **The fix and the defect were in the same change, in two languages, and only the one with a mechanism got fixed.** The Python side had a function to write, so the reasoning was made explicit and executable. The markdown side was prose, so the same reasoning had nowhere to land and the token swap looked complete. This is precisely the plan's own thesis — a generic instruction cannot see a language-specific defect — reproduced inside the plan that argues it. Nothing in the plan lifecycle asks *"you just fixed this class in code; does the same class exist in the prose this code serves?"*

## The remedy that worked

Step 2 was rewritten as *"Inspect Existing State (case-EXACT)"*: it now **forbids** an existence check, lists the project root with `Glob '*.md'`, and compares returned basenames byte-for-byte against `AGENTS.md`, tabulating three outcomes — exact match → update mode; case-differing legacy entry → two-hop `git mv` through a `.tmp` intermediate, verified by a fresh listing; no entry in any case → creation mode. Step 9 post-conditions assert an exactly-named entry **plus the absence of any case-differing sibling**. The step cites `resolve_doc_file` by name, so the two representations now point at each other.

## Proposed action

1. **Make "case-exact filename question" a self-review candidate class.** Any workflow step phrased as *"check whether `{Name}` exists"* where `{Name}` differs from a sibling only in case is deterministically detectable, and the remedy is always the same: listing + byte-for-byte comparison, plus a rename path for the legacy casing.
2. **Add a cross-representation check to the diff.** When a change introduces a mechanism whose docstring or comment states a portability hazard (as `resolve_doc_file` does verbatim), the same change's markdown surface should be swept for the same hazard. Both sides are in the same diff; the connection was available and unmade.
3. **A rename deliverable owes a rename step.** Steps 1–3 detected the wrong casing; no step corrected it, while a sibling checker reported it as `wrong_case` with remedy "rename it". Detection without the corresponding remediation step is the shape that produced the silent Critical-Rule violation.

## Relation to the epic

Indirect but real: this is a first-party instance of the epic's recurring *"the guard exists and did not fire"* shape, and it is the third representation-mismatch datum this plan produced. It is offered as corpus material rather than as a new plan — the actionable half (candidate class 1 above) belongs to the self-review surface, which **PLAN-PR-011** and **PLAN-PR-018**'s retired scope both touch.

## Evidence

- Q-Gate `5faf79` (6-finalize, `pm-plugin-development:ext-self-review-plan-marshall`) — `tools-sync-agents-file.md:30`, and the Critical Rule at `:70` it silently violates; `resolution: fixed` with the case-EXACT Glob rewrite
- Q-Gate `e5b5bd` (4-plan, `plan-marshall:manage-tasks:qgate-mechanical-checks`) — `files_exist` on `/Users/oliver/git/TokenSheriff/AGENTS.md`; remodelled `write-new` → `write-replace` with the two-hop `git mv`
- `marshall-steward/scripts/determine_mode.py` — `resolve_doc_file`, added by this same change, stating the portability hazard verbatim
- `check_docs` `wrong_case` verdict with remedy "rename it" — a remedy no step of the command performed before the fix
