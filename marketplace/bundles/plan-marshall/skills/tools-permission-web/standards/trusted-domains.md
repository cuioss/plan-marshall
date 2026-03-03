# Trusted Domains

Pre-approved domains for WebFetch operations that have passed comprehensive security assessment and meet CUI trust criteria.

## Purpose

This document provides a curated list of domains that are pre-approved for WebFetch operations in CUI projects. These domains have been evaluated against security criteria defined in [domain-security-assessment.md](domain-security-assessment.md) and deemed safe for automated web fetching operations.

**When to use this list:**
- Before requesting WebFetch permissions for a domain, check if it's already trusted
- When reviewing pull requests that add WebFetch permissions
- During security audits of project permissions

**When additional review is needed:**
- If the specific URL path on a trusted domain seems suspicious
- If the trusted domain has been compromised (check security news)
- If fetching sensitive or dynamic content (API endpoints, user data)

## Selection Criteria

Domains on this list meet ALL of the following criteria:

1. **Security**
   - Valid HTTPS with up-to-date SSL certificate
   - No history of malware, phishing, or security incidents
   - Not listed on security blocklists (URLhaus, PhishTank, Google Safe Browsing)
   - Implements security headers (HSTS, CSP)

2. **Reputation**
   - Established presence (domain age >1 year for non-major companies)
   - Verifiable ownership by reputable organization
   - Positive community reputation
   - Professional web presence with clear purpose

3. **Relevance**
   - Provides documentation, tools, or resources relevant to software development
   - Commonly used by development community
   - Maintains stable, reliable content

4. **Maintenance**
   - Active updates and maintenance
   - Responsive to security issues
   - Clear content governance

For detailed security assessment methodology, see [domain-security-assessment.md](domain-security-assessment.md).

## Trusted Domains List

