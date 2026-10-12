envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:08Z

# Candidate lesson: outline deliverable edits a package-info that names types only a later deliverable creates

Source: Q-Gate finding b0ad71 (phase 3-outline, resolved fixed in-run).

Deliverable 2 (no dependencies) rewrote `pm-runtime/.../runtime/start/package-info.java` to describe `ServiceManager` and `ServiceUnitInstaller`, which only deliverable 3 creates. Any `{@link}` to them would fail deliverable 2's own verification (`test -pl pm-runtime -am`), because the referenced types do not exist yet at that point.

Fix applied: the package-info edit moved into deliverable 3, so the Javadoc is written once after every type it names exists.

Candidate rule: when the outline splits a package across deliverables, put the `package-info.java` edit in the LAST deliverable that adds a type to that package (or restrict earlier text to types already present). Javadoc links are compile-time references and fall under the deliverable ordering too.

Scope hint for classification: Java-domain outline authoring (phase-3-outline deep lane); likely generic, not project-specific.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-04-service-unit-001.md` from plan plan-04-service-unit (PLAN-04, #25)
