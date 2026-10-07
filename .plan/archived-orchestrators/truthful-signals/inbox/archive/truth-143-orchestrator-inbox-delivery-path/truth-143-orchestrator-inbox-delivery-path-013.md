envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:27:59Z

# Candidate lesson: a population-derived guard that walks ONE document under-covers a roster split across TWO

## Signal source

Q-Gate `3-outline` finding `974a5e` (severity error, operator-escalated as blocking via `3b061a`).

## Observation

Caught at outline, before implementation. Deliverable 5 placed two check-points in two separate governing documents (`ref-workflow-architecture/standards/phase-lifecycle.md` and `plan-marshall/workflow/planning.md`), while deliverable 9's population-derived test reused `parse_roster` / `section_lines` from `test/_shared/_dispatch_roster.py` — a **heading-bounded walk over ONE document**.

The failure mode is the dangerous one: the guard would have enumerated at most one of the two check-points, **still reported a non-zero population**, and passed while covering half the roster. A non-zero population reads as evidence of coverage, so nothing downstream would have flagged it.

## Resolution that worked

The outline was revised to consolidate the roster into **one enumeration section** (`phase-lifecycle.md` § "Mailbox check-point roster"), with each check-point still *stated* where it executes but *enumerated* exactly once, rows in the `- key` shape the roster regex matches and each row carrying the stable anchor key its execution site emits verbatim. Deliverable 9 then closed **both directions with published populations**:

- roster-to-site reachability via each row's named document, and
- site-to-roster completeness via an anchor-key scan asserted equal to the roster set,

so a check-point added without a roster row fails instead of shrinking the guard silently.

## Corrective rule

When a test derives its population by parsing a roster:

1. **Pin the roster to one enumeration section in one document** and make the parser's single-document assumption explicit, or make the parser multi-document and publish a per-document population.
2. **Close both directions.** Roster-to-site alone lets a site exist with no row; site-to-roster alone lets a row point nowhere. Only the pair makes the guard non-shrinkable.
3. A non-zero population is **not** evidence of complete coverage. Publish the expected population size independently of the parse.
