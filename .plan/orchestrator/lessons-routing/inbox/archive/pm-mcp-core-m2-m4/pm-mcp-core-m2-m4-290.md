envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:16Z

# Candidate lesson: workflow documents describe verbs the pinned executor does not have

Component: plan-marshall:tools-script-executor / plan-marshall:workflow-integration-git / plan-marshall:manage-solution-outline
Category (proposed): bug
Source: plan spend-removal, execute and finalize (script-failure cluster)

## Observation

- The generated `.plan/execute-script.py` of this repository pinned plugin version 0.1.1916, while the installed plugin cache also held 0.1.1947 and the skill documents read in the session came from 0.1.1947.
- Documented verbs were missing from the pinned executor: `git-workflow commit` (the commit workflow of `workflow-integration-git` and of the execute envelope names it; it returned `unknown_verb`, so the execute agents committed with plain `git commit -F` and had to say so), and `manage-solution-outline deliverable-hashes` (the Q-Gate content-hash cache; `unknown_verb` in the outline and the plan Q-Gate passes, so no pass could skip on an unchanged outline).
- The Maven build exposes no `module-tests` or `test-compile` canonical, so two of the pre-push gate's arms could only degrade with a warning.
- Each case was handled by the step's honest-degradation rule, but nothing reported the version skew itself; the preflight at the start of the run printed `executor_version: 0.1.1916` next to `installed_version: 0.1.1947` and judged it `fresh`.

## Proposed correction

- Treat an executor older than the documents' version as `stale` in `generate_executor preflight` whenever the installed manifest's script surface differs, or have the preflight list the verbs the documents name that the executor lacks.
- Add a contract test that every verb a workflow document invokes exists in the registered argparse surface of its notation.
