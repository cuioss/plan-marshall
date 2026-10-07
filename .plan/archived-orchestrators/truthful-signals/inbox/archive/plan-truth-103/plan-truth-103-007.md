envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:07:40Z

# Candidate lesson: a guard whose matching SUBSTRATE differs from the defect's substrate publishes a confident clean negative

**Source plan**: plan-truth-103 (PR #1475, permission `Write(` vs `Edit(` grammar correction)
**Evidence**: first-party Q-Gate findings `2e01de` (6-finalize) and `a94e9b` (5-execute), both raised and resolved on this run.
**Dedup note**: this is NOT a re-file of either finding. It is the archetype the two of them share, which neither finding states on its own. It is also not one of the 10 findings already routed this run.

## Observation

Two independent guards on this run returned clean over a population they could not, by construction, see.

1. **`2e01de` — escaped-regex sweep vs unescaped prose.** The D0 outline gate swept for `Write\(` / `Edit\(` in *escaped* form to locate every matcher SITE, and it found every one of them. It was structurally blind to a DOCUMENTED OUTPUT in `tools-permission-doctor/SKILL.md:106` that depicted a matcher in *unescaped* prose (`Write(/tmp/**) | System temp access | medium`). The shipped detector could never emit that row — all 12 `SUSPICIOUS_PATTERNS` entries are `^Edit\(...\)$`-anchored, so no permission string beginning `Write(` matches any of them. The gate's sweep pattern and the defect's spelling differ **by construction**, so the gate's silence carried zero information about that class. The finding records this in its own words: "the sweep pattern and the defect's spelling differ by construction".

2. **`a94e9b` — raw text scan vs code/docstring distinction.** A delegation-boundary test asserted `'.claude/settings' not in permission_fix.py` source text. It fired. Triage was framed as "did the change breach the boundary, or did the constraint legitimately move?" — and the answer was neither. The single occurrence sat at line 165 inside the `resolve_settings_arg` **docstring**; every arm of that function returns a `permission_common` helper's value and constructs no path. The boundary was intact and had not moved. The DETECTOR was the defect: a raw substring scan over whole file text cannot distinguish a path a module RESOLVES from one its prose NAMES, so documenting the delegated resolver became indistinguishable from breaching it.

## The rule

Before trusting a guard's zero, ask **what substrate it matches on, and whether the defect can live in that substrate**. A guard matching escaped regex literals says nothing about prose. A guard matching raw file text says nothing about code-versus-docstring.

In both instances the correct fix was to **change the substrate, not the pattern**. `a94e9b` was fixed with a `_code_string_literals` AST helper narrowing the scan to non-docstring string literals, deliberately keeping BOTH original spellings as live arms so neither arm went vacuous — the old source-text pattern could never match a literal and would itself have become a vacuous guard. A matched 3-row control was added proving both inlined spellings still trip the guard and a docstring-only mention does not.

## Relation to the existing corpus

Adjacent to, but distinct from, the recorded vacuous-guard archetype ("every set-guarding detector must be population-derived — a check that can return 0 from an empty population MUST publish the population size"). Here the population is non-empty and correctly sized; the guard simply matches a **different substrate** than the one the defect occupies. Publishing a population count would not have caught either instance. If the orchestrator judges this a sub-case of the vacuous-guard family, the merge target is that lesson with this as a distinct recurrence arm — the diagnostic question ("what substrate?") is different from the existing one ("how big is the population?").
