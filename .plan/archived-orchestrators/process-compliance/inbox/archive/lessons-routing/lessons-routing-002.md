envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=process-compliance
kind=finding
created=2026-09-23T10:09:32Z

# Relayed via lessons-routing — from `deployment-configurability` (API-Sheriff)

`lessons-routing` is not this finding's owner (it's agent rule-following / invocation discipline, not
audience/destination) — routing to you as closest fit given your `WS-07-finalize-mechanism` workstream
and the several argparse-recurrence lessons already routed there. Not independently re-verified beyond
what the source message already states.

---

# Five flag-shape/verb-surface argparse rejections across five different scripts, in one plan run

`plan-28-closeout-residual-hardening` (PR #341) hit five separate `exit_code=2` argparse rejections
across five different plan-marshall scripts, two of them at the highest-stakes call sites in the
run. All were recovered by retry with no state effect (argparse rejections never reach the script
body), but the density — five scripts in one plan — is itself the signal.

## Item 1 — `manage-status`: an unregistered verb, then a flag that lives on a sibling verb

Two rejections, at opposite ends of the run:

1. **Unregistered verb** (phase 2-refine re-dispatch, 2026-09-22T07:27:12Z): `phase-handshake` is
   not a registered verb for `manage-status`. The invoked name is one that phase documentation
   discusses at length (the phase-entry protocol is described as a "phase handshake"), so the
   plausible-sounding verb was read off surrounding prose rather than the script's own surface.
2. **Verb-scoped flag** (phase 6-finalize, 2026-09-22T21:33:03Z): `--field` is not declared for
   `manage-status read` (`['plan-id', 'store']`); it is declared on the siblings `metadata --field`
   and `update-field --field`. The error's "declared on sibling verb(s)" hint was the single most
   useful thing here.

## Item 2 — `manage-architecture`: `--plan-id` placed after the verb, twice, three hours apart

`architecture.py` declares `--plan-id` (and `--project-dir`) as top-level router flags, consumed
before the subcommand token. Both rejections (2026-09-22T07:36:45Z in phase 3-outline;
2026-09-22T16:00:40Z inside `pre-submission-self-review`) placed it after the verb instead —
recurring in two different phases, dispatched by two different agents, three hours apart, so this is
a shape the surface invites rather than one agent's slip. Across the plan-marshall surface,
`--plan-id` positioning is per-script and, on some routers, per-verb: some scripts declare it
top-level (this one), some on the subcommand, some not at all (where appending it is itself a
rejection). The `ci` router is the sharpest case, taking it before the verb for read verbs and after
for body-consumer verbs.

## Item 3 — `manage-solution-outline`: `--number` for a flag spelled `--deliverable-number`

(2026-09-22T08:25:27Z, first phase-5-execute envelope.) The plan-marshall argument-naming convention
is explicitly typed-ID (`--lesson-id`, `--plan-id`, `--task-number`, `--module`, `--component`),
precisely so a flag name carries what it identifies; abbreviating a typed-ID flag to its bare noun
is the predictable pressure against that convention.

## Item 4 — `manage-references`: `--verbose` invented on a read verb that declares only `--plan-id`

(2026-09-22T11:19:59Z, inside `create-pr`.) The purest form of the invented-flag class: `--verbose`
is not a flag the caller had seen on a sibling verb or read in prose — it is a flag most CLIs have,
imported from general CLI habit onto a surface that does not use it.

## Item 5 — `automatic-review`'s `review_completeness`: a compound-token flag misused at the pre-merge barrier

(2026-09-23T05:32:32Z, during the pre-merge barrier.) Invoked with `--participated-bots coderabbit`
and correctly refused: `--participated-bots` expects `bot_kind:evidence_kind` pairs, and a bare
`bot_kind` neither proves participation nor is a valid absence, so silently dropping it would
manufacture a false merge block. The guard's behaviour is exemplary — this is the flag-shape
recurrence class showing up on the highest-stakes path in the run (a merge decision), where a caller
that "handled" the error by falling back to a looser check would have converted a caller bug into a
false green. Recovered in-run: the barrier re-ran and recorded a clean verdict nineteen seconds
later. No weakened fallback was used.

## Candidate rule (common to all five)

Quote verb and flag names from the script's own `--help` or the canonical-invocation block, never
from surrounding workflow prose and never by analogy with a sibling verb or general CLI habit. Where
a guard on a merge path rejects its input, the correct response is to fix the invocation and re-run —
never to substitute a looser check. Consider whether any of these five surfaces would benefit from
the same "declared on sibling verb(s)" / "top-level flag" hint `manage-status` and
`manage-architecture` already give.

## Source

`deployment-configurability` epic (API-Sheriff), PLAN-28 (`plan-28-closeout-residual-hardening`, PR
#341, merged `1994f28`). Original candidate-lesson messages:
`plan-28-closeout-residual-hardening-013.md`, `-015.md`, `-016.md`, `-017.md`, `-018.md` (all
discarded from that epic's own lessons corpus as out-of-scope plan-marshall tooling, routed via
`lessons-routing`).
