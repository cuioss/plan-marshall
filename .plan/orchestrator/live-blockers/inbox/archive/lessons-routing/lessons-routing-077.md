envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:29Z

Severity: MEDIUM, domain content issue. Bundle: pm-dev-java (javadoc). Checked at f6830b837.

JavaDoc that restates a derivable count as a literal drifts from the declaring source, and JavaDoc that asserts a guard or sanitisation ordering the calling code does not have went unnoticed until an external review bot caught it. The javadoc skill's review rules have no rule for either.

Ground-truth evidence:
- `marketplace/bundles/pm-dev-java/skills/javadoc/SKILL.md:145-155` - the Review Rules block holds four rules (`@param`, `@throws`, a nullness/return claim, `{@link}`). None covers a restated count or an ordering/guard claim.
- A search of `pm-dev-java/skills/javadoc` for restated counts and ordering claims finds only `javadoc-method-documentation.md:38` (state ordering as a guarantee), which says nothing about verifying an ordering claim against the caller.
- The count-prose discipline exists only in `pm-plugin-development` plugin-doctor (`_analyze_literal_count.py`, `rule-catalog.md`), not for Java.

Source lessons:
- cui-http 2026-09-09-10-002 (preset count restated as a literal in Javadoc)
- cui-http 2026-09-15-19-002 (Javadoc asserted a guard/sanitisation ordering the caller does not have)
- cui-http 2026-10-04-06-008 (count-prose part only; its loop-back ceiling part worked as designed)

Full bodies: `lessons-archive/filed-live-blockers/sweep-2026-11-02/cui-http/`
