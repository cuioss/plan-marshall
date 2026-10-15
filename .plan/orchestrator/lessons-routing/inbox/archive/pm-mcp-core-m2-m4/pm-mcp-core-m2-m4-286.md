envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T08:52:28Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-24-plan-instance (PLAN-24, pm-mcp-core #67, merged 2ebec2a), drained 2026-10-15.
> Source: pm-mcp-core local lesson 2026-10-15-07-002 (the plan sent no candidate-lesson message).
> RECURRENCE of -281 (build-wrapper timeout). New evidence: a dispatched phase-5-execute leaf (TASK-20 envelope) ran a whole-tree `verify -Ppre-commit` synchronously, hit the 590 s Bash cap, and returned nothing usable; the rerun in the background took about 9.5 minutes. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# A whole-tree verify -Ppre-commit inside a leaf hit the 590s cap and had to be rerun in the background

- Component: pm-mcp-core (build gates); process: plan-marshall:phase-5-execute
- Suggested category: improvement
- Signal: plan-24-plan-instance, TASK-20 envelope

## Observation

A whole-tree `verify -Ppre-commit` ran synchronously inside a dispatched leaf (the TASK-20 envelope) and hit
the 590 second cap of the Bash tool. The run was cut off, and the orchestrator had to rerun the gate in the
background, where it took about 9.5 minutes. The leaf had spent its budget and returned nothing usable.

The gate rewrites files (licence headers, OpenRewrite recipes, import order) over every module, so its
duration grows with the tree, not with the size of the task. A task that touches one module can still pay for
the whole tree.

## Suggested correction

- A leaf does not run the whole-tree quality gate. Inside a task, run the bounded form: `test -pl {module} -am`
  for the module that changed, or `verify -Ppre-commit -pl {module} -am` where a module-scoped gate is enough.
- The whole-tree `verify -Ppre-commit` belongs to the orchestrator. It runs it as a background, result-bearing
  task and reads the TOON result when it exits.
- When a leaf does hit the cap, it returns control with a clear signal ("whole-tree gate not run within the
  cap") instead of retrying in the same envelope.
- Plan the long gate as its own step, so the task that needs it is not the one that times out.
