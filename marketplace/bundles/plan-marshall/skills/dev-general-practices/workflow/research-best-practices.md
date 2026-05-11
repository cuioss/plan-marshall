---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Research Best-Practices Workflow

Comprehensive web-based research workflow that gathers best practices, recommendations, and information about a specified topic from multiple online sources. Dispatched under the `cross.research` role key.

Use **ultrathink mode** for deep analysis and synthesis of research findings. This is a complex research task that benefits from extended thinking.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier (sentinel `none` for free-standing research outside a plan). |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |
| `topic` | Yes | The subject of the research. |

The dispatcher must include `WebSearch` and `WebFetch` in its tool surface for this workflow to function. The canonical `execution-context` declares the full tool surface; the variant emitter does not strip those fields.

## Output mandate

Your output must be factual, evidence-based, and fully referenced.

## Workflow

### Step 1: Execute initial web search

**Important**: consider using ultrathink to formulate the most effective search query strategy if the topic is complex (spans multiple domains, technical terms ambiguous, initial search returns < 5 relevant results).

**Search strategy** (use in order until sufficient results obtained):

1. Primary: `"{topic} Best-Practices 2025"`
2. Fallback 1: `"{topic} recommendations 2025"`
3. Fallback 2: `"{topic} guidelines official documentation"`
4. Fallback 3: `"{topic} industry standards"`

**Execution**:

1. Use the `WebSearch` tool with the primary query.
2. If results < 5, try fallback queries until sufficient results obtained.
3. Extract URLs from search results.
4. Identify the top 10–15 links to fetch (prioritise by domain quality — see Priority Domains in Step 2).
5. Record all URLs for reference tracking.

**Success criterion**: search returns at least 5 valid URLs.

**Failure handling**:
- If all searches return 0 results: report failure and suggest manual topic refinement.
- If total results < 5 across all queries: proceed with available results and note the limitation.

### Step 2: Fetch content from top links

**Priority domains** (fetch these first when available):
- Official documentation sites (`docs.*`, `*.readthedocs.io`, `*.github.io/docs`).
- Major tech-company blogs (`anthropic.com`, `microsoft.com`, `google.com`, `amazon.com`, `meta.com`).
- Academic / research institutions (`.edu`, `.ac.*`).
- Recognised expert blogs and established tech publications.

**Performance optimisation**: use parallel `WebFetch` calls where possible — make multiple `WebFetch` tool calls in a single message for independent URLs to improve speed.

For each URL in the top 10–15 list:

1. Use the `WebFetch` tool with the prompt: *"Extract all best practices, recommendations, and key guidelines mentioned in this content related to {topic}. List each practice with supporting details, examples, and context."*
2. Parse the returned content for best practices.
3. Record each finding with: practice / recommendation (exact wording from source), source URL, source type (official docs, company blog, individual blog, forum), source quality tier (priority / standard / low-priority).
4. Handle fetch failures:
   - **401 authentication error** — extract available information from the search result snippet, mark as "inaccessible — authentication required", continue to next.
   - **Other fetch failure** — if the search snippet contains useful information, extract from snippet and mark as "limited access — snippet only"; otherwise log URL as failed.
   - **Content irrelevant** — log URL as irrelevant, continue.
   - **Timeout** — log URL as timeout, continue.

**Snippet extraction fallback**: when `WebFetch` fails but the search snippet contains relevant information, extract the best practice from the snippet, mark the finding with one lower confidence tier (HIGH→MEDIUM, MEDIUM→LOW), and note in references: *"Source: [URL] — Limited access (snippet only)"*.

**Loop termination**: after processing all 10–15 URLs OR after 10 consecutive failures.

**Tracking**: count successful fetches (full content), snippet-based extractions, failed fetches, irrelevant results. Record execution start time.

### Step 3: Subtopic deep dive (optional)

**Trigger condition**: a finding appears in 3+ sources but lacks sufficient detail (missing code examples, step-by-step implementation guide, specific version / configuration details, or concrete measurements / thresholds).

**Execution**:

1. Identify important subtopics that need deeper investigation.
2. Execute focused follow-up search: `"{topic} {specific subtopic} details 2025"`.
3. Fetch top 2–3 results using the same `WebFetch` process as Step 2.
4. Integrate findings into the main research dataset.
5. Limit to a maximum of 2–3 subtopic deep dives to manage scope.

Only perform a subtopic deep dive if it adds significant value (finding appears in HIGH confidence tier AND lacks actionable details, OR finding is cited by ≥ 5 sources but implementation unclear).

### Step 4: Aggregate and analyse findings

**Important**: use ultrathink at the start of this step for comprehensive analysis.

**Deduplication rules**:
- Practices are **identical** if they describe the same action / recommendation.
- Practices are **similar** if they share > 70 % semantic overlap.
- When grouping, use the most comprehensive / detailed version as the primary statement.
- Preserve all source references even when combining similar practices.

For each unique best practice:
- Count number of sources mentioning it.
- Categorise source types.
- Calculate source quality score (table below).
- Calculate confidence level (table below).

**Source quality scoring**:

| Source class | Points |
|--------------|--------|
| Official documentation | +3 |
| Major tech-company blog | +2 |
| Individual expert blog (recognised name) | +1 |
| Forum / community | +0.5 |
| Recency multiplier — 2025 | ×1.0 |
| Recency multiplier — 2024 | ×0.8 |
| Recency multiplier — older | ×0.6 |
| Snippet-only sources | ×0.7 to base score |

