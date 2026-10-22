envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-22T10:49:09Z

# Finding (HIGH PRIORITY): the runbook lane leaves SonarCloud issues open at the merge, because nothing in its contract asks it to read or clear them

Source: epic `pm-mcp-core-m2-m4`, 2026-10-22, from the landings of PLAN-90, 82, 64, 83, 84 and 85 (`/plan-marshall-runbook-lane` on opencode) and the SonarCloud API. Priority: high — the backlog refills with every landing, and a green gate hides it.

## Observed

Open SonarCloud issues on each pull request of the epic, read from `https://sonarcloud.io/api/issues/search?componentKeys=plan-marshall_pm-mcp-core&pullRequest=<N>&resolved=false` on 2026-10-22 (the quality gate was green on every one of them):

| pull request | plan | open issues at merge |
|---|---|---|
| #120 | PLAN-90 | 1 |
| #121 | PLAN-82 | 10 |
| #122 | PLAN-64 | 18 |
| #125 | PLAN-83 | 0 |
| #126 | PLAN-89 | 0 |
| #131 | PLAN-91 | 0 |
| #135 | PLAN-84 | 2 |
| #129 | PLAN-85 | 7 |

38 issues over eight merges, three of them clean. All 38 are open on `main` now (118 open on `main` in all on 2026-10-22). The landing messages relay the gate, not the issues: "quality gate passed" (#121, #120, #122: the lane did not read the issues), "7 new issues, informational, not triaged into this plan" (#129), nothing about the 2 left on #135. The lanes behave differently: the lane of #135 fixed 17 smells from the CI feedback, the lane of #129 left 7, the lanes of #120 to #122 did not open them.

## Cause (read, not assumed)

- The installed `runbook-lane` skill (plugin 0.1.1981) never mentions Sonar (`grep -ri sonar` over the skill directory finds nothing), so no step reads the pull request's open issues and none blocks the report of "ready to merge" on them.
- The SonarCloud quality gate checks thresholds on new code (coverage, duplication, rating), so it passes with open issues; a lane that reports "gate passed" has not said that the pull request is clean.
- The specs of the epic (written by the orchestrator) did not ask for it either: their Standing Constraints say how to suppress a rule, and their Done-when lists the Maven gates, not the Sonar search. That half is the orchestrator's, to be handled in the epic.

## Suggestion

A step in the runbook lane, before the lane reports the pull request ready: fetch the pull request's open issues (the `workflow-integration-sonar` `fetch_findings` verb, or the search above with `pullRequest=<N>`), fix each or dismiss it with a stated reason, and treat any other open issue as a blocker of the merge request, like a failing check. The landing-facts block gets an optional key `sonar_open_issues` (count and the rules) so the drain reads a measured figure instead of the gate's word; `unknown` when the search could not be made, never `0`.
