envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=process-compliance
kind=finding
created=2026-09-24T10:44:53Z
revision=4
amended=2026-09-24T14:27:05Z

# Process-rule issue: whole-tree quality-gate red on pristine main blocks every finalize

Reporter: plan `truth-179-opencode-target-detection-landed` at `default:pre-push-quality-gate`.

## Status: cache class fully closed; residual is 26 rule-side rows + 1 repo file

Cache backfill (operator-authorized, audited): 154/154 deployed `SKILL.md` files now carry
their tree twin's verbatim `mode:` line (151 in the first pass + 3 stragglers the first
predicate missed because it scanned whole files instead of frontmatter-only — fixed predicate,
re-run, applied). Bodies untouched. A re-sweep confirms the `skill-missing-mode` class is
gone from the deployed cache.

Residual red (gate still fails; step stays `failed`; loop stays halted before push):

- 26 × `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT`, error, all in tree
  `persona-plan-marshall-agent/standards/argument-naming.md`. Deliberately NOT edited:
  every flagged invocation demonstrably executes (this session ran them all day through the
  executor), the file is byte-identical to `origin/main`, and it is the canonical contract
  other phases consume — editing correct prose to satisfy a misreading rule would corrupt
  the system. The defect is in the rule's derivation/index layer in this environment
  (registry usable, `--help` probes healthy, derivation disk cache populated, yet zero
  shorthand resolutions). Owner: plugin-doctor rule maintainers.
- 1 × `skill-missing-mode` in repo-tracked worktree `.agents/skills/sync-antigravity/SKILL.md`.
  Not touched: the `mode:` value is an author decision with no tree twin to copy from.
  Owner: that skill's author.
- 53 × `lesson_id_in_skill_prose`, WARNING severity: reported only, non-blocking.

## Original evidence (retained)

- Whole-tree red reproduced on plan worktree (3x, incl. `--plan-id` routing and
  `--execution-mode in_process`) and pristine `origin/main` scratch worktree; per-bundle
  green; tree left clean every run. Wrapper yields zero parsed diagnostics throughout.
- CI stays green via fresh env (no stale cache) + `skip-on-docs-only`; the reusable
  workflow composition was never needed as an explanation.
- Durable follow-up stands: scope the gate's plugin-doctor invocation to tree sources so
  deployed-cache state can never red a source gate again.