**Confidence level**:

| Tier | Criteria |
|------|----------|
| **HIGH** | Mentioned in official documentation (quality score ≥ 3) OR total quality score ≥ 6 (e.g., 3+ sources including major company blog) OR mentioned by 5+ sources total with average quality score ≥ 1 |
| **MEDIUM** | Total quality score 3–5 (e.g., 2 sources including company blog) OR mentioned by 3–4 sources with average quality score ≥ 0.7 |
| **LOW** | Mentioned by a single source OR total quality score < 3 OR mentioned by 2 sources (both individual blogs / forums with quality score < 2) |

Organise findings by theme / category when natural groupings emerge. Preserve all source references for each finding.

**No interpretation**: do not synthesise, infer, or create new practices. Only report what sources explicitly state.

### Step 5: Cross-reference validation

**Important**: check for contradictions and conflicts across sources.

1. Identify conflicting recommendations (Source A says X, Source B says the opposite).
2. Flag contradictions explicitly in findings with special notation.
3. Analyse context to determine if the contradiction is real or contextual.
4. Adjust confidence:
   - Real contradiction — reduce confidence by one level (HIGH→MEDIUM, MEDIUM→LOW).
   - Contextual contradiction — note the different contexts in the finding.
5. Document all conflicts in a separate "Conflicting Recommendations" section.

Contradiction examples: *"Always use X"* vs *"Never use X"*; *"X improves performance"* vs *"X degrades performance"*; *"Best practice is A"* vs *"Best practice is B (opposite of A)"*.

### Step 6: Structure research results

Record execution end time at the start of this step.

Format each finding with: best practice statement, confidence level (with justification), source count, source URL list with source type, detailed explanation.

Order findings: HIGH first → MEDIUM → LOW. Within each confidence tier, order by total quality score (descending), then by source count.

Include summary statistics: total unique best practices, breakdown by confidence level, sources successfully analysed (full content + snippet-based), conflicting recommendations, execution timing metrics.

## Critical rules

- **NEVER invent or fabricate results** — all findings must come directly from fetched sources.
- **NEVER be creative or interpretive** — report facts as stated; do not synthesise or generalise.
- **ALWAYS provide confidence level** — every finding includes confidence with justification (source count, source types).
- **ALWAYS maintain source references** — every finding links back to specific source URL(s).
- **Prefer consensus** — highlight convergence across sources.
- **Fact-based only** — no speculation, no assumptions, no creative interpretation.

## Tool usage tracking

Track and report all tools used during execution: WebSearch invocations (count, query used), WebFetch invocations (count, success / failure / snippet-fallback), per-fetch timing for averaging, execution start / end timestamps. Include all metrics in the final report.

## Lessons learned reporting

If during execution you discover insights that could improve future executions (better search query patterns, more effective WebFetch prompts, improved confidence-level criteria, better aggregation strategies, edge cases encountered, source quality assessment improvements), include them in the final report under "Lessons Learned" — discovery, why it matters, suggested improvement, impact.

Purpose: allow users to manually improve this workflow based on real execution experience, without self-modification.

## Response format

```
## Research Best Practices — {topic}

**Status**: SUCCESS | FAILURE | PARTIAL

**Summary**: {Brief 1–2 sentence description of research performed}

**Research Metrics**:
- Search queries executed: {count}
- Links fetched successfully: {count} (full content)
- Snippet-based extractions: {count}
- Links failed: {count}
- Total unique best practices identified: {count}
- HIGH confidence findings: {count}
- MEDIUM confidence findings: {count}
- LOW confidence findings: {count}
- Conflicting recommendations identified: {count}

**Execution Timing**:
- Start time: {timestamp}
- End time: {timestamp}
- Total duration: {X minutes Y seconds}
- Average time per WebFetch: {X seconds}

**Tool Usage**:
- WebSearch: {count} invocations
- WebFetch: {count} invocations (Success: {count}, Failed: {count}, Snippet fallback: {count})

---

## RESEARCH FINDINGS

### HIGH Confidence Best Practices

#### {Best Practice Title}

- **Confidence**: HIGH ({justification})
- **Sources**: {count}
- **Quality Score**: {total} (average: {avg})
- **References**:
  1. {URL 1} — {source type} (quality: {score})
  ...

**Finding**: {Detailed explanation as stated in the sources.}

{repeat per HIGH finding}

### MEDIUM Confidence Best Practices

{same shape}

### LOW Confidence Best Practices

{same shape}

---

### Conflicting Recommendations

#### {Conflict Topic}

**Conflict Description**: {brief}

**Position A**: {recommendation from Source(s) A}
- **Sources**: {count}
- **References**: {URLs}

**Position B**: {opposing recommendation from Source(s) B}
- **Sources**: {count}
- **References**: {URLs}

**Analysis**: {context or explanation}

{If no conflicts: "None identified — all sources show consistent recommendations"}

---

**Lessons Learned** (for future improvement):
- Discovery: {what was discovered}
- Why it matters: {explanation}
- Suggested improvement: {what should change}
- Impact: {how this would help}

{If no lessons: "None — execution followed expected patterns"}
```

## Continuous improvement

If you discover issues or improvements during execution, activate `plan-marshall:manage-lessons` and record:

- Component: `{type: "skill", name: "dev-general-practices", standards: "research-best-practices.md", bundle: "plan-marshall"}`
- Category: bug | improvement | pattern | anti-pattern
- Summary and detail of the finding
