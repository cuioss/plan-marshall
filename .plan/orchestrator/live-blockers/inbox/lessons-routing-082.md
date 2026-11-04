envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T16:42:58Z

Severity: MEDIUM, domain content issue. Bundle: pm-documents (ref-asciidoc). Checked at f6830b837.

`verify-links` ignores `link:` macros and reports a clean pass. Its result carries no field naming the link classes it did not check, so `broken_links: 0` reads as full coverage when `link:` targets were never examined.

Ground-truth evidence:
- `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_verify_links.py:70`, `:82`, `:97` are the only link grammars scanned: `<<anchor>>`, `xref:` and the deprecated `<<file.adoc>>`. The only `link:` occurrence (`:48`) strips `link:https?://...` from a title and does not verify anything.
- The result payload (`_cmd_verify_links.py:225-242`) has no unchecked-class field.
- PLAN-LB-58 covers only the `.md` file-mode false pass (`_cmd_verify_links.py:192-197`), not `link:` macros inside `.adoc` files.

Source lessons:
- API-Sheriff 2026-08-09-07-007

Full body: `lessons-archive/filed-live-blockers/sweep-2026-11-02/API-Sheriff/2026-08-09-07-007.md`
