---
name: review-skill
description: Content-quality review of knowledge skills for correctness, consistency, structure, and LLM-optimization
user-invocable: true
allowed-tools: Read, Glob, Grep
---

# Review Skill

Reviews a knowledge skill's content quality. Complements `/plugin-doctor` (structure and rule compliance) by analyzing the actual information across all documents.

## Parameters

**skill** (required) — Skill path or `bundle:skill-name` notation.

**focus** (optional) — Single dimension: `correctness`, `structure`, `llm-optimization`, `consistency`. Default: all.

## Workflow

### Step 1: Inventory

Resolve skill path. Glob all files recursively. Read SKILL.md, then every file in `standards/`, `references/`, and other subdirectories. Record: filename, line count, role.

### Step 2: Review per dimension

Load the relevant standards document for each dimension (or all four if no `focus` given). Apply the criteria from each document to the full corpus. Each finding needs: severity (high/medium/low), file:line location, concrete recommendation.

- `standards/correctness-completeness.md` — factual accuracy, gaps, stale content
- `standards/consistency-duplication.md` — contradictions, term drift, redundancy
- `standards/structural-coherence.md` — hierarchy, cross-refs, ordering
- `standards/llm-optimization.md` — actionability, verbosity, noise

### Step 3: Report

```
Skill: {name}
Documents: {count} ({total_lines} lines)
Assessment: {STRONG | ADEQUATE | NEEDS WORK}

## Findings

### Correctness and completeness
{findings or "No issues"}

### Consistency and duplication
{findings}

### Structural coherence
{findings}

### LLM optimization
{findings}

## Top recommendations (max 5)
1. ...
```

### Step 4: Plugin-doctor

Run `/pm-plugin-development:plugin-doctor skills skill-name={skill-name}` and append structural findings under a separate heading.

## Rules

1. Read every document before analyzing.
2. Read-only — do not modify files.
3. Skip what plugin-doctor covers (frontmatter, enforcement blocks, Rule 9/10a/11). Step 4 handles that.
4. Ground findings in `file:line` locations.
