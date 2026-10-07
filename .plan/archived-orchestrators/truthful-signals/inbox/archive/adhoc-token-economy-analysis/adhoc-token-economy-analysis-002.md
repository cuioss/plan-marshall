envelope_version=1
sender_type=plan
sender_id=adhoc-token-economy-analysis
epic=truthful-signals
kind=finding
created=2026-09-14T17:02:17Z

component=plan-marshall:manage-adr
category=bug
title=ADR number allocation reads the local tree, so two open branches take the same number and the collision lands invisibly
confidence=high
source_plan=adhoc-token-economy-analysis

# ADR number allocation reads the local tree, so two open branches take the same number

## Context

`manage-adr create --title ...` allocates the next ADR number by scanning the **local working
tree**. A branch opened before a sibling branch's ADR lands never sees that sibling, so both
allocate the same number.

⛔ **The resulting collision is invisible to git.** The two ADRs get *different filenames* —
the number is only a prefix — so there is no merge conflict, no CI failure, and no review
signal. Both merge cleanly. The duplicate surfaces only as two rows carrying the same number
in `manage-adr scan`.

This is not hypothetical. It occurred live in this repository: two ADRs landed as **021**
minutes apart — `021-machine-local-effort-to-model-map-and-resolve-chain-slot.adoc` (#1490)
and `021-Economy_rules_bind_the_persisted_artifact_never_the_reasoning_that_produced_it.adoc`
(#1492). `manage-adr scan` on the resulting `main` reported `20, 21, 21`. It was cleared by
#1493 renumbering the second to 022, which cost a whole extra PR.

The failure mode matches this epic's theme exactly: a confident signal — a clean merge, green
CI, no conflict — hiding the caveat that the tree now holds two ADRs with one identity. Any
cross-reference written as "ADR-021" is ambiguous from that moment on, and one already exists
(`_cmd_effort.py` cites ADR-021 meaning the effort-map one).

## Root cause

Allocation is a read of local state used as though it were a claim on a shared namespace. The
number is a **repository-global identifier**, but nothing global is consulted when it is
issued and nothing validates uniqueness when it lands.

A second factor made the live instance costlier than it needed to be: adding a PR to the
platform merge queue **locks the head branch**. After `ci pr merge-queue`, both `git push`
and `git push --force-with-lease` are refused with `protected branch hook declined`, so the
renumber could not ride along in the same PR once the collision was spotted. The window in
which a cheap fix is possible closes at enqueue, not at merge.

## Proposed action

Ordered cheapest-first; the epic settles which to take.

- **A landing-time uniqueness check.** A duplicate ADR number is mechanically detectable from
  the tree alone — `manage-adr scan` already computes the numbers it would need. A check that
  fails when two entries share a number catches every instance of this regardless of how it
  arose, and needs no change to allocation. This is the highest-leverage option: it closes the
  class, not the cause.
- **Allocate against the remote.** Have `create` consult `origin/main` rather than the local
  tree, or fail closed when the local tree is behind it. Narrower than the check above (it
  cannot catch two branches created after the same fetch) and it makes a local verb depend on
  network state, so it is worth considering only alongside the check, not instead of it.
- **Report the ambiguity rather than hide it.** `manage-adr scan` currently emits duplicate
  numbers as two ordinary rows. Surfacing a duplicate as a distinct state would let any
  consumer notice, and is the read-side counterpart to the check.

One adjacent observation, recorded but not proposed as work: `doc/adr/` now carries two
filename conventions — `Title_With_Underscores` (what `create` generates) and
`lowercase-hyphenated` (hand-named). Whichever is canonical, the generator's output should
match it.

## Evidence

- `manage-adr scan` against `main` between #1492 and #1493 — `20, 21, 21`; after #1493 —
  `20, 21, 22`
- `git log origin/main` — `fb8aadc9c (#1490)` and `fea2f3ea3 (#1492)` both adding an
  `021-*.adoc`, neither conflicting
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` — an
  existing by-number citation of ADR-021, which is what made the collision ambiguous rather
  than merely untidy
- The enqueue lock: `git push` and `--force-with-lease` to a queued head branch both refused
  with `protected branch hook declined`, observed on PR #1492
