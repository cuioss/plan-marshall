envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:33:39Z

component=plan-marshall:marshall-orchestrator
category=bug
title=epic.md Decisions list is a second copy of the logs decision store with no stated authority

# epic.md Decisions list is a second copy of the logs decision store with no stated authority

STAGED by PLAN-203's D4 gate, not fixed. Surface:
`marketplace/bundles/plan-marshall/skills/marshall-orchestrator/templates/epic.md`.

## Observation

The template itself states that every `Decisions` entry is **ALSO** logged via
`manage-logging decision --store orchestrator`. That makes the `epic.md` list a **second copy of a
machine-held record** (`logs/`), i.e. DERIVABLE — with a drift path identical to the inbox count that
PLAN-203 fixed: the prose list can omit, reorder, or contradict a logged decision and **nothing
detects it**.

## Rule

A duplicated record needs one of two things and currently has neither: render the `Decisions` list from
`logs/` into a generated block, **or** state in the template which of the two representations is
authoritative so a reader knows which one to disbelieve when they disagree.

## Why it matters

A decisions list is exactly the surface a resuming session trusts most. Silent divergence between the
narrated decisions and the logged ones lets a superseded decision keep being cited as current — the
confident direction again.

Claim label: OBSERVED (first-party enumeration, D4 gate).
