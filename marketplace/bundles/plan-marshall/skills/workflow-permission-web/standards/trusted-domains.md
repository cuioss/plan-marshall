# Trusted Domains

Pre-approved domains for WebFetch operations that have passed security assessment.

> **Source of truth:** `domain-lists.json` is the sole source of truth for domain categorization used by `permission_web.py`. This document is a human-readable companion derived from that JSON file. When adding or removing domains, always update `domain-lists.json` first.

## Major Domains (Fully Trusted Documentation)

| Domain | Purpose |
|--------|---------|
| docs.anthropic.com | Claude API documentation |
| code.claude.com | Claude Code CLI documentation |
| www.anthropic.com | Anthropic company site |
| docs.oracle.com | Java API documentation, Java SE/EE specs |
| jakarta.ee | Jakarta EE specifications |
| docs.redhat.com | Red Hat product documentation |
| docs.spring.io | Spring Boot/Framework documentation |
| quarkus.io | Quarkus framework documentation |
| maven.apache.org | Apache Maven documentation |
| projectlombok.org | Lombok annotation library |
| junit.org | JUnit 5 testing framework |
| sonarcloud.io | Code quality analysis |
| docs.docker.com | Docker/containerization documentation |
| cheatsheetseries.owasp.org | OWASP security best practices |
| www.keycloak.org | Keycloak IAM documentation |
| docs.openrewrite.org | Automated code refactoring recipes |
| www.graalvm.org | GraalVM native image compilation |
| docs.github.com | GitHub Actions/API documentation |
| gist.github.com | GitHub Gist code snippets |
| raw.githubusercontent.com | GitHub raw content CDN |
| developer.mozilla.org | MDN Web Docs (HTML/CSS/JS reference) |
| www.w3.org | W3C web standards and specs |

## High-Reach Domains (Developer Platforms)

| Domain | Purpose | Trust |
|--------|---------|-------|
| github.com | Code hosting and collaboration | Full |
| stackoverflow.com | Developer Q&A | Full |
| ux.stackexchange.com | UX design Q&A | Full |
| medium.com | Technical articles and tutorials | Generally (verify author) |
| gitingest.com | Repository analysis tool | Generally |
| www.usertesting.com | UX research platform | Generally |
| www.llamaindex.ai | LlamaIndex LLM framework | Full |
| www.tabnine.com | AI code completion | Full |
| registry.npmjs.org | npm package registry API | Full |
| www.npmjs.com | npm package browser | Full |
| pypi.org | Python Package Index | Full |
| crates.io | Rust package registry | Full |
| docs.python.org | Python standard library docs | Full |
| rust-lang.org | Rust language documentation | Full |
| go.dev | Go language documentation | Full |
| kotlinlang.org | Kotlin language documentation | Full |
| typescriptlang.org | TypeScript documentation | Full |
| docs.rs | Rust crate documentation | Full |
| pkg.go.dev | Go package documentation | Full |
| learn.microsoft.com | Microsoft technical documentation | Full |
| cloud.google.com | Google Cloud documentation | Full |
| docs.aws.amazon.com | AWS documentation | Full |
| vercel.com | Frontend deployment platform | Full |
| netlify.com | Web deployment platform | Full |

## Selection Criteria

Domains on this list meet ALL of: valid HTTPS, no malware/phishing history, verifiable ownership, relevant to software development, actively maintained. For detailed assessment methodology, see [domain-security-assessment.md](domain-security-assessment.md).

## Usage Guidelines

- **Adding domains**: Update `domain-lists.json` first (JSON is source of truth), then update this table
- **Unknown domains**: Perform security assessment per [domain-security-assessment.md](domain-security-assessment.md)
- **Compromised domains**: Remove immediately from `domain-lists.json` and notify security team
- **Periodic review**: Check domains quarterly for security incidents, expired certs, or blocklist entries
