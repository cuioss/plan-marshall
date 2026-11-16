envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-16T07:45:22Z

# The documented OpenRewrite marker gate (`marker-detect`) has no caller in any phase or workflow

**Severity:** high (operator grade, 2026-11-16 `gather` run; the grading leaf had it medium, BORDERLINE medium/high)
**Bundle:** plan-marshall (gate wiring in phase-5 / phase-6) and `pm-dev-java-cui` (`search-markers`, the verb's implementation)
**Checked at:** `ee019bf1d` (origin/main)

## What was reported

TokenSheriff lesson `2026-10-31-12-008`: the `-Ppre-commit` OpenRewrite run injected a `/*TODO: Catch specific not RuntimeException. Suppress: // cui-rewrite:disable InvalidExceptionUsageRecipe*/` marker into a class (plan-02, PR #832) and it was committed. Nothing in the build or the early review rounds flagged it. Only the closing code-review round surfaced it, and it is still on main, where Sonar reports an open INFO `java:S1135` issue. The consumer's own `AGENTS.md` already says never to commit markers. The lesson asks that every marker be handled before the commit and that the diff be scanned for newly injected markers after every `-Ppre-commit` run, with the `search-markers` tooling.

## Ground truth at the checked commit

- `extension-api/standards/ext-point-domain-verb.md:110` describes `marker-detect` (`pm-dev-java-cui:search-markers`) as a domain-owned detector for a marker GATE: a project without the java-cui domain resolves the verb to null and "the marker gate simply does not run". `manage-config/standards/skill-domains.md:130` lists "marker-gate callers" as its consumers, and `build-maven/SKILL.md:78` says the tree-scan marker signal (`marker-detect`) is unchanged.
- A search of `marketplace/bundles/plan-marshall` and `.claude` for `marker-detect` and `search-markers` (markdown, python, json) matches only the verb declaration support code (`script-shared/.../extension_base.py`), the extension-api and manage-config standards, `build-maven/SKILL.md`, `marshall-steward/references/skill-domains-setup.md` and `manage-config` scripts. No file under `phase-5-execute`, `phase-6-finalize` or `execute-task` matches, and no workflow resolves the verb with `resolve-workflow-skill-extension --type marker-detect`. The grading leaf searched `doc/` too and found no caller. The documented gate has no wired caller.
- Per the leaf (not re-read): the declaration is at `pm-dev-java-cui/skills/plan-marshall-plugin/extension.py:112`; build output tagged `openrewrite_info` is classified acceptable at `script-shared/scripts/build/_warnings_classify.py:30`; and the consumer's `.plan/marshal.json:321` has the java-cui domain active, so the detector was available and unused.

## Not verified

- Whether a consumer project wires a marker step in its own `marshal.json`. The leaf grepped the TokenSheriff one for "marker" and found none.
- A call path through `.claude/` hooks or the generated executor was searched in the repository only.
- Whether the intended design is automatic invocation by verify/finalize (a real gap) or on-demand use only (documentation to correct). The grading leaf marked this as the deciding fact; the operator graded high.

## Source

- TokenSheriff lesson `2026-10-31-12-008`, archived verbatim at `lessons-routing/lessons-archive/filed-live-blockers/sweep-2026-11-16/TokenSheriff/2026-10-31-12-008.md`.
