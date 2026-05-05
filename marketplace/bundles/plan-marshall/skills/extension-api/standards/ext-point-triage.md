# Extension Point: Triage

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_triage()` | **Implementations**: 7 | **Status**: Active

## Overview

Triage extensions declare domain-specific decision-making knowledge for the consumer-side dispatch in the [findings pipeline](../../ref-workflow-architecture/standards/findings-pipeline.md). The contract scope covers two finding types: `pr-comment` (raised on a pull request, dispatched by [`phase-6-finalize/standards/automated-review.md`](../../phase-6-finalize/standards/automated-review.md)) and `sonar-issue` (raised by SonarQube/SonarCloud, dispatched by [`phase-6-finalize/standards/sonar-roundtrip.md`](../../phase-6-finalize/standards/sonar-roundtrip.md)). For each finding, the consumer detects the domain from `file_path`, resolves the per-domain triage skill, loads it, and decides per-finding (FIX / SUPPRESS / ACCEPT / `AskUserQuestion`) using the loaded standards.

Build / test / lint findings are routed through their own producer-side store path (build-* SKILL.mds, `--plan-id` always-on); they currently flow into `manage-findings` directly without per-domain ext-triage dispatch. Future iterations may extend ext-triage scope to those types — at that point the Required Skill Sections table below is the contract surface to update.

## Implementor Requirements

### Required Skill Sections

The referenced triage skill MUST include these sections in its `SKILL.md` (or as standards files referenced from it):

| Section | Purpose | Content |
|---------|---------|---------|
| `## Suppression Syntax` (or `standards/suppression.md`) | How to suppress findings | Annotation/comment syntax per finding type |
| `## Severity Guidelines` (or `standards/severity.md`) | When to fix vs suppress vs accept | Decision table by severity |
| `## Acceptable to Accept` (or `standards/acceptable-to-accept.md`) | What can be accepted without fixing | Situations where accepting is appropriate |
| `standards/pr-comment-disposition.md` | Per-domain disposition table for PR comments | When to FIX (fix-task) vs reply-with-rationale-and-resolve vs escalate-to-user, with reply-rationale templates per category |

### Implementor Frontmatter

All triage implementor skills must include in their SKILL.md frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-triage
```

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_triage(self) -> str | None:
        return "pm-dev-java:ext-triage-java"
```

## Runtime Invocation Contract

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | str | Yes | Domain key (e.g., `java`, `python`, `documentation`) |
| `finding` | dict | Yes | Finding with `type ∈ {'pr-comment', 'sonar-issue'}`, `file`, `line`, `message`, `severity` |

### Pre-Conditions

- Domain is registered in `marshal.json` under `skill_domains.{domain_key}`
- Triage skill exists and is loadable via `resolve-workflow-skill-extension --domain {domain} --type triage`
- The producer-side stage has run: PR comments have been fetched + stored as `pr-comment` findings (`workflow-integration-{github,gitlab}:github_pr/gitlab_pr comments-stage`), or Sonar issues have been fetched + stored as `sonar-issue` findings (`workflow-integration-sonar:sonar fetch-and-store`)

### Post-Conditions

- Each finding gets a decision: **FIX**, **SUPPRESS**, **ACCEPT**, or `AskUserQuestion` (escalation) with rationale
- Suppressions include syntax-correct annotation/comment for the domain (`suppression.md`)
- The decision is recorded via `manage-findings resolve --resolution {fixed|suppressed|accepted|taken_into_account}`
- Decisions are logged to `decision.log`

### Lifecycle

```
1. Producer stage: fetch upstream items, pre-filter, store as pr-comment / sonar-issue
   findings via manage-findings add (workflow-integration-{github,gitlab,sonar})
2. Consumer dispatch: manage-findings query --type {pr-comment|sonar-issue} --resolution pending
3. For each finding:
   a. Determine domain from the file_path (architecture which-module heuristic)
   b. resolve-workflow-skill-extension --domain {domain} --type triage
   c. If extension exists: load Skill: {bundle}:ext-triage-{domain}
   d. If no extension: use default severity mapping
   e. Decide: FIX | SUPPRESS | ACCEPT | AskUserQuestion (when standards leave the call ambiguous)
4. Act on the decision (fix-task + loop-back / annotation / pr thread-reply or sonar dismiss)
5. manage-findings resolve --hash-id H --resolution {fixed|suppressed|accepted|taken_into_account}
```

See [`findings-pipeline.md` § Consumer Dispatch](../../ref-workflow-architecture/standards/findings-pipeline.md#consumer-dispatch) for the full producer→store→consumer→gate flow.

## Hook API

### Python API

```python
def provides_triage(self) -> str | None:
    """Return triage skill reference as 'bundle:skill', or None.

    Default: None
    """
```

### Return Structure

Returns a skill reference string (`bundle:skill`) or `None`.

| Value | Meaning |
|-------|---------|
| `"pm-dev-java:ext-triage-java"` | Domain has a triage skill |
| `None` | No triage skill; use default severity mapping |

## Storage in marshal.json

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  }
}
```

**Path**: `skill_domains.{domain_key}.workflow_skill_extensions.triage`

## Resolution

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain {domain} --type triage
```

## Current Implementations

| Bundle | Skill | Domain |
|--------|-------|--------|
| pm-dev-java | ext-triage-java | java |
| pm-dev-frontend | ext-triage-js | javascript |
| pm-dev-python | ext-triage-python | python |
| pm-dev-oci | ext-triage-oci | oci-containers |
| pm-documents | ext-triage-docs | documentation |
| pm-requirements | ext-triage-reqs | requirements |
| pm-plugin-development | ext-triage-plugin | plan-marshall-plugin-dev |
