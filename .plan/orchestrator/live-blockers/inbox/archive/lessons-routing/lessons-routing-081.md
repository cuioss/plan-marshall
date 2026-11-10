envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:53Z

Severity: MEDIUM, domain content issue. Bundle: pm-dev-java (java-core). Checked at f6830b837.

The java-core guidance on converting an if/else chain over a closed constant set into a switch says the exhaustive switch needs no `default` and no trailing `throw`. It does not say that this holds only for a switch EXPRESSION or an enhanced switch with pattern/enum exhaustiveness. A constant-only switch STATEMENT is not exhaustiveness-checked and silently falls through for an unmatched value; removing the trailing `throw` turned a fail-closed authorization path into a fail-open one in the source lesson.

Ground-truth evidence:
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md:74-108`, section "From an if/else chain over a closed constant set": line 94 shows the after-form and says the trailing throw disappears; line 106 states "an exhaustive switch over an enum needs no `default`". Neither carries a caveat that a switch statement is not exhaustiveness-checked.
- A search of `pm-dev-java` and `pm-dev-java-cui` for "exhaustive", "enhanced switch" and "legacy switch" finds no such caveat.

Source lessons:
- API-Sheriff 2026-08-09-07-001

Full body: `lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/2026-08-09-07-001.md`
