envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:24:47Z

component=plan-marshall:plan-retrospective
category=bug
title=Two report sections are structurally unrenderable and their non-emission is reported as benign

# Executive Summary and Phase Dispatch Boundaries can never render on a run that follows the documented workflow

## Context

`references/report-structure.md` declares fifteen sections and states the compiler "must emit exactly these sections in this order". Two of them cannot be produced by any documented step.

**Executive Summary (section 1, NOT marked conditional).** `collect-fragments` validates every `add` against a canonical aspect registry of seventeen keys. There is no `executive-summary` key. No fragment can supply the section, so it lands in `sections_omitted` — which the spec defines as "benign: nothing was lost". The report's headline severity synthesis is silently absent from every run.

**Phase Dispatch Boundaries (section 5, conditional).** Its trigger is "the `dispatch_boundaries` fragment carries at least one phase entry reporting `present: true`". The registry DOES declare `dispatch_boundaries` — the only underscore-cased key among sixteen kebab-cased siblings — but it appears nowhere in `SKILL.md`'s Step 3 aspect table, so no documented step produces it. Meanwhile `analyze-logs` emits exactly that data **nested inside** the `log_analysis` fragment, where the compiler does not look.

Observed first-hand: the first compile of this report omitted both, reporting `sections_dropped[0]` — a clean pass. Hand-registering a top-level `dispatch_boundaries` fragment and recompiling made section 5 render with three phases of real content. It was a **drop**, reported as an omission.

## Root cause

The spec's own partition is `omitted` = "the trigger fragment was absent or carried nothing renderable — nothing was lost" versus `dropped` = "a fragment WAS present and carried payload yet did not render — loud". A section whose producer does not exist takes the benign branch, because the compiler can only observe the fragment bundle, not the workflow that was supposed to fill it. Absence of a producer is indistinguishable from absence of content.

## Proposed action

1. Add `dispatch_boundaries` (and rename it to kebab-case) to `SKILL.md` Step 3's aspect table with a documented producer, or change section 5's trigger to read the nested `log_analysis.dispatch_boundaries`.
2. Either add an `executive-summary` producer step or mark section 1 conditional in `report-structure.md` — today the spec and the registry contradict each other.
3. Add a third bucket, or a startup assertion: a section in `report-structure.md` with no registry key that could ever supply it is a build-time error, not a per-run omission.

## Evidence

- `collect-fragments add --aspect dispatch-boundaries` returned the registry: 17 keys, no `executive-summary`, `dispatch_boundaries` present but undocumented
- compile pass 1: `sections_omitted[3]` = Executive Summary, Phase Dispatch Boundaries, Permission Prompt Analysis; `sections_dropped[0]`
- compile pass 2 (same run, `dispatch_boundaries` hand-registered): Phase Dispatch Boundaries in `sections_written[16]`
