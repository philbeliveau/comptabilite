---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/12-research-rbc-bank-connection-options-sec/12-RESEARCH.md
autonomous: true
requirements: [RESEARCH-RBC-CONN]

must_haves:
  truths:
    - "User understands all viable methods to connect to RBC for automated transaction data"
    - "User knows the security tradeoffs of each approach"
    - "User has a curated list of open-source projects and resources to evaluate"
    - "User can make an informed decision on which approach to pursue for their accounting stack"
  artifacts:
    - path: ".planning/quick/12-research-rbc-bank-connection-options-sec/12-RESEARCH.md"
      provides: "Comprehensive research document on RBC bank connection options"
      min_lines: 150
  key_links: []
---

<objective>
Research and document all viable options for connecting to RBC (Royal Bank of Canada) for automated/recurring transaction data uploads into the accounting system. Cover connection methods, security considerations, and open-source resources.

Purpose: The user needs to understand how to automate transaction imports from RBC into their Beancount-based accounting stack, what security guarantees each approach provides, and what existing open-source tooling is available.

Output: A comprehensive research document at `.planning/quick/12-research-rbc-bank-connection-options-sec/12-RESEARCH.md`
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Research RBC bank connection methods, security, and open-source ecosystem</name>
  <files>.planning/quick/12-research-rbc-bank-connection-options-sec/12-RESEARCH.md</files>
  <action>
Research and produce a comprehensive document covering these areas:

**1. Canadian Open Banking Landscape**
- Status of Canada's open banking / consumer-directed finance framework (expected timelines, current state as of early 2026)
- How this affects RBC specifically (any RBC open banking APIs, developer portals)
- Comparison with US/UK open banking maturity

**2. RBC-Specific Connection Methods**
Evaluate each method with pros, cons, security profile, and feasibility:

a) **Aggregator services (Plaid, Flinks, MX, Yodlee)**
   - Which aggregators support RBC? (Flinks is Canadian-founded, Plaid expanded to Canada)
   - How they connect (credential-sharing vs OAuth vs screen scraping)
   - Pricing tiers (free tier availability, developer plans)
   - Data freshness (real-time vs daily sync)
   - Reliability and breakage frequency with RBC

b) **OFX/QFX direct download from RBC Online Banking**
   - Manual export steps (RBC allows QFX/CSV download)
   - Can this be automated? (headless browser, RBC API endpoints)
   - File formats available and parsing considerations

c) **Screen scraping / headless browser automation**
   - Tools: Playwright, Puppeteer, Selenium
   - RBC's anti-scraping measures and TOS implications
   - Reliability concerns (UI changes break scrapers)

d) **RBC Developer/Partner APIs**
   - Any official RBC APIs for account data (research RBC's developer portal if one exists)
   - Partnership-only access vs public APIs

e) **Email/notification parsing**
   - RBC transaction alerts -> parse email for transaction data
   - Limitations (not all transactions, delayed)

f) **Manual CSV/OFX import (current baseline)**
   - Already supported in the accounting stack
   - Frequency and effort required

**3. Security Considerations**
For each connection method, evaluate:
- Credential exposure (who holds your banking credentials?)
- Data in transit (TLS, encryption)
- Data at rest (where is transaction data stored? local-only vs cloud?)
- Regulatory compliance (PIPEDA, Quebec privacy law)
- Token-based vs credential-based access
- Revocation capabilities (can you cut off access instantly?)
- What happens if the aggregator is breached?
- Best practices: read-only access, minimal scopes, local-first architecture, credential rotation
- How to architect the accounting stack to minimize attack surface (e.g., fetch data locally, never store credentials in cloud, use short-lived tokens)

**4. Open-Source Projects and Resources**
Research and list relevant projects:
- **ofxtools** (Python OFX parser)
- **beancount-import** / **smart_importer** for Beancount
- **plaid-python** / **plaid-node** SDKs
- **flinks** SDKs or community wrappers
- **ofxhome.com** (OFX server directory -- check RBC entry)
- **bank-connect** or similar OSS aggregator alternatives
- **weboob/woob** (French banking automation, may support Canadian banks)
- Any RBC-specific open-source importers on GitHub
- **beancount** community importers for Canadian banks
- Hledger CSV import rules for RBC format

**5. Recommended Approach**
Given the user's context (solo IT consultant, Beancount-based stack, security-conscious, Quebec-based):
- Rank approaches by feasibility, security, and maintenance burden
- Suggest a phased approach (e.g., start with manual OFX, add aggregator later when open banking matures)
- Note any approaches that are clearly not worth pursuing and why

Format the document with clear headers, comparison tables where appropriate, and actionable next steps.
  </action>
  <verify>
    The file `.planning/quick/12-research-rbc-bank-connection-options-sec/12-RESEARCH.md` exists, is at least 150 lines, and covers all 5 major sections (Canadian open banking, RBC connection methods, security, open-source projects, recommendations).
  </verify>
  <done>
    A comprehensive, well-structured research document exists that enables the user to make an informed decision about RBC bank connection strategy for their accounting stack. All connection methods are evaluated with security tradeoffs. Open-source resources are catalogued with links and descriptions.
  </done>
</task>

</tasks>

<verification>
- Document covers all 5 major research areas
- Each connection method has pros/cons/security assessment
- Open-source projects are listed with descriptions and relevance
- Recommendation section provides actionable guidance
- Content is specific to RBC and Canadian context (not generic)
</verification>

<success_criteria>
- Research document is comprehensive (150+ lines)
- User can identify which connection method to pursue
- Security implications are clearly articulated for each option
- Open-source resources are catalogued for implementation
</success_criteria>

<output>
After completion, create `.planning/quick/12-research-rbc-bank-connection-options-sec/12-SUMMARY.md`
</output>
