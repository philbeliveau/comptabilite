# RBC Bank Connection Options: Research Document

**Date:** 2026-02-26
**Context:** Solo IT consultant in Quebec, Beancount-based accounting stack, security-conscious, seeking automated transaction import from RBC.

---

## 1. Canadian Open Banking Landscape

### 1.1 Consumer-Directed Finance (CDF) Framework

Canada's open banking initiative, rebranded as **Consumer-Directed Finance (CDF)**, has been progressing slowly compared to the UK and EU:

| Milestone | Status |
|-----------|--------|
| Advisory Committee on Open Banking report | Published June 2021 |
| Abraham report: "Final Report of the Advisory Committee on Open Banking" | Published August 2021 |
| Budget 2022 commitment to open banking framework | Announced April 2022 |
| Abraham appointed as Open Banking Lead | September 2022 |
| Consumer-Directed Finance Framework consultation paper | Published January 2023 |
| Fall Economic Statement 2023: legislation promised | November 2023 |
| Budget 2024: commitment to CDF legislation in 2025 | April 2024 |
| CDF legislation tabled (Bill C-365, *Consumer-Directed Finance Act*) | Tabled fall 2024 |
| Expected initial implementation (Phase 1: banking data) | Targeted 2026-2027 |

**Current state (early 2026):** The Consumer-Directed Finance Act has been tabled. Phase 1 is expected to cover read-only access to deposit and credit card account data. The Financial Consumer Agency of Canada (FCAC) is expected to be the regulator. However, royal assent, regulatory rule-making, and bank compliance timelines mean practical API access is unlikely before late 2026 at the earliest.

### 1.2 How This Affects RBC

RBC is one of Canada's Big Five banks and has participated in CDF consultations. Key observations:

- **No public developer API** as of early 2026. RBC does not offer an open banking API, developer portal, or partner sandbox for account data access.
- RBC has existing integrations with select aggregators (Plaid, Flinks) but these use credential-sharing, not OAuth-based access.
- When CDF Phase 1 launches, RBC will be required to provide standardized API access. This will be the cleanest long-term solution.
- RBC has an **API marketplace** (developer.rbc.com) but it focuses on payment initiation (e.g., PayEdge) and business banking APIs, not personal account data export.

### 1.3 Comparison with UK/US/EU

| Region | Open Banking Status | Practical API Access |
|--------|-------------------|---------------------|
| **UK** | Fully implemented since 2018 (CMA order). 9 largest banks. | Mature. Free standardized APIs via Open Banking Implementation Entity (OBIE). |
| **EU** | PSD2 in effect since 2019. PSD3 proposed. | Mature. Banks must provide APIs. AISPs (Account Information Service Providers) regulated. |
| **US** | CFPB Section 1033 rule finalized October 2024. | Transitioning. Large banks must comply by April 2026. Aggregators already widespread. |
| **Australia** | Consumer Data Right (CDR) live since 2020 for banking. | Mature for Big Four banks. |
| **Canada** | CDF legislation tabled. Phase 1 targeted 2026-2027. | **Not yet available.** Credential-sharing aggregation remains the norm. |

**Key takeaway:** Canada is 5-8 years behind the UK and at least 2 years behind the US. Until CDF is implemented, all RBC connection methods involve either credential-sharing aggregation, manual file export, or scraping.

---

## 2. RBC-Specific Connection Methods

### 2a. Aggregator Services (Plaid, Flinks, MX, Yodlee)

#### Plaid

- **RBC support:** Yes. Plaid supports RBC personal and business accounts in Canada.
- **Connection method:** Credential-sharing (user enters RBC online banking username/password in Plaid Link widget). No OAuth -- RBC does not support Plaid's OAuth flow.
- **Data available:** Transactions (up to 24 months history), balances, account details, identity.
- **Data freshness:** Near real-time for balances; transactions typically refreshed every few hours to daily.
- **Reliability with RBC:** Generally stable but subject to breakage when RBC changes login flows, adds new MFA steps, or modifies their web portal. Plaid maintains the connection but outages of 1-7 days occur periodically.
- **Pricing:**
  - Free tier: Plaid offers a sandbox and a limited free tier (100 items in development) via their developer dashboard.
  - Production: Pay-per-item pricing. For a single personal use case, costs are negligible (~$0.30/item/month for Transactions product).
  - Plaid launched "Plaid for Personal Use" (consumer data access) but availability in Canada is uncertain.
