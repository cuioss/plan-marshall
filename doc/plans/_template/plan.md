# {Plan title — what changes, stated as an outcome}

> **Template.** Copy this file to `doc/plans/{epic}/{plan-name}.md`, fill it in, delete this
> blockquote and every `{…}` placeholder. The `cloud-plan-lane` skill moves it into
> `doc/plans/{epic}/{plan-name}/plan.md` at Step 3 of the run.
>
> `{plan-name}` is a short kebab-case slug — it becomes the directory name and the branch name.

**Epic:** {truthful-signals | review-apparatus | code-intelligence-substrate}
**Branch prefix:** {feature | fix | chore} — new capability / bug fix / maintenance-refactor-docs

## Problem

{What is wrong or missing today, in terms of observable behaviour. One or two paragraphs.}

{State the mechanism: *why* it behaves this way, naming the file and symbol responsible. If the
mechanism is inferred rather than read, label it under Claim Labels below.}

## Goal

{What is true when this plan has landed. One paragraph. Not a restatement of the deliverables.}

## Deliverables

Each deliverable is independently verifiable and small enough to review. Roughly six or more is a
signal to split the plan.

1. **{D1 — short name}** — {what changes, and in which file or symbol}
   *Done when:* {the observable condition that settles it — a passing test, a changed output, a
   removed branch. Not "the code is updated".}
2. **{D2 — short name}** — {…}
   *Done when:* {…}

## Out of scope

{What a reader might reasonably expect to be included and deliberately is not, with the reason.
An explicit boundary here is what stops scope drift mid-run.}

## Expected surface

{The files and modules this plan is expected to touch. Used to judge whether two plans can run
concurrently, and to spot collateral change during verification.}

- `{path/to/file.py}` — {why}
- `{path/to/other}` — {why}

## Claim labels

Every scoping premise is labelled, because a downstream reader cannot otherwise tell what was read
from what was inferred. Label the mechanism, the expected surface, and any derived count.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| {the claim} | OBSERVED | {file + symbol that was actually read} |
| {the claim} | HYPOTHESIS | {file + symbol that will settle it — required for every HYPOTHESIS} |

An asserted **absence** ("X does not exist, build it") is verified exactly as an asserted presence,
and is the higher-risk half: an unverified absence produces duplicate work against something that
already exists. A `HYPOTHESIS` with no named artifact must not ship — resolve it or drop the claim.

## Verification

{How the run proves the goal was met, beyond the per-deliverable "done when" conditions. Name the
tests to run or add, and anything that must be checked by reading rather than by executing.}

## Notes

{Prior art, related PRs, constraints, sequencing against other plans, decisions already taken.}
