envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:31Z

component=plan-marshall:build-maven
category=bug
created=2026-10-21
bundle=plan-marshall

# A whole-tree verify can exhaust the user's inotify watch pool and fail an unrelated test

A whole-tree reactor `verify` on a workstation whose editor/file-watcher already holds
inotify watches can exhaust `fs.inotify.max_user_watches`. The watch pool is per-UID, not
per-process, so the exhaustion surfaces inside whichever test first registers a
WatchService — here `SubprocessJobRunnerTest.escalated`, a test the change does not touch:

    org.opentest4j.AssertionFailedError:
    class java.io.IOException: User limit of inotify watches reached
        at sun.nio.fs.LinuxWatchService$Poller.implRegister

Observed in plan-91-plan-instance-advisories: the whole-tree `verify -Ppre-commit` run of
10:44Z failed with exactly that message (1 failure in 1560 tests, job
maven-2026-10-21-104417); the same tree went green (exit 0, 1654s, job 57cbf0ab) at
12:21:37Z after the watch-heavy scope was excluded and the run was given an explicit
2400s bound.

## Solution

Recognise the signature before touching the failing test: an `IOException: User limit of
inotify watches reached` raised from `LinuxWatchService` is an environment signal, not a
defect in the test that observed it. Confirm with `sysctl fs.inotify.max_user_watches`
and the editor's watch count, then exclude the watcher-heavy scope from the whole-tree
run (or raise the limit) rather than editing the unrelated test. Give the re-run an
explicit timeout above the failed run's duration: the first attempt consumed the default
bound, so the retry needs a wider one.

## Impact

Any whole-tree build on a developer machine running an editor that watches the
repository. The failure is misattributed by construction: it lands on whichever test
registers a watch first, which is why a green module build and a red whole-tree build can
both be correct.