- **SDK:** `plaid-python` (official), `plaid-node`. Well-documented REST API.
- **Canadian considerations:** Plaid's Canadian entity is regulated. Data may be stored in US data centers unless Canadian residency is specifically negotiated.

#### Flinks

- **RBC support:** Yes. Flinks is Canadian-founded (Montreal) and has strong RBC support.
- **Connection method:** Credential-sharing via Flinks Connect widget. Similar to Plaid. No OAuth for RBC.
- **Data available:** Transactions, balances, account details, statements (PDF retrieval for some banks).
- **Data freshness:** Configurable refresh. Typically daily or on-demand.
- **Reliability with RBC:** Flinks specializes in Canadian banks and has historically had strong RBC reliability. Still subject to the same credential-sharing breakage risks.
- **Pricing:**
  - Developer sandbox available.
  - Production pricing is custom/quote-based. Historically more expensive than Plaid for small scale.
  - Flinks was acquired by National Bank of Canada's venture arm, which may influence pricing and priorities.
- **SDK:** REST API. No official Python SDK, but straightforward HTTP integration. Community wrappers exist.
- **Canadian considerations:** Data stored in Canada (AWS ca-central-1). Subject to PIPEDA. This is a significant advantage over US-based aggregators.

#### MX (formerly MX Technologies)

- **RBC support:** Yes, via their data aggregation platform.
- **Connection method:** Credential-sharing.
- **Pricing:** Enterprise-focused. Not practical for a solo developer.
- **Relevance:** Low for this use case. MX targets financial institutions and fintech companies, not individual developers.

#### Yodlee (Envestnet)

- **RBC support:** Yes. Yodlee was one of the earliest aggregators with Canadian bank support.
- **Connection method:** Screen scraping / credential-sharing.
- **Pricing:** Enterprise-focused. Minimum commitments. Not practical for individual use.
- **Relevance:** Low. Yodlee's developer program has been deprioritized in favor of enterprise clients.

#### Aggregator Comparison

| Factor | Plaid | Flinks | MX | Yodlee |
|--------|-------|--------|-----|--------|
| RBC support | Yes | Yes | Yes | Yes |
| Connection type | Credential-sharing | Credential-sharing | Credential-sharing | Screen scraping |
| Data in Canada | No (US default) | Yes (ca-central-1) | No | No |
| Developer-friendly | High | Medium | Low | Low |
| Pricing for solo use | Low (~$5/mo) | Quote-based | Enterprise | Enterprise |
| Python SDK | Official | Community | N/A | Deprecated |
| Recommended | **Yes** | **Yes** | No | No |

### 2b. OFX/QFX Direct Download from RBC Online Banking

#### Manual Export

RBC Online Banking supports manual transaction download:

- **Formats available:** QFX (Quicken), CSV, Microsoft Money (.ofx)
- **Access:** Online Banking > Account > Download Transactions
- **Date range:** Typically up to 18 months of history
- **Frequency:** Can be done as often as needed

#### OFX Direct Connect

- RBC historically supported OFX Direct Connect (used by Quicken, Microsoft Money).
- **OFX server information** (from ofxhome.com):
  - Institution: Royal Bank of Canada
  - OFX URL: Varies; RBC has used `https://www1.royalbank.com/cgi-bin/rbaccess/rbunxcgi?F6=1&F7=IB&F21=IB&F22=IB&REQUEST=` (historical, may be outdated)
  - FI Org: RBC
  - FI ID: 900000100
- **Automation potential:** OFX Direct Connect uses HTTP POST with OFX-formatted XML. In theory, you could script requests using `ofxtools` or `ofxget`. However:
  - RBC may have deprecated OFX Direct Connect endpoints.
  - Authentication is username/password-based, and MFA (security questions, 2FA) complicates automation.
  - RBC's OFX endpoint status should be tested empirically.

#### Can Manual Export Be Automated?

- **Headless browser:** Theoretically possible (see section 2c) but fragile.
- **Scheduled download:** Not supported natively by RBC. No recurring export feature.
- **RBC mobile API:** The RBC mobile app uses undocumented APIs. Some reverse-engineering projects exist but using them violates RBC's terms of service and risks account lockout.

### 2c. Screen Scraping / Headless Browser Automation

#### Technical Approach

- Use Playwright, Puppeteer, or Selenium to automate the RBC Online Banking login and transaction download flow.
- Steps: Navigate to login > enter credentials > handle MFA > navigate to account > download transactions as CSV/QFX.