Domains in this list are classified by trust level (Fully Trusted, Generally Trusted, Review Required, High Scrutiny). For complete trust level definitions, decision framework, and assessment criteria, see **[domain-security-assessment.md](domain-security-assessment.md#trust-levels)**.

### AI and Claude Documentation

First-party and official Claude/Anthropic documentation:

- **docs.anthropic.com** - Claude AI documentation
  - Purpose: Claude API, Claude Code documentation
  - Trust Level: Fully Trusted (First-party documentation)

- **code.claude.com** - Claude Code documentation
  - Purpose: Claude Code CLI documentation, guides
  - Trust Level: Fully Trusted (First-party documentation)

- **www.anthropic.com** - Anthropic company site
  - Purpose: Claude announcements, company information
  - Trust Level: Fully Trusted (First-party documentation)

### Java and Jakarta EE Documentation

Official Java, Jakarta EE, and related specifications:

- **docs.oracle.com** - Oracle Java documentation
  - Purpose: Java API documentation, Java SE/EE specs
  - Trust Level: Fully Trusted (Official Java documentation)

- **jakarta.ee** - Jakarta EE specifications
  - Purpose: Jakarta EE specifications, API documentation
  - Trust Level: Fully Trusted (Eclipse Foundation/Official specs)

- **docs.redhat.com** - Red Hat documentation
  - Purpose: Red Hat product documentation, guides
  - Trust Level: Fully Trusted (Major enterprise vendor)

### Frameworks and Build Tools

Spring, Quarkus, Maven, and related framework documentation:

- **docs.spring.io** - Spring Framework documentation
  - Purpose: Spring Boot, Spring Framework docs
  - Trust Level: Fully Trusted (Official framework documentation)

- **quarkus.io** - Quarkus Framework
  - Purpose: Quarkus documentation and guides
  - Trust Level: Fully Trusted (Red Hat/Open Source)

- **maven.apache.org** - Apache Maven
  - Purpose: Maven documentation, plugin repository
  - Trust Level: Fully Trusted (Apache Foundation)

- **projectlombok.org** - Project Lombok
  - Purpose: Lombok annotation library documentation
  - Trust Level: Fully Trusted (Established open source project)

### Testing and Code Quality

Testing frameworks and code analysis tools:

- **junit.org** - JUnit Testing Framework
  - Purpose: JUnit 5 documentation
  - Trust Level: Fully Trusted (Established testing framework)

- **sonarcloud.io** - SonarCloud code analysis
  - Purpose: Code quality analysis, security scanning
  - Trust Level: Fully Trusted (SonarSource/Established tool)

### DevOps and Containerization

Docker, infrastructure, and deployment documentation:

- **docs.docker.com** - Docker documentation
  - Purpose: Docker, containerization documentation
  - Trust Level: Fully Trusted (Official Docker docs)

### Security and Standards

Security resources and standards organizations:

- **cheatsheetseries.owasp.org** - OWASP Cheat Sheet Series
  - Purpose: Security best practices, guidelines
  - Trust Level: Fully Trusted (OWASP Foundation)

- **www.keycloak.org** - Keycloak authentication
  - Purpose: Keycloak identity and access management documentation
  - Trust Level: Fully Trusted (Red Hat/CNCF project)

### AI and ML Tools

AI/ML platforms and tools documentation:

- **www.llamaindex.ai** - LlamaIndex documentation
  - Purpose: LlamaIndex framework for LLM applications
  - Trust Level: Fully Trusted (Established AI framework)

- **www.tabnine.com** - Tabnine AI code completion
  - Purpose: AI-powered code completion documentation
  - Trust Level: Fully Trusted (Established AI tool)

### Code Hosting and Collaboration

GitHub and related code hosting platforms:

- **github.com** - Code hosting and collaboration
  - Purpose: Repository browsing, issue tracking, releases
  - Trust Level: Fully Trusted (Major platform)
  - Note: Verify specific repository authenticity

- **docs.github.com** - GitHub documentation
  - Purpose: Git, GitHub Actions, API documentation
  - Trust Level: Fully Trusted (Major tech company)

- **gist.github.com** - GitHub Gist
  - Purpose: Code snippets, sharing
  - Trust Level: Fully Trusted (GitHub platform)

- **raw.githubusercontent.com** - GitHub raw content
  - Purpose: Direct file access from repositories
  - Trust Level: Fully Trusted (GitHub CDN)
  - Note: Verify repository authenticity before fetching

- **gitingest.com** - Repository analysis tool
  - Purpose: Repository structure visualization
  - Trust Level: Generally Trusted (Third-party GitHub tool)

### Code Migration and Refactoring

OpenRewrite and code transformation tools:

- **docs.openrewrite.org** - OpenRewrite documentation
  - Purpose: Automated code refactoring recipes
  - Trust Level: Fully Trusted (Moderne/Open source)

### GraalVM and Native Compilation

GraalVM native image and JIT compilation:

- **www.graalvm.org** - GraalVM documentation
  - Purpose: GraalVM, native image compilation
  - Trust Level: Fully Trusted (Oracle/Open source)

### Developer Communities

Platforms for developer knowledge sharing:

- **stackoverflow.com** - Developer Q&A
  - Purpose: Programming questions and answers
  - Trust Level: Fully Trusted (Stack Exchange network)

- **ux.stackexchange.com** - UX Stack Exchange
  - Purpose: User experience design Q&A
  - Trust Level: Fully Trusted (Stack Exchange network)

- **medium.com** - Technical articles and tutorials
  - Purpose: Developer blogs, technical articles
  - Trust Level: Generally Trusted
  - Note: Verify author reputation for critical information

### UX and Design

User experience and usability resources:

- **www.usertesting.com** - User testing platform
  - Purpose: UX research, usability testing
  - Trust Level: Generally Trusted (Established UX platform)

## Usage Guidelines

### For Developers

When adding WebFetch permissions to a project:

1. **Check this list first** - If domain is listed, reference this document in PR description
2. **If not listed** - Perform security assessment using [domain-security-assessment.md](domain-security-assessment.md)
3. **Document justification** - Explain why domain access is needed
4. **Use specific paths** - Prefer specific path patterns over domain wildcards when possible

### For Code Reviewers

When reviewing WebFetch permission requests:

1. **Verify against trusted list** - Trusted domains should be approved quickly
2. **For new domains** - Ensure proper security assessment was performed
3. **Check for alternatives** - Can a trusted domain be used instead?
4. **Validate scope** - Ensure permissions are as narrow as possible

## Maintenance Procedures

### Adding New Domains

To add a domain to this trusted list:

1. **Perform comprehensive assessment** using [domain-security-assessment.md](domain-security-assessment.md)
2. **Document findings** including:
   - Security verification results (SSL, blocklists, reputation)
   - Ownership and organizational details
   - Relevance to development workflows
   - Trust level designation
3. **Submit PR** with domain addition and assessment documentation
4. **Require security review** - Changes to this list need approval from security stakeholders

### Reviewing Existing Domains

Periodically review trusted domains (recommended: quarterly):

1. **Check for security incidents** - Search for "[domain] security breach" or "[domain] compromised"
2. **Verify SSL certificate** - Ensure valid and up-to-date
3. **Review blocklist status** - Check Google Safe Browsing, VirusTotal
4. **Assess continued relevance** - Is domain still actively maintained and used?
5. **Remove or downgrade** if domain no longer meets criteria

### Reporting Issues

If you discover a security issue with a trusted domain:

1. **Immediately notify security team** - Don't wait for scheduled review
2. **Document the issue** - Include evidence and impact assessment
3. **Submit PR to remove or downgrade** domain from trusted list
4. **Update affected projects** - Review projects using the domain

## Risk Mitigation

Even for trusted domains, implement defense-in-depth:

1. **Validate responses** - Check content type, size, format before processing
2. **Sanitize content** - Don't blindly execute or render fetched content
3. **Handle errors gracefully** - Don't expose internal details in error messages
4. **Log access** - Monitor WebFetch usage for anomalies
5. **Rate limit** - Implement reasonable rate limits to prevent abuse

## Related Standards

- [domain-security-assessment.md](domain-security-assessment.md) - Comprehensive security assessment methodology
- See permission-management standards in the plan-marshall bundle for WebFetch permission validation patterns
