envelope_version=1
sender_type=plan
sender_id=cross-repo-telemetry-archive-and-analyze
epic=post-run-quality
kind=candidate-lesson
created=2026-10-03T23:22:04Z

component=plan-marshall:plan-retrospective
category=improvement

# Union split-PR landings and exclude sibling-repo paths in the shared footprint resolver

## Context

The footprint resolver answered from the realized_capture tier, which held only the 78 paths of the final PR #1694. Part 1 of the split (#1692, 74 test-mirror deletions) and the 111 declared paths that landed in the sibling plan-marshall-telemetry repository were invisible to it. As a result artifact-consistency reported recall 27% (error), manifest-decisions reported 186 declared-but-unrealized paths, and outline-vs-shipped reported 185 include_unrealised paths as a possible silent descope, although every deliverable shipped.

## Root cause

The resolver assumes one plan = one PR in one repository. It has no tier that unions several PRs landed for one plan, and it does not tell apart a declared path outside the repository (sibling-repo prefix, ../{repo} placeholder) from a declared in-repo path that never changed.

## Proposed action

Have the resolver union every PR the plan recorded as landed (create-pr firings or merge commits), and partition declared paths outside the repository root into an "out of repo, not measurable here" bucket that is excluded from the recall denominator and reported separately, never as a descope.

## Evidence

- aspect: artifact_consistency - affected_files_recall 27.3% (70 of 256), footprint tier realized_capture
- aspect: manifest_decisions - declared_vs_realized_set: 186 outline_only, 8 references_only
- aspect: outline_vs_shipped - include_unrealised 185 of 255
- git: 5ec134b0f (#1692) deleted 74 of the 185; the remaining 111 are plan-marshall-telemetry/ paths
