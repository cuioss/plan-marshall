envelope_version=1
sender_type=plan
sender_id=rb-lb-59-skill-and-adr-resolution
epic=live-blockers
kind=landing
created=2026-10-19T21:06:16Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-59-skill-and-adr-resolution
epic=live-blockers
pr=#1821
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

guard: present

## 1. Deliverables

**D1 — Task skills are resolved for the task's module.** All Done-when met. Commit `ec4376957`, with review fixes in `137b8abff`, `4f08de720`, `a64ceb973`.

- *A Java module without CDI dependencies resolves no `java-cdi` / `java-quarkus` / `junit-weld-testing`* — met. `test_java_module_without_cdi_admits_no_cdi_optionals` (fail-first at `d17ac5bef`).
- *A module with CDI resolves `java-cdi`* — met. `test_java_module_with_cdi_admits_java_cdi`; the production signal is exercised by `test_discover_declared_dependencies_carry_the_cheap_pom_dependencies` plus `test_qualifies_optional_admits_cdi_skills_from_declared_dependency_objects` and `test_qualifies_optional_treats_quarkus_arc_as_a_cdi_signal`.
- *A repository exclusion removes a skill the module would otherwise get* — met. `test_repository_exclusion_removes_skill_the_module_would_get` (both notations) and `test_repository_exclusion_reads_the_real_config_reader` (real marshal.json reader path; fail-first at `d17ac5bef`).
- *An unreadable module yields defaults only* — met. `test_unreadable_module_admits_defaults_only_and_reports_it` and `test_cmd_resolve_reports_unreadable_module` (fail-first at `d17ac5bef`).
- *The first and fourth fail at `d17ac5bef`* — met as recorded in the progress file; the pre-fix run failed on the absent resolver API (the feature did not exist yet). Nuance recorded in Residue.

**D2 — ADR numbering and the scan see every ADR directory.** All Done-when met. Commit `4a2edc241`.

- *`doc/adr/a/0001-x.adoc` + `doc/adr/b/0001-y.adoc` → the scan reports the duplicate* — met. `test_scan_reports_duplicate_number_across_directories` (fail-first: `assert 'success' == 'error'` at `d17ac5bef`).
- *`next-number` in a tree whose highest ADR is in a subdirectory returns the next number after it* — met. `test_next_number_sees_highest_adr_in_subdirectory` (fail-first: `assert 1 == 8` at `d17ac5bef`).
- Finalize/pre-merge refusal — met without a gate change: the existing pre-merge ADR duplicate gate (`phase-6-finalize/standards/branch-cleanup.md`) already blocks on `duplicate_numbers`; the recursive scan now feeds it. Numbering scope (unique across the whole tree; per-directory deliberately not enabled) is recorded in `manage-adr/SKILL.md`.

## 2. Personas and skills

- Production code: `persona-implementer`; tests: `persona-module-tester`; every self-review round: `persona-code-reviewer`.
- Per deliverable: `skills: none named` (the spec declares no `Skills:`/`Persona:` lines).
- Skills added for surface drift: `extension-api`, `script-shared` (the `qualifies_optional` hook on `ExtensionBase`), `build-maven` (`declared_dependencies`), `manage-config` (config key + write path), `manage-architecture` (stale ADR path) — reason: the spec's Expected Surface marked the hook and tests as verify-at-outline hints; the Maven dependency signal was required for the CDI Done-when to hold in production.

## 3. Hypotheses

- *A repository-level skill exclusion has a home in `marshal.json` (`skill_domains` or the persona config)* — **refuted**: no such key or persona-config block existed (`.plan/marshal.json` L319-363). Added `skill_domains.{domain}.excluded_skills` with configure preservation and `set-inclusion --excluded-skills`.
- *The finalize ADR step (`adr-propose.md`) is where a duplicate refusal belongs* — **refuted**: `adr-propose` is advisory (`adr-propose.md` L18); the enforcement site already exists as the pre-merge ADR duplicate gate (`branch-cleanup.md` L1423-1456).

## 4. Findings

Self-review round 1: non-Java domains lost all optionals (blocking → fixed via `ExtensionBase.qualifies_optional` + Java override); `module_status` semantics (fixed); `excluded_skills` lifecycle/overclaim (fixed); exclusion fail-open (accepted: the same `load_config` gates the cell); per-cell discovery cost (fixed with process cache); multi-domain latent gap (accepted, no current trigger); stale `architecture-persistence.md` ADR path (fixed); a semantic edit rode a `chore(format)` commit (noted).

Self-review round 2: Maven's cheap crawl carries empty `dependencies`, so the positive CDI half never fired in production (blocking → fixed with `declared_dependencies` from the cheap POM parse); D1 fail-first evidence is AttributeError-shaped rather than behavioural (nuance recorded); `module_status`/phase-4 wording (fixed); `qualifies_optional`/`excluded_skills` docs and write path (fixed); exclusion reader tests (added); `applies_to_module` gate latent (accepted); CDI proxy for quarkus/weld (spec-mandated, accepted); stale progress file (fixed); nits addressed.

PR comments: CodeRabbit filed 3 findings — flat-domain `get` omitted `excluded_skills` (fixed), `io.quarkus:quarkus-arc` not recognised as CDI (fixed), gated set should be derived from declarations (fixed via `requires: cdi` / `requires: lombok`). All three threads replied to and resolved.

## 5. Reviewers

| Reviewer | Required | Result | Head reviewed | History |
|---|---|---|---|---|
| cuioss-review-bot | yes | reviewed | `a64ceb973` | triggered 19:41Z and again after the second push; both Guide comments updated until `a64ceb973`; review checks pass |
| coderabbit | yes (quota-limited) | reviewed an earlier head; refused current head on quota | `4f08de720` (current head `a64ceb973`) | reviewed 19:51Z with 3 findings, all fixed and resolved; re-triggered after the push at 20:10Z and refused ("review limit reached", next included review ~20:43Z) |
| sourcery | no (optional) | refused on quota | none | triggered 19:44Z; "review budget" refusal; not retriggered |

**Standing review authorization (CodeRabbit):** qualifying review exists on `4f08de720`; every finding from it is fixed in `a64ceb973` and its threads are resolved; it was re-triggered once after the last push and the refusal is recorded; every other gate condition holds on `a64ceb973` (cuioss reviewed it, all comments handled, verify green, CI green).

## 6. Operator questions

None asked.

## 7. Rule check

guard: present. The guard log `.plan/temp/guard.log` carries one line for this run: a self-review subagent ran `git ... diff ... | grep -n "^-"` (rule R1 — pipe), at line 148, session `ses_eaa800a11ffeZswg3oaaYwG2OK`. No other guard refusal is recorded for this run. No rule was knowingly broken in the implementation itself.

## 8. Residue

- D1's fail-first evidence is the pre-fix run failing because the module-aware resolver API did not exist yet, not a behavioural assertion against the old merge; the old code's unconditional optional merge is documented in the spec's OBSERVED labels and was replaced.
- `applies_to_module`/`qualifies_optional` still receive no domain key (latent only: no current multi-domain `ExtensionBase` implementor).
- `excluded_skills` is honoured by the `manage-personas` expansion path; the architecture-enrichment `skills_by_profile` path is deliberately unchanged (documented).
- Sourcery (optional) could not review because of its quota; it never gated the merge.
