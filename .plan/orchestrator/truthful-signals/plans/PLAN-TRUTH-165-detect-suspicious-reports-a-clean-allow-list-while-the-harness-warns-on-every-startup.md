# PLAN-TRUTH-165: `detect-suspicious` reports a clean allow list while the harness warns about it on every startup

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from a self-filed orchestrator finding (`inbox/truthful-signals-011.md`), observed when
Claude Code's own startup warning flagged a permission rule in `.claude/settings.local.json` that
`permission_doctor detect-suspicious` had been reporting as clean the whole time the rule stood. The
offending rule was already fixed in place before this spec was staged (verified below) — **the single rule
is not the finding; the finding is that the tool calling it clean is the defect.**

## Objective

**`permission_doctor detect-suspicious` matches every allow rule against `SUSPICIOUS_PATTERNS` — roughly
twenty hand-maintained regexes, every one of which names a dangerous TARGET (`sudo`, `rm -rf`, `/tmp`
writes, unrestricted `curl`, …) — and has no family at all for malformed GRAMMAR: a rule whose `*`
wildcard spans an argument boundary and therefore silently pre-approves any option inserted there.**
`suspicious_count: 0` reads as "the allow list is sound"; it actually means "no rule matched twenty
hardcoded dangerous-target regexes" — a materially narrower claim than its consumers read it as. The
divergence was unusually sharp in the observed instance because a SECOND, independent instrument
(`claude_runtime.py`'s deny-rule renderer, via `_reject_unprotectable_path`) was simultaneously reporting
the opposite verdict on files containing the same class of hazard — the codebase already knows this
boundary rule and applies it only on the deny-rule side, never on the allow-rule inspector.

**What is NOT wrong, already checked so it is not re-derived.** None of plan-marshall's own rule generators
(`_default_permission_rules()`, `_render_permission_intent()`, `permission_fix.generate_wildcard()`) emit a
mid-command wildcard — every one places `*` at the tail or uses `:*`. The defect arrives through
operator-approved ad-hoc grants (the harness writes exactly the command approved, glob and all) that
`permission_fix add` then appends to `permissions.allow` with no grammar validation at all — only an
exact-duplicate check.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: confirm the population at HEAD.** Re-verify the specific rule that triggered this finding is
still fixed, re-sweep all live allow lists (`.claude/settings.local.json`, `.claude/settings.json`,
`~/.claude/settings.json`) for any remaining mid-command-wildcard rule, and confirm `SUSPICIOUS_PATTERNS`
still carries no grammar-validity family. Publish the population and its size, per this epic's standing
rule.

**D1 — Add a grammar-validity family to `detect-suspicious`.** Flag any allow rule whose `*` is followed
by further command text rather than terminating the rule or appearing as `:*` — the trailing and `:*` forms
are the only sanctioned ones, so the detector has a zero-false-positive shape. Report the new family's
count against the number of allow rules actually scanned and the settings files actually resolved (reusing
`detect-suspicious`'s existing `permissions_checked` discipline), so a zero distinguishes *looked, found
nothing* from *found no settings file*. Consider whether this belongs in `detect-suspicious` itself or a
sibling verb, so mixing "dangerous target" and "malformed rule" into one count does not itself blur a
signal.

**D2 — `permission_fix add` refuses or reports a malformed-grammar rule rather than appending it silently.**
Reuse the argument-boundary reasoning already written once, correctly, at `claude_runtime.py`'s
`_reject_unprotectable_path` — the boundary rule should have one home, not two absent ones.

**D3 — State the boundary rule in both grammar documents.** `plugin-architecture/references/
frontmatter-standards.md` § Permission Patterns and `plugin-script-architecture/references/
notation-spec.md` § Permission Pattern both teach the trailing-wildcard/`:*` forms without stating WHY the
wildcard belongs at the tail — nothing currently stops the next hand-written rule from putting one in the
middle.

## Claim Labels

- OBSERVED: the specific triggering rule (`Bash(cp -r .plan/project-architecture/* /tmp/arch-snap)`) is
  already fixed in `.claude/settings.local.json` to `Bash(cp -r .plan/project-architecture /tmp/arch-snap)`
  — re-verified first-party at staging via direct grep of the file.
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/analyze | rescoped: n/a | evidence: grep of .claude/settings.local.json line 11 confirms the exact-directory form, no wildcard, at current HEAD
- OBSERVED: `SUSPICIOUS_PATTERNS` in `tools-permission-doctor/scripts/permission_doctor.py` (~line 226) is
  a list of dangerous-target regexes (root access, `sudo`, etc.) — re-verified first-party at staging.
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/analyze | rescoped: n/a | evidence: read permission_doctor.py at line 226; SUSPICIOUS_PATTERNS opens with root_access-category dangerous-target entries, consistent with the finding's characterization
- OBSERVED: `claude_runtime.py`'s `_reject_unprotectable_path` refuses to render a deny rule for any path
  containing whitespace, with the argument-boundary reasoning stated in its own code comment — per the
  source finding, not independently re-read line-for-line at staging (verify-at-outline).
- ⚠ HYPOTHESIS: a full sweep of all three live allow lists (46 + 7 + 184 rules) finds no OTHER
  mid-command-wildcard rule beyond the one already fixed. ⛔ Reported by the source finding as already
  swept, but not independently re-run at staging. D0 re-confirms (verify-at-outline).
- ⚠ HYPOTHESIS: none of plan-marshall's own rule generators emit a mid-command wildcard. ⛔ Reported by
  the source finding as verified by reading each renderer; not independently re-read at staging
  (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py`
  — `SUSPICIOUS_PATTERNS` and `detect-suspicious` (D0, D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-permission-fix/**` — `permission_fix add`'s
  append path (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` —
  `_reject_unprotectable_path`, the argument-boundary reasoning D2 reuses (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md`
  — § Permission Patterns (D3)
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/references/notation-spec.md`
  — § Permission Pattern (D3)
- HYPOTHESIS: `test/plan-marshall/tools-permission-doctor/**`, `test/plan-marshall/tools-permission-fix/**`
  — coverage for D1/D2 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Secondary observation carried but NOT scoped into this spec's deliverables: the same allow list carries
  well-formed but unrestricted-execution rules (`Bash(python3 *)`, `Bash(python3:*)`,
  `Bash(env PM_ARGUMENT_NAMING_ENABLED=1 *)`) that `detect-suspicious` is also silent on — not a claim
  those rules are wrong, and whether a "breadth" family belongs alongside the "grammar" family added here
  is left as an open scoping question for whoever picks this up.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-165-detect-suspicious-reports-a-clean-allow-list-while-the-harness-warns-on-every-startup.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
