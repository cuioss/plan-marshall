envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:43:03Z

Severity: LOW (the second lesson could be argued medium), domain content issue. Bundle: pm-dev-java (java-security), secondary persona-security-expert secure-logging and pm-dev-java-cui cui-logging. Checked at f6830b837.

Two gaps in the secure-logging guidance. A masking helper redacts content but does not neutralise CR/LF or control characters, so a masked value can still forge log lines. And `\p{Cntrl}` matches only the ASCII control range, so C1 controls such as U+009B pass through silently; `Character.isISOControl` or an explicit C1 range is needed.

Ground-truth evidence:
- `marketplace/bundles/pm-dev-java/skills/java-security/standards/java-security-patterns.md:29-40`, "Masking Pattern": the example keeps the first three characters and logs them, with no warning that masking is not sanitising.
- `persona-security-expert` `secure-logging.md:55` lists only CR, LF, tab and delimiters to strip. A search for `javaISOControl`, `Cntrl` and C1 across `pm-dev-java`, `pm-dev-java-cui` and `persona-security-expert` finds nothing.
- `pm-dev-java-cui` `cui-logging` `logging-standards.md:292-312` covers the throwable and cause-chain channel only.
- Related earlier filing: lessons-routing-063 covers U+2028/U+2029 escape notation, a different subject. Fold this item into that fix or reference it when planning.

Source lessons:
- nifi-extensions 2026-09-04-11-001 (a masking helper is not a sanitizer)
- nifi-extensions 2026-09-04-11-002 (`\p{Cntrl}` is ASCII-only)

Full bodies: `lessons-archive/filed-live-blockers/sweep-2026-11-02/nifi-extensions/`