#### Challenges

| Challenge | Severity | Notes |
|-----------|----------|-------|
| RBC anti-bot measures | High | RBC uses device fingerprinting, behavioral analysis, and may challenge with CAPTCHAs |
| MFA/2FA | High | RBC requires security questions and increasingly SMS/push verification |
| UI changes | Medium | RBC redesigns their online banking interface periodically, breaking scrapers |
| TOS violation | High | RBC's Terms of Service explicitly prohibit automated access |
| Account lockout risk | High | Repeated automated login attempts may trigger account lockout |
| Session management | Medium | Sessions expire; must handle re-authentication |

#### Tools

- **Playwright** (recommended if scraping): Best cross-browser support, async Python API, stealth plugins available.
- **Puppeteer:** Node.js focused, good but Playwright is generally preferred now.
- **Selenium:** Mature but heavier. Less suited to modern dynamic sites.

#### Verdict

**Not recommended** for production use. The combination of TOS violation, account lockout risk, and maintenance burden makes this approach impractical. Only consider as a last resort for prototyping.

### 2d. RBC Developer/Partner APIs

- **RBC API Marketplace** (developer.rbc.com): Exists but focuses on:
  - PayEdge (B2B payments)
  - Treasury and cash management APIs
  - Commercial/business banking APIs
- **Personal account data API:** Does not exist publicly.
- **Partner access:** Some fintech partners (e.g., Wealthsimple, for direct deposit) have private API integrations with RBC, but these are NDA-protected, enterprise-scale partnerships.
- **Future:** When CDF is implemented, RBC will be required to provide a standardized consumer data API. This is the most promising long-term path but not available today.

### 2e. Email/Notification Parsing

#### Approach

- Enable RBC transaction alerts (email or push notifications).
- Parse incoming emails for transaction details.
- Extract: date, amount, merchant, account.

#### Implementation

- Use IMAP to fetch RBC alert emails.
- Parse with regex or structured extraction (RBC alert emails have a consistent format).
- Map extracted data to Beancount transactions.

#### Limitations

| Limitation | Impact |
|------------|--------|
| Not all transactions trigger alerts | High -- only debit/credit above threshold, or specific types |
| Delayed delivery | Medium -- emails may arrive minutes to hours after transaction |
| No historical data | High -- only going forward, no backfill |
| Limited detail | Medium -- no category, limited merchant info, no running balance |
| Format changes | Low -- email format is relatively stable |

#### Verdict

**Supplementary only.** Useful for near-real-time alerts and quick categorization prompts, but cannot replace full transaction export. Could be a nice addition to a manual CSV import workflow.

### 2f. Manual CSV/OFX Import (Current Baseline)

This is the approach already supported in the accounting stack.

#### Workflow

1. Log into RBC Online Banking (monthly or bi-weekly).
2. Download transactions as CSV or QFX for each account.
3. Run the Beancount importer to parse and categorize.
4. Review and approve categorizations.

#### Characteristics

| Factor | Assessment |
|--------|-----------|
| Security | Excellent -- no third-party credential sharing |
| Reliability | Excellent -- deterministic, no breakage |
| Effort | Low-medium -- 5-10 minutes per download session |
| Frequency | Monthly or bi-weekly is practical |
| Automation | None -- fully manual |
| Data completeness | Excellent -- full transaction history available |

#### Verdict

**Solid baseline.** For a solo consultant doing ~50-100 transactions/month, manual monthly download is entirely manageable. This should remain the fallback regardless of any automation added.

---

## 3. Security Considerations

### 3.1 Security Assessment by Method

| Method | Credential Exposure | Data Transit | Data at Rest | Revocation | Breach Impact |
|--------|-------------------|-------------|-------------|------------|---------------|
| **Plaid** | High -- Plaid holds RBC credentials | TLS 1.2+ | Plaid's US servers (encrypted) | Disconnect in Plaid dashboard | Plaid breach = credential exposure |
| **Flinks** | High -- Flinks holds RBC credentials | TLS 1.2+ | Canadian AWS (encrypted) | Disconnect in Flinks | Flinks breach = credential exposure |
| **Screen scraping** | High -- credentials in local scripts | TLS to RBC | Local only | Delete script | Local machine compromise |
| **OFX Direct Connect** | Medium -- credentials sent per-request | TLS to RBC | Local only | Change password | Low -- no persistent storage |
| **Email parsing** | None -- uses email credentials only | TLS (IMAP) | Local only | Revoke email access | Email breach (not bank) |
| **Manual CSV/OFX** | None | Browser TLS | Local only | N/A | None |
| **CDF (future)** | None -- OAuth tokens | TLS 1.3 | Per provider policy | Revoke token | Limited scope exposure |

