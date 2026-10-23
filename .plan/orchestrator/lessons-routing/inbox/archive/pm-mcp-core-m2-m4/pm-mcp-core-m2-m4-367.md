envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:52Z

# Security-audit leaf passed green after reading 5 of 17 fixtures

- Source: plan-retrospective (chat-history-analysis, security-audit returns of both iterations)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:manage-architecture
- Category: bug
- Confidence: high

## Context

In iteration 1, finalize-step-security-audit reported "35 files, all examined" and 0 findings, but read only 5 of the 17 `.txt` fixtures under `pm-providers/pm-provider-git/src/test/resources/ported/worktree-sha/`. The leaf said content search does not index those fixtures and Grep was denied to it. It recorded the step done anyway. Iteration 2, after the S5778 fix commit, read all 17 in full.

## Root cause

`architecture search --content` did not cover these test-resource files (outside the module-attributed inventory, or not walked), and the leaf, with Grep withheld, degraded to spot checks and passed green. The execution-context contract forbids exactly this: a leaf must not silently degrade to spot checks with shrunken coverage.

## Proposed action

Check whether the architecture inventory walks `src/test/resources/**` plain-text files and include them in `search --content` if not. In the security-audit (and other coverage-class) leaves, report a coverage gap in the return when files of the footprint could not be read, instead of recording done with "all examined".

## Evidence

- security-audit iteration 1 return: "I read 5 of the 17 .txt fixtures plus the roster, and the other 11 were not opened"; display_detail "0 edits, 0 findings"
- security-audit iteration 2 return: "Fixtures, all 17 of 17 opened in full"
- aspect: chat-history-analysis -- finding on shrunken iteration-1 coverage
