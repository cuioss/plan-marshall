envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:52Z

# direct-gh-glab-usage aspect reports zero while a leaf self-reported a direct `gh` call

**Component:** plan-marshall:plan-retrospective (`direct-gh-glab-usage` Surfaces A and B), plan-marshall:workflow-integration-github / tools-integration-ci (missing read verb)
**Category:** bug
**Source plan:** plan-14-operator-and-question-stores (PR #93), from plan-retrospective

## Observation

The sonar-roundtrip leaf at HEAD 971d0df reported in its hand-back: "I ran `gh pr view 93 --json comments` directly to read the decoration comment, which the persona rule forbids." The rebase leaf likewise reported one Bash `git grep -n`. The `direct-gh-glab-usage` aspect still returned `total: 0`, because it scans only the plan logs and the plan diff, and a leaf's own Bash calls appear in neither. The `gh` call happened because no script exposes the PR comments the leaf needed to tie the Sonar analysis to the head (see lesson 003).

## Suggested corrective action

- Add a surface that scans the session transcript's leaf Bash calls, or the leaves' hand-back self-reports, for `gh`/`glab`/`git grep`, so a self-reported breach is counted.
- Expose a `ci pr comments --author <bot>` read verb, so the Sonar head-binding check needs no direct `gh`.
