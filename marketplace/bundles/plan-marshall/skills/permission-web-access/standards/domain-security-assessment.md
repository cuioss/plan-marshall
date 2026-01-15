# Domain Security Assessment

Security evaluation criteria and risk indicators for assessing domain trustworthiness when managing WebFetch permissions.

## Security Red Flags

### High-Risk Indicators

**Immediately Reject:**
- Domains known for malware, phishing, or spam distribution
- Newly registered domains (<30 days old) without verifiable ownership
- Domains with no HTTPS support
- Domains with expired or invalid SSL certificates
- Domains on known blocklists (URLhaus, PhishTank, Google Safe Browsing)
- Domains using URL shorteners (bit.ly, tinyurl, etc.) - verify destination first
- Domains with excessive redirects (>2 hops)
- Free hosting services (unless verified major provider like GitHub Pages, Netlify)

**Review Carefully:**
- Domains registered in high-risk TLDs (.tk, .ml, .ga, .cf, .gq)
- Domains with suspicious patterns (random characters, common typos of legitimate domains)
- Domains with no clear ownership information in WHOIS
- Domains with no web presence beyond the target resource
- Domains mixing unrelated content (e.g., finance + pharmaceuticals)

### Content-Based Risk Indicators

**Warning Signs:**
- Excessive advertising or pop-ups
- Requests for unnecessary permissions or personal information
- Pressure tactics (limited time offers, scarcity claims)
- Poor grammar, spelling, or unprofessional design
- Missing privacy policy or terms of service
- Broken links or non-functional features
- Content that contradicts established facts without credible sources

## Domain Research Methodology

### Step 1: Basic Verification

```
1. Check domain age: whois <domain> or https://whois.domaintools.com
2. Verify SSL certificate: Click padlock in browser or use SSL Labs
3. Check domain reputation:
   - Google Safe Browsing: https://transparencyreport.google.com/safe-browsing/search
   - VirusTotal: https://www.virustotal.com/gui/domain/<domain>
4. Review WHOIS information for ownership details
```

### Step 2: Content Assessment

```
1. Visit the domain and assess:
   - Professional appearance and functionality
   - Clear purpose and ownership information
   - Privacy policy and terms of service
   - Contact information (email, physical address)
   - About page with organizational details

2. Cross-reference information:
   - Verify company/organization exists independently
   - Check social media presence and activity
   - Search for reviews or discussions about the domain
   - Validate claimed credentials or certifications
```

### Step 3: Technical Analysis

```
1. Check HTTP headers for security features:
   - Strict-Transport-Security
   - Content-Security-Policy
   - X-Frame-Options
   - X-Content-Type-Options

2. Review domain history:
   - Archive.org Wayback Machine for historical snapshots
   - Any significant changes in content or ownership
   - Consistency in purpose and branding

3. Analyze network behavior:
   - External resources loaded (CDNs, analytics, ads)
   - Third-party cookies or trackers
   - Unexpected network requests
```

### Step 4: Reputation Research

```
1. Search for mentions and discussions:
   - "[domain] reviews"
   - "[domain] scam" or "[domain] fraud"
   - "[domain] security" or "[domain] malware"

2. Check security databases:
   - URLhaus: https://urlhaus.abuse.ch
   - PhishTank: https://phishtank.org
   - Spamhaus: https://www.spamhaus.org

3. Review community feedback:
   - Reddit, HackerNews, security forums
   - Industry-specific communities
   - Professional networks (LinkedIn, industry groups)
```

## Trust Levels

For the complete list of pre-approved trusted domains, see [trusted-domains.md](trusted-domains.md).

### Fully Trusted

Domains that have been comprehensively assessed and approved. Categories include:
- Major tech companies and platforms
- Established open-source foundations
- Government and educational institutions
- Official documentation sites for widely-used technologies
- Industry standards bodies

**See [trusted-domains.md](trusted-domains.md) for the authoritative list of approved domains with detailed justifications.**

### Generally Trusted (Verify First)
- Popular developer resources and blogs
- Open-source project hosting (GitHub, GitLab)
- Technical training platforms (Pluralsight, Udemy, Coursera)
- Cloud providers and SaaS platforms
- Security research firms
- Academic institutions and research papers

### Review Required
- Personal blogs (check author credentials)
- Smaller commercial sites
- Regional or specialized services
- New or emerging platforms
- Community-driven content sites
- Forums and discussion boards

### High Scrutiny
- Domains outside primary trust categories
- Sites requesting sensitive data
- Sites with commercial interests in recommendations
- Sites with aggressive monetization
- Sites lacking clear ownership

## Decision Framework

### Approve When:
1. Domain is on trusted domains list OR
2. All of the following are true:
   - No security red flags present
   - Clear legitimate purpose aligns with WebFetch use case
   - Verifiable ownership and professional presence
   - Positive or neutral reputation research
   - Technical security indicators are present

### Review/Defer When:
1. Domain is generally trusted but specific resource is questionable
2. Mixed signals from research (some positive, some concerning)
3. New domain but from established organization
4. Temporary security issues (expired cert, recent compromise)

### Reject When:
1. Any high-risk indicator present
2. Domain on blocklists or security databases
3. Evidence of malicious activity
4. Purpose does not justify WebFetch access
5. Unable to verify legitimacy despite research

## Special Cases

### GitHub User Content
- Trust: `raw.githubusercontent.com`, `gist.github.com`
- Review: User-specific repos (check repository legitimacy)
- Pattern: Verify repository ownership and activity

### Documentation Mirrors
- Prefer official sources over mirrors
- Verify mirror is authorized/recognized
- Check update frequency and accuracy

### API Endpoints
- Verify API belongs to trusted service
- Check authentication requirements
- Review API terms of service and rate limits

### CDN and Static Assets
- Trust major CDNs (CloudFlare, Akamai, Fastly)
- Verify assets belong to legitimate projects
- Check for integrity hashes when available

## Maintenance

For comprehensive maintenance procedures including adding domains, reviewing existing domains, and reporting issues, see [trusted-domains.md](trusted-domains.md#maintenance-procedures).

### Documentation
- Document reason for approval/rejection decisions
- Track special conditions or limitations
- Note expiration dates for temporary approvals
- Record review dates for periodic reassessment
