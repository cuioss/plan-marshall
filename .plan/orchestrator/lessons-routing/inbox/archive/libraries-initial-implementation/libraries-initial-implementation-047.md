envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:30Z

component=plan-marshall:tools-script-executor
category=bug
title=execute-script.py: check the Python 3.11 requirement before dispatching and name the interpreter found
source_lesson=2026-11-22-13-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# execute-script.py: check the Python 3.11 requirement before dispatching and name the interpreter found

# Candidate lesson: no pre-flight check names the Python 3.11 requirement; scripts broke when python3 resolved to 3.10 after a resume

- Source signal: orchestrator observation in plan plan-09-store-release-index-listeners (inbox plan-09-store-release-index-listeners-006; work log 2026-11-22T11:36:24Z: "resumed after an interpreter outage: python3 was 3.10 for a while, now 3.13").

## What happened

During the finalize wait the session was resumed and `python3` changed from 3.13 to 3.10. The plan-marshall scripts need 3.11 or later (they import `datetime.UTC`), so every `.plan/execute-script.py` call failed until the interpreter was 3.13 again. No check named the cause: the failures looked like generic script errors.

## Candidate rule

`execute-script.py` checks `sys.version_info >= (3, 11)` before dispatching and, below that, fails with one structured error that names the required and the found version and the interpreter path. The marshall-steward health check gets the same check. Owning component: `plan-marshall:tools-script-executor`.
