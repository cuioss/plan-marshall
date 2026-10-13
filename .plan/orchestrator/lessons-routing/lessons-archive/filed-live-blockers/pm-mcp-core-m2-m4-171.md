envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:08Z

# Candidate lesson: CodeRabbit concerns raised only in the summary body were not filed as findings

Source: run event in plan verify-not-resolve (PR #43), automatic-review / fetch_findings.

## What happened

CodeRabbit raised review-surfaced defects (project-script arguments lost before launch; interpreter host tool calls) and two security concerns. Some of these appeared only inside its summary/walkthrough body, not as inline review threads. `fetch_findings` filed no finding for the concerns that existed only in the summary body. They were found by reading the summary by hand.

## Why it matters

The findings pipeline counts as complete without them, so a real defect or security concern can pass the merge gate untriaged. This is a quiet hole in coverage.

## Suggested correction

Make `plan-marshall:workflow-integration-github` `fetch_findings` parse the CodeRabbit summary/walkthrough body, including "Outside diff range" and actionable or security sections, and file each item as a finding. Or at least report that the summary body carried actionable items it did not file. Add a fixture with a summary-only security concern.

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-003.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