### 3.2 Credential-Sharing Risks (Aggregators)

This is the single biggest security concern for Plaid/Flinks:

1. **You give your banking password to a third party.** Despite encryption at rest, Plaid/Flinks must be able to decrypt your credentials to log into RBC on your behalf.
2. **No read-only scoping.** Because aggregators log in as you, they theoretically have full account access (view, transfer, etc.). They contractually limit actions to read-only, but technically they have full session access.
3. **Breach scenario:** If Plaid or Flinks is breached:
   - Attacker gets your RBC login credentials.
   - Attacker can log into your RBC account.
   - Your only recourse is to immediately change your RBC password.
4. **Shared credential problem:** If you use the same password elsewhere (you shouldn't), the blast radius expands.

### 3.3 Best Practices for Aggregator Use

If you choose to use an aggregator:

1. **Use a unique, strong password for RBC** that is not reused anywhere.
2. **Enable all available MFA** on your RBC account (SMS, push notification).
3. **Monitor account activity** -- set up RBC alerts for all transactions.
4. **Limit aggregator scope** -- only connect the accounts you need (e.g., business chequing, business credit card).
5. **Review connected apps** periodically in the aggregator dashboard.
6. **Prefer Canadian-hosted** (Flinks > Plaid for data residency).
7. **Architect locally:** Fetch transaction data from the aggregator API, store locally in your Beancount ledger, do not keep a cloud copy.

### 3.4 Local-First Architecture

For maximum security, the accounting stack should follow these principles:

```
RBC --> [Aggregator API or Manual Download] --> Local Machine --> Beancount Ledger (git repo)
                                                     |
                                             No cloud storage
                                             No SaaS dependency
                                             All data on local disk + backup
```

- **Never store banking credentials** in the accounting stack itself.
- **Never store raw transaction data in a cloud service** (except encrypted backups).
- **Use environment variables or OS keychain** for aggregator API keys.
- **Git-encrypt sensitive files** if the Beancount ledger is pushed to a remote (use `git-crypt` or similar).

### 3.5 Regulatory Considerations

- **PIPEDA** (federal): Requires consent for collection, use, and disclosure of personal financial data. Aggregators must comply.
- **Quebec Privacy Law (Law 25 / Bill 64):** Quebec's modernized privacy law (in effect since September 2023) imposes stricter requirements:
  - Privacy impact assessments required for high-risk processing.
  - Data breach notification within 72 hours.
  - Right to data portability (aligns with CDF goals).
  - Fines up to 2% of global revenue or $10M CAD.
- **CDF regulation:** When implemented, will provide a regulated framework for data sharing, removing the need for credential-sharing.

---

## 4. Open-Source Projects and Resources

### 4.1 OFX Parsing and Import

| Project | Language | Description | RBC Relevance |
|---------|----------|-------------|---------------|
| **[ofxtools](https://github.com/csingley/ofxtools)** | Python | Full OFX parser, client, and statement model. Supports OFX 1.x and 2.x. Includes `ofxget` CLI for OFX Direct Connect. | High -- can parse RBC QFX/OFX files. `ofxget` could test OFX Direct Connect endpoint. |
| **[ofxparse](https://github.com/jseutter/ofxparse)** | Python | Simpler OFX parser. Less maintained than ofxtools. | Medium -- works for basic QFX parsing. |
| **[ofxhome.com](https://www.ofxhome.com/)** | Web directory | Directory of OFX server information for financial institutions. | Check RBC entry for current OFX endpoint details and user reports. |

### 4.2 Beancount Ecosystem

| Project | Description | RBC Relevance |
|---------|-------------|---------------|
| **[beancount](https://github.com/beancount/beancount)** | Core double-entry accounting engine. | Foundation of the accounting stack. |
| **[beangulp](https://github.com/beancount/beangulp)** | Beancount's official importer framework (replacement for beancount.ingest). | Use for building RBC CSV/OFX importers. |
| **[smart_importer](https://github.com/beancount/smart_importer)** | ML-based transaction categorization for Beancount. Uses scikit-learn. | Apply to RBC transactions for auto-categorization. |
| **[beancount-import](https://github.com/jbms/beancount-import)** | Web-based import reconciliation UI. | Useful for reviewing RBC imports interactively. |
| **[fava](https://github.com/beancount/fava)** | Web UI for Beancount. Already in use. | Already integrated in the stack. |

### 4.3 Canadian Bank Importers

| Project | Description | RBC Relevance |
|---------|-------------|---------------|
| **[beancount-rbc](https://github.com/search?q=beancount+rbc)** | Search GitHub for Beancount RBC importers. Several community importers exist for RBC CSV format. | Directly applicable. Check for maintained forks. |
| **RBC CSV format** | RBC's CSV export follows a consistent format: `Account Type, Account Number, Transaction Date, Cheque Number, Description 1, Description 2, CAD$, USD$`. | Known format; existing importers handle this. |
| **[hledger CSV rules](https://hledger.org/csv.html)** | hledger supports declarative CSV import rules. | Can define rules for RBC CSV format (even if using Beancount, the approach is informative). |

### 4.4 Aggregator SDKs

| Project | Language | Description |
|---------|----------|-------------|
| **[plaid-python](https://github.com/plaid/plaid-python)** | Python | Official Plaid Python SDK. Well-maintained. |
| **[plaid-node](https://github.com/plaid/plaid-node)** | Node.js | Official Plaid Node SDK. |
| **Flinks API** | REST | No official SDK, but simple REST API. Use `requests` or `httpx` in Python. |

### 4.5 Web Scraping / Automation (if needed)

| Project | Language | Description |
|---------|----------|-------------|
| **[Playwright](https://playwright.dev/python/)** | Python/Node | Browser automation. Best option if scraping is pursued. |
| **[playwright-stealth](https://github.com/nickthecook/playwright-stealth)** | Plugin | Anti-detection measures for Playwright. |

### 4.6 General Banking Automation

| Project | Language | Description | RBC Relevance |
|---------|----------|-------------|---------------|
| **[woob (formerly weboob)](https://woob.tech/)** | Python | Modular framework for interacting with websites (banking, housing, etc.). Has modules for many French and some international banks. | Low -- no known RBC module. Could be extended but effort is significant. |
| **[bank2ynab](https://github.com/bank2ynab/bank2ynab)** | Python | Converts bank CSV exports to YNAB format. Has RBC CSV support. | Informative for RBC CSV parsing patterns. |
| **[firefly-iii](https://github.com/firefly-iii/firefly-iii)** | PHP | Open-source personal finance manager. Has CSV import and some aggregator integrations. | Architecture reference. |

### 4.7 Security Tools

| Tool | Purpose |
|------|---------|
| **[git-crypt](https://github.com/AGWA/git-crypt)** | Encrypt sensitive files in git repositories. |
| **[sops](https://github.com/getsops/sops)** | Secrets management for config files. |
| **macOS Keychain (via `keyring` Python package)** | Store API keys and credentials in OS keychain instead of env files. |

---

## 5. Recommended Approach

### 5.1 Ranking of Methods

| Rank | Method | Feasibility | Security | Maintenance | Recommended? |
|------|--------|-------------|----------|-------------|-------------|
| 1 | **Manual CSV/OFX import** | Excellent | Excellent | None | **Yes -- baseline** |
| 2 | **Flinks (aggregator)** | Good | Medium (Canadian data residency) | Low | **Yes -- if automation desired** |
| 3 | **Plaid (aggregator)** | Good | Medium (US data storage) | Low | **Yes -- alternative to Flinks** |
| 4 | **CDF API (future)** | Not yet available | Excellent (OAuth, scoped) | Low | **Yes -- when available (2027+)** |
| 5 | **OFX Direct Connect** | Uncertain (may be deprecated) | Good | Medium | **Test first** |
| 6 | **Email parsing** | Limited scope | Good | Medium | **Supplementary only** |
| 7 | **Screen scraping** | Fragile | Poor (TOS risk) | High | **No** |

### 5.2 Recommended Phased Approach

#### Phase A: Now (Manual + Smart Import)

**Already in place.** Continue with:

1. Monthly manual CSV/OFX download from RBC Online Banking.
2. Beancount importer with `smart_importer` for auto-categorization.
3. Fava web UI for review and approval.
4. Total effort: ~10-15 minutes/month.

**Enhancements to consider:**
- Test OFX Direct Connect with `ofxtools` / `ofxget` to see if RBC's endpoint still works. If so, this can be scripted (still requires password, but avoids browser login).
- Refine CSV importer rules based on accumulated categorization history.

#### Phase B: Near-term (Aggregator Integration -- Optional)

If the manual approach becomes burdensome or if you want daily/real-time transaction visibility:

1. **Evaluate Flinks first** (Canadian data residency, Montreal-based).
   - Sign up for developer sandbox.
   - Test RBC connection reliability over 2-4 weeks.
   - Assess pricing for single-user production use.
2. **Plaid as alternative** if Flinks pricing is prohibitive.
   - Plaid's developer tier may be more cost-effective for a single connection.
3. **Architecture:**
   - Local Python script runs daily (cron or manual trigger).
   - Fetches new transactions from aggregator API.
   - Converts to Beancount format.
   - Appends to ledger file.
   - Flags uncategorized transactions for review.

**Security mitigation:**
- Use dedicated RBC password (not shared with anything).
- Enable all RBC MFA options.
- Store aggregator API keys in macOS Keychain.
- Keep all data local.

#### Phase C: Long-term (CDF / Open Banking)

When Canada's Consumer-Directed Finance framework goes live:

1. Register as a CDF-authorized application (or use an authorized intermediary).
2. Use OAuth-based token access -- no credential sharing.
3. Scoped read-only access to specific accounts.
4. Revocable tokens with clear audit trail.

This is the ideal end state but unlikely before 2027.

### 5.3 Approaches Not Worth Pursuing

| Method | Reason |
|--------|--------|
| **Screen scraping** | TOS violation, account lockout risk, high maintenance, poor reliability. |
| **RBC mobile app API reverse-engineering** | Undocumented, changes frequently, TOS violation, security risk. |
| **MX / Yodlee** | Enterprise pricing, not developer-friendly. Overkill for single-user. |
| **woob** | No RBC module exists. Building one is effectively screen scraping with extra steps. |

### 5.4 Actionable Next Steps

1. **Immediate:** Test OFX Direct Connect for RBC using `ofxtools`:
   ```bash
   pip install ofxtools
   ofxget scan --url "https://www1.royalbank.com/..." --org RBC --fid 900000100
   ```
   Document results. If it works, this provides a scriptable (though password-based) download path.

2. **If automation desired:** Create a Flinks developer account and test RBC sandbox connectivity. Evaluate pricing.

3. **Enhance current importer:** Invest in improving the existing Beancount RBC CSV importer with better categorization rules and `smart_importer` training.

4. **Monitor CDF progress:** Subscribe to FCAC announcements and Department of Finance open banking updates. When Phase 1 launches, evaluate API access options.

---

## Appendix: RBC CSV Format Reference

RBC's standard CSV export format for chequing/savings accounts:

```
Account Type,Account Number,Transaction Date,Cheque Number,Description 1,Description 2,CAD$,USD$
Chequing,12345-1234567,1/15/2026,,INTERAC PURCHASE,MERCHANT NAME,-45.67,
Chequing,12345-1234567,1/15/2026,,DEPOSIT,WIRE TRANSFER,5000.00,
```

RBC credit card CSV format:

```
Transaction Date,Posting Date,Description,Amount
1/15/2026,1/16/2026,AMAZON.CA,-89.99
1/14/2026,1/15/2026,PAYMENT - THANK YOU,500.00
```

Key parsing notes:
- Date format: M/D/YYYY (US-style, not ISO 8601).
- Negative amounts = debits (money out). Positive = credits (money in) for chequing.
- For credit cards: negative = purchases, positive = payments/credits.
- Description may be split across two fields (Description 1, Description 2) for chequing.
- Currency columns are separate (CAD$, USD$) for chequing -- useful for USD accounts.

---

## Appendix: Key URLs and Resources

- **RBC Online Banking:** https://www.rbcroyalbank.com/
- **RBC API Marketplace:** https://developer.rbc.com/
- **ofxhome.com RBC entry:** https://www.ofxhome.com/index.php/institution/view/473
- **Plaid docs:** https://plaid.com/docs/
- **Flinks docs:** https://docs.flinks.com/
- **Canada CDF info:** https://www.canada.ca/en/department-finance/programs/financial-sector-policy/open-banking-implementation.html
- **FCAC:** https://www.canada.ca/en/financial-consumer-agency.html
- **ofxtools:** https://github.com/csingley/ofxtools
- **beangulp:** https://github.com/beancount/beangulp
- **smart_importer:** https://github.com/beancount/smart_importer
- **git-crypt:** https://github.com/AGWA/git-crypt
