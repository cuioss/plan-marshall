# PLAN-02: marshalld registration scope population — daemon registered but inert

epic: plan-server
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.

## Objective

The shipped Rung 2 daemon (`marshalld`, PR #933) runs but is **inert**: the meta-project registered
2026-07-18 with empty `worktree_containers` and empty `notation_allowlist`, so the daemon has no
scope to intercept any build, and every plan build (plan-optimization PLAN-11/12/14/15 and earlier)
ran inline. The spec required `notation_allowlist` to *default to the build/test job kinds* and the
registration to carry the worktree container path(s); an empty registration means that population
never happened. Fix the register/enable path so a registered project's builds are actually routed to
the daemon, and add the end-to-end positive-routing coverage that would have caught this.

## Verified ground truth (2026-07-19)

- `~/.plan-marshall/marshalld/registry.json` → `/Users/oliver/git/plan-marshall` registered
  `2026-07-18T21:45:41Z`, `worktree_containers: []`, `notation_allowlist: []`.
- `~/.plan-marshall/marshalld/job-logs/` → empty (zero jobs ever dispatched).
- Daemon alive — PID 6973, python.org `/Library/Frameworks/Python.framework/3.14` build (NOT the
  Homebrew x86_64 Cellar python from the unrelated 07-19 crash report).
- `registry-audit.log` → single `register` with empty containers/allowlist; nothing since.
- Distinct/NOT the cause (do not conflate): `~/.plan-marshall/build-queue.json` is the Rung-1
  manage-locks FIFO and is working (run_log populated); only the marshalld job-dispatch side is inert.

## Deliverables

1. **Root-cause the empty-scope registration.** Trace the register/enable path that writes
   `registry.json` (`manage-build-server` register verb, and the `phase-1-init` preflight /
   steward enable path if it participates): determine whether population of `worktree_containers` /
   `notation_allowlist` is missing, gated, or expected from a later step that never fires. Do not
   pre-decide — the outline confirms which surface owns the write.
2. **Populate the two fields at registration.** `notation_allowlist` defaults to the build/test job
   kinds (per spec); `worktree_containers` includes the canonical worktree container (e.g.
   `{root}/.plan/local/worktrees/`). Empty-scope registration becomes impossible or is explicitly
   rejected with a named reason.
3. **Repair the existing inert registration.** A re-register / migration path so the already-written
   empty entry for `/Users/oliver/git/plan-marshall` becomes functional without hand-editing
   `registry.json` (the daemon owns its state; per Rung-1 discipline, no direct file surgery).
4. **Positive-routing acceptance test.** A registered project that runs a build actually dispatches a
   job to the daemon (`job-logs/` non-empty; the routed build produces the same result TOON as the
   inline path). This is the coverage gap: the original suite exercised unregistered ⇒ byte-identical
   and refusal paths, but not registered ⇒ job-actually-routed end-to-end.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-build-server/**` (register/enable verb + scripts)
- `marketplace/bundles/plan-marshall/skills/phase-1-init/**` (preflight, if it participates in enable)
- the daemon-side routing/verify path in `manage-build-server/scripts/marshalld.py` (scope check)
- `build-server-client` skill routing decision (does notation reach the daemon), if implicated
- tests for the above

## Dependencies and Sequencing

- Depends on: none (Rung 2 shipped; this fixes it in place).
- Overlaps with: none currently staged — only active plan in the reopened epic.

## Hand-Off Command

```text
/plan-marshall task="Fix marshalld registered-but-inert: the manage-build-server register/enable path writes registry.json with empty worktree_containers and empty notation_allowlist, so the daemon never intercepts any build and all plan builds run inline. Root-cause and fix the register/enable path to populate notation_allowlist (default build/test job kinds) and worktree_containers (canonical worktree container); provide a re-register/migration path to repair the existing empty entry for /Users/oliver/git/plan-marshall without hand-editing registry.json; and add a positive-routing acceptance test that a registered project's build is actually dispatched to the daemon (job-logs non-empty, routed result TOON matches inline). Spec: .plan/local/orchestrator/plan-server/plans/PLAN-02-registration-scope-population.md"
```

## Status Trail

- plan_marshall_plan_id: marshalld-registration-scope-population (RUNNING — worktree live at .plan/local/worktrees/marshalld-registration-scope-population, 2026-07-19)
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-02.md}
