# Domain Security Assessment

Security evaluation criteria for assessing domain trustworthiness when managing WebFetch permissions.

## Quick Assessment Checklist

For routine domain categorization (most invocations):

1. **Check trusted lists** — Is the domain in `domain-lists.json`? If yes → approved.
2. **Check red flags** — Does the domain match any pattern in `domain-lists.json` red_flags? If yes → flag for review.
3. **Basic web search** — `WebSearch: "domain-name.com reputation security"`. Any malware/phishing reports? If yes → reject.
4. **Verify HTTPS** — Does the domain support HTTPS? If no → reject.
5. **Assess purpose** — Is the domain relevant to software development? If no → defer to user.

## Security Red Flags

### Immediately Reject

- Domains known for malware, phishing, or spam distribution
- Newly registered domains (<30 days old) without verifiable ownership
- No HTTPS support or expired/invalid SSL certificates
- Listed on blocklists (URLhaus, PhishTank, Google Safe Browsing)
- URL shorteners (bit.ly, tinyurl, etc.) — verify destination first
- Excessive redirects (>2 hops)

### Review Carefully

- High-risk TLDs (.tk, .ml, .ga, .cf, .gq)
- Suspicious patterns (random characters, typosquatting)
- No clear ownership in WHOIS
- No web presence beyond the target resource
- Mixing unrelated content

## Trust Levels

| Level | Criteria | Examples |
|-------|----------|---------|
| **Fully Trusted** | Major platforms, official docs, standards bodies | Oracle, Mozilla, Apache, GitHub |
| **Generally Trusted** | Popular developer resources, verify content quality | Medium, community blogs, SaaS platforms |
| **Review Required** | Personal blogs, smaller commercial sites, new platforms | Check author credentials, organizational backing |
| **High Scrutiny** | Outside primary categories, aggressive monetization, unclear ownership | Require explicit user approval |

See [trusted-domains.md](trusted-domains.md) for the complete list of pre-approved domains.

## Decision Framework

### Approve When

1. Domain is in `domain-lists.json`, OR
2. All of: no red flags, clear legitimate purpose, verifiable ownership, positive reputation, HTTPS with valid cert

### Review/Defer When

- Mixed signals from research
- New domain from established organization
- Temporary security issues (expired cert, recent compromise)

### Reject When

- Any high-risk indicator present
- Listed on blocklists or security databases
- Evidence of malicious activity
- Unable to verify legitimacy despite research

## Special Cases

- **GitHub user content**: Trust `raw.githubusercontent.com`, `gist.github.com`; verify repository legitimacy for user repos
- **Documentation mirrors**: Prefer official sources; verify mirror is authorized
- **API endpoints**: Verify API belongs to trusted service; check rate limits and ToS
- **CDN/static assets**: Trust major CDNs (CloudFlare, Akamai, Fastly); verify asset legitimacy
