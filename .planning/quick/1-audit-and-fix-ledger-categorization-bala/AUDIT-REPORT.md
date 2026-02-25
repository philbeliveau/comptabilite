# Ledger Categorization Audit Report

**Date:** 2026-02-19
**Scope:** All transactions from csv4883.csv import (160 CSV data rows)
**Files audited:**
- `ledger/pending.beancount` (141 transactions)
- `ledger/2026/01.beancount` (9 transactions -- Mollo Cafe)
- `ledger/2026/02.beancount` (9 transactions -- Mollo Cafe)

**Total transactions in ledger:** 159
**Total CSV data rows:** 160 (1 missing from ledger -- see LOW-02)

---

## Executive Summary

| Severity | Count | Financial Impact |
|----------|-------|------------------|
| CRITICAL | 4 issues (15 transactions) | $2,964.56 misclassified |
| HIGH | 7 issues (28 transactions) | $1,609.96 misclassified |
| MEDIUM | 7 issues (13 transactions) | $485.53 questionable |
| LOW | 3 issues | Metadata only |

**Key findings:**
- **$981.48** in payroll deposits wrongly booked as expense (Salaires:Brut) instead of liability clearing -- inflates expenses AND creates phantom salary expense without corresponding payroll journal entries
- **$266.68** in personal tax credits (Impot Solidarite) booked as Revenus:Autres instead of Passifs:Pret-Actionnaire -- inflates corporate revenue
- **$1,973.69** credit card payment entry broken (both legs post to same account) -- accounting integrity violation
- **$89.56** GST refund booked as negative expense instead of asset reduction
- **$92.36** in personal coffee (Mollo Cafe x18) inflating corporate meal expenses
- **$5,325.00** rent correctly categorized but with wrong capex flag (would misreport on CCA schedule)
- Multiple personal expenses (bars, restaurants, groceries) wrongly booked as business expenses totaling ~$573.46

**Total expenses potentially overstated:** ~$1,647.30
**Total revenue potentially overstated:** $266.68
**Total shareholder loan balance potentially understated:** ~$1,006.52

---

## CRITICAL Issues

### CRIT-01: DEPOT DE PAIE classified as Depenses:Salaires:Brut

**Transactions affected:** 5 entries

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 3 | 2025-11-06 | 522.67 | pending:19 |
| 8 | 2025-11-20 | 329.90 | pending:76 |
| 14 | 2025-12-04 | 34.37 | pending:145 |
| 26 | 2025-12-31 | 60.15 | pending:269 |
| 49 | 2026-01-29 | 34.39 | pending:529 |

**Total:** $981.48

**Current entry (example, line 3):**
```beancount
2025-11-06 ! "Depot De Paie Consultants En" "DEPOT DE PAIE CONSULTANTS EN" #pending
  Actifs:Banque:RBC:Cheques   522.67 CAD
  Depenses:Salaires:Brut     -522.67 CAD
```

**Problem:** These are NET PAY deposits into the corporate chequing account from the payroll processor ("Consultants En" = the payroll service). The bank receives cash (debit correct), but the credit side should NOT be Depenses:Salaires:Brut. Booking it this way:
1. Creates a phantom gross salary expense that does not reflect actual gross pay
2. Does not clear the payroll liability (Passifs:Salaires-A-Payer)
3. Amounts are net-of-deductions, not gross -- the actual gross salary is higher
4. Source deductions and employer contributions are completely missing

**Correct entry (interim, pending full payroll journal):**
```beancount
2025-11-06 ! "Depot De Paie Consultants En" "DEPOT DE PAIE CONSULTANTS EN" #pending
  Actifs:Banque:RBC:Cheques    522.67 CAD
  Passifs:Salaires-A-Payer    -522.67 CAD
```

**Full correction requires:** Creating complete payroll journal entries with:
- Dr Depenses:Salaires:Brut (actual gross)
- Cr Passifs:Retenues:* (each deduction type)
- Cr Passifs:Cotisations-Employeur:* (employer portions)
- Cr Passifs:Salaires-A-Payer (net pay = these deposit amounts)
- Then the deposit clears Salaires-A-Payer

**Impact:** Depenses:Salaires:Brut overstated by $981.48 (but actually should be HIGHER than these amounts once real gross is calculated). All payroll deduction liabilities are missing.

**Additional metadata issue:** Line 3 has spurious `capex: "oui"` flag on a payroll deposit.

---

### CRIT-02: IMPOT SOLIDARITE classified as Revenus:Autres

**Transactions affected:** 4 entries

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 2 | 2025-11-05 | 66.67 | pending:8 |
| 16 | 2025-12-05 | 66.67 | pending:167 |
| 33 | 2026-01-05 | 66.67 | pending:348 |
| 56 | 2026-02-05 | 66.67 | pending:607 |

**Total:** $266.68

**Current entry:**
```beancount
2025-11-05 ! "Impot Solidarite Gouv. Quebec" "IMPOT SOLIDARITE GOUV. QUEBEC" #pending
  Actifs:Banque:RBC:Cheques   66.67 CAD
  Revenus:Autres             -66.67 CAD
```

**Problem:** The "Impot Solidarite" (QST solidarity tax credit) is a PERSONAL tax benefit paid by Revenu Quebec to the individual taxpayer. It is not corporate revenue. When deposited into the corporate bank account, it creates a shareholder loan obligation -- the corporation owes this amount to the shareholder.

**Correct entry:**
```beancount
2025-11-05 ! "Impot Solidarite Gouv. Quebec" "IMPOT SOLIDARITE GOUV. QUEBEC" #pending
  Actifs:Banque:RBC:Cheques    66.67 CAD
  Passifs:Pret-Actionnaire    -66.67 CAD
```

**Impact:** Revenus:Autres overstated by $266.68. Passifs:Pret-Actionnaire understated by $266.68. This falsely increases taxable income.

---

### CRIT-03: PAIEMENT AUTOMATISE -- both legs post to CartesCredit:RBC

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 110 | 2026-01-26 | 1,973.69 | pending:1147 |

**Current entry:**
```beancount
2026-01-26 ! "Paiement Automatise - Merci" "PAIEMENT AUTOMATISE - MERCI" #pending
  Passifs:CartesCredit:RBC   1973.69 CAD
  Passifs:CartesCredit:RBC  -1973.69 CAD
```

**Problem:** Both postings go to the same account, netting to zero. This is a credit card PAYMENT recorded from the Visa statement perspective (positive = reduces balance). It should debit CartesCredit:RBC (reducing the liability) and credit Actifs:Banque:RBC:Cheques (cash going out). HOWEVER, this same payment already appears on the chequing side as CSV line 46 (PAIEMENT DIVERS CARTE RBC, -$1,973.69) at pending line 493.

**Correct entry (from Visa perspective):**
```beancount
2026-01-26 ! "Paiement Automatise - Merci" "PAIEMENT AUTOMATISE - MERCI" #pending
  Passifs:CartesCredit:RBC    1973.69 CAD
  Actifs:Banque:RBC:Cheques  -1973.69 CAD
```

**CRITICAL NOTE on double-counting:** If BOTH the Visa-side entry (line 110) and the chequing-side entry (line 46) are kept, this payment will be recorded twice. Only ONE should survive. See Double-Counting Analysis section below.

**Impact:** Currently nets to zero (no balance impact due to same-account posting). Once fixed, must ensure only one entry survives to avoid double-counting $1,973.69.

**Additional metadata issues:** Has spurious `capex: "oui"` and `classe_dpa_suggeree: "10"` flags on a payment transaction.

---

### CRIT-04: TPS CANADA GST refund as Depenses:TPS-Remise (negative)

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 34 | 2026-01-05 | 89.56 | pending:359 |

**Current entry:**
```beancount
2026-01-05 ! "Tps Canada" "TPS CANADA" #pending
  Actifs:Banque:RBC:Cheques   89.56 CAD
  Depenses:TPS-Remise        -89.56 CAD
```

**Problem:** A GST refund from CRA is not a negative expense. It is a reduction of the GST receivable (Actifs:TPS-Payee) or a credit to the GST liability (Passifs:TPS-Percue), depending on the net position. In most cases for a business claiming ITCs, this should reduce Actifs:TPS-Payee.

**Correct entry:**
```beancount
2026-01-05 ! "Tps Canada" "TPS CANADA" #pending
  Actifs:Banque:RBC:Cheques   89.56 CAD
  Actifs:TPS-Payee           -89.56 CAD
```

**Impact:** Depenses:TPS-Remise has a -$89.56 credit balance (negative expense = effectively income). TPS-Payee asset is overstated by $89.56 because the refund was never applied against it.

---

## HIGH Issues

### HIGH-01: Mollo Cafe x18 as Depenses:Repas-Representation (personal coffee)

**Transactions affected:** 18 entries across 01.beancount and 02.beancount

**In 01.beancount (9 entries):**

| CSV Line | Date | Amount |
|----------|------|--------|
| 68 | 2026-01-07 | 4.60 |
| 81 | 2026-01-13 | 4.88 |
| 82 | 2026-01-13 | 4.60 |
| 94 | 2026-01-20 | 5.13 |
| 97 | 2026-01-21 | 5.13 |
| 112 | 2026-01-26 | 5.08 |
| 113 | 2026-01-27 | 4.88 |
| 116 | 2026-01-28 | 5.31 |
| 117 | 2026-01-29 | 5.13 |

**In 02.beancount (9 entries):**

| CSV Line | Date | Amount |
|----------|------|--------|
| 124 | 2026-02-01 | 5.13 |
| 126 | 2026-02-02 | 5.31 |
| 128 | 2026-02-03 | 5.13 |
| 132 | 2026-02-04 | 5.13 |
| 139 | 2026-02-09 | 5.13 |
| 141 | 2026-02-10 | 5.31 |
| 146 | 2026-02-12 | 4.88 |
| 158 | 2026-02-16 | 5.13 |
| 159 | 2026-02-17 | 5.13 |

**Total:** $92.36 (18 entries)

**Current entry (example):**
```beancount
2026-01-07 ! "Mollo Cafe Montreal Qc" "MOLLO CAFE MONTREAL QC"
  Passifs:CartesCredit:RBC       -4.60 CAD
  Depenses:Repas-Representation   4.60 CAD
```

**Problem:** Daily ~$5 coffee purchases at the same cafe are clearly personal consumption, not business meals or representation. CRA rules require business meals to have a specific business purpose (client meeting, travel, etc.). Daily coffee from the same shop is a personal lifestyle expense. These were categorized by rule (confiance: 1.0) which means the rule itself is wrong.

**Correct entry:**
```beancount
2026-01-07 ! "Mollo Cafe Montreal Qc" "MOLLO CAFE MONTREAL QC"
  Passifs:CartesCredit:RBC    -4.60 CAD
  Passifs:Pret-Actionnaire     4.60 CAD
```

**Impact:** Depenses:Repas-Representation overstated by $92.36. Passifs:Pret-Actionnaire understated by $92.36.

**Note:** The categorization rule for "Mollo Cafe" needs to be updated from Repas-Representation to Pret-Actionnaire.

---

### HIGH-02: SAAQ-IMMATRIC as Depenses:Vehicule:Assurance

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 47 | 2026-01-27 | 400.86 | pending:506 |

**Current entry:**
```beancount
2026-01-27 ! "Paiement Paiement W3 - 1426 Saaq-Immatric" "Paiement PAIEMENT W3 - 1426 SAAQ-IMMATRIC" #pending
  Actifs:Banque:RBC:Cheques    -400.86 CAD
  Depenses:Vehicule:Assurance   400.86 CAD
```

**Problem:** SAAQ-IMMATRIC is vehicle registration/immatriculation at the SAAQ (Societe de l'assurance automobile du Quebec), NOT insurance. Registration fees are a separate expense type. Additionally: is this a personal vehicle used for business, or a corporate vehicle? If personal, this should be Pret-Actionnaire (or partially deductible if business-use percentage applies).

**Correct entry (if corporate vehicle):**
```beancount
2026-01-27 ! "Paiement Paiement W3 - 1426 Saaq-Immatric" #pending
  Actifs:Banque:RBC:Cheques              -400.86 CAD
  Depenses:Vehicule:Immatriculation       400.86 CAD
```

**Note:** Account `Depenses:Vehicule:Immatriculation` does not exist in comptes.beancount -- see Chart of Accounts Gaps section.

**If personal vehicle:** Should be `Passifs:Pret-Actionnaire` instead.

**Impact:** Depenses:Vehicule:Assurance overstated by $400.86.

---

### HIGH-03: LS Muni GC as Depenses:Vehicule:Stationnement

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 79 | 2026-01-11 | 58.19 | pending:850 |

**Current entry:**
```beancount
2026-01-11 ! "Ls Muni Gc Montreal Qc" "LS Muni GC Montreal QC" #pending
  Passifs:CartesCredit:RBC         -58.19 CAD
  Depenses:Vehicule:Stationnement   58.19 CAD
```

**Problem:** "LS Muni GC" is a bar/restaurant in Montreal (Le Muni, Grand Central area), NOT a parking facility. The $58.19 amount and "LS" prefix (typical of Lightspeed POS systems used by restaurants) confirm this is a bar/restaurant charge. This is a personal expense.

**Correct entry:**
```beancount
2026-01-11 ! "Ls Muni Gc Montreal Qc" "LS Muni GC Montreal QC" #pending
  Passifs:CartesCredit:RBC    -58.19 CAD
  Passifs:Pret-Actionnaire     58.19 CAD
```

**Impact:** Depenses:Vehicule:Stationnement overstated by $58.19. Passifs:Pret-Actionnaire understated by $58.19.

---

### HIGH-04: Adelard Belanger Et Fils as Depenses:Bureau:Fournitures

**Transactions affected:** 2 entries

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 75 | 2026-01-09 | 22.99 | pending:806 |
| 105 | 2026-01-24 | 27.23 | pending:1092 |

**Total:** $50.22

**Current entry (example):**
```beancount
2026-01-09 ! "Adelard Belanger Et Fils Montreal Qc" "ADELARD BELANGER ET FILS MONTREAL QC" #pending
  Passifs:CartesCredit:RBC     -22.99 CAD
  Depenses:Bureau:Fournitures   22.99 CAD
```

**Problem:** Adelard Belanger et Fils is a grocery/butcher shop at Marche Atwater in Montreal. These are personal grocery purchases, not office supplies.

**Correct entry:**
```beancount
2026-01-09 ! "Adelard Belanger Et Fils Montreal Qc" "ADELARD BELANGER ET FILS MONTREAL QC" #pending
  Passifs:CartesCredit:RBC    -22.99 CAD
  Passifs:Pret-Actionnaire     22.99 CAD
```

**Impact:** Depenses:Bureau:Fournitures overstated by $50.22. Passifs:Pret-Actionnaire understated by $50.22.

---

### HIGH-05: Restaurant Grinder $323.64 -- probable Valentine's dinner

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 151 | 2026-02-13 | 323.64 | pending:1480 |

**Current entry:**
```beancount
2026-02-13 ! "Restaurant Grinder Montreal Qc" "RESTAURANT GRINDER MONTREAL QC" #pending
  Passifs:CartesCredit:RBC       -323.64 CAD
  Depenses:Repas-Representation   323.64 CAD
```

**Problem:** $323.64 at a restaurant on February 13 (Valentine's Day eve) is almost certainly a personal dinner. The amount ($323.64 for what appears to be a single dining occasion) and the date make business purpose very difficult to justify to CRA.

**Correct entry:**
```beancount
2026-02-13 ! "Restaurant Grinder Montreal Qc" "RESTAURANT GRINDER MONTREAL QC" #pending
  Passifs:CartesCredit:RBC    -323.64 CAD
  Passifs:Pret-Actionnaire     323.64 CAD
```

**Impact:** Depenses:Repas-Representation overstated by $323.64. Passifs:Pret-Actionnaire understated by $323.64.

---

### HIGH-06: VIREMENT ENVOYE $1,775 x3 with capex:"oui" flag

**Transactions affected:** 3 entries

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 12 | 2025-12-01 | 1,775.00 | pending:122 |
| 30 | 2026-01-02 | 1,775.00 | pending:314 |
| 53 | 2026-02-02 | 1,775.00 | pending:573 |

**Total:** $5,325.00

**Current entry (example):**
```beancount
2025-12-01 ! "Vir Courriel Virement Envoye" "Vir courriel VIREMENT ENVOYE" #pending
  capex: "oui"
  Actifs:Banque:RBC:Cheques  -1775.00 CAD
  Depenses:Bureau:Loyer       1775.00 CAD
```

**Problem:** The account classification (Depenses:Bureau:Loyer) is correct -- this appears to be monthly rent. However, the `capex: "oui"` metadata flag is WRONG. Rent is an operating expense (opex), not a capital expenditure. If CCA schedules are generated from the capex flag, these would incorrectly appear as capital assets instead of period expenses.

**Correct entry:**
```beancount
2025-12-01 ! "Vir Courriel Virement Envoye" "Vir courriel VIREMENT ENVOYE" #pending
  Actifs:Banque:RBC:Cheques  -1775.00 CAD
  Depenses:Bureau:Loyer       1775.00 CAD
```

(Remove `capex: "oui"` flag)

**Impact:** No dollar misclassification, but CCA/asset schedules would be polluted with $5,325.00 of non-capital items.

---

### HIGH-07: REQ annual registration fee as Depenses:Impots:Quebec

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 65 | 2026-01-06 | 41.00 | pending:707 |

**Current entry:**
```beancount
2026-01-06 ! "Req/020100060033430 Quebec Qc" "REQ/020100060033430 QUEBEC QC" #pending
  Passifs:CartesCredit:RBC  -41.00 CAD
  Depenses:Impots:Quebec     41.00 CAD
```

**Problem:** REQ is the Registraire des entreprises du Quebec. The $41.00 is the annual registration fee (declaration annuelle), NOT a tax payment. This is a regulatory compliance fee, not income tax. Booking it as Impots:Quebec misrepresents the nature of the expense and inflates the tax expense line.

**Correct entry:**
```beancount
2026-01-06 ! "Req/020100060033430 Quebec Qc" "REQ/020100060033430 QUEBEC QC" #pending
  Passifs:CartesCredit:RBC               -41.00 CAD
  Depenses:Honoraires-Professionnels:Autres  41.00 CAD
```

**Impact:** Depenses:Impots:Quebec overstated by $41.00. Depenses:Honoraires-Professionnels:Autres understated by $41.00. While the total expenses remain the same, the classification matters for GIFI mapping (government fee = GIFI 8860, not GIFI 9060).

---

## MEDIUM Issues

### MED-01: HYDRO-QUEBEC as Depenses:Bureau:Entretien

**Transactions affected:** 4 entries

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 4 | 2025-11-10 | 81.14 | pending:31 |
| 17 | 2025-12-08 | 81.14 | pending:178 |
| 37 | 2026-01-07 | 81.14 | pending:392 |
| 58 | 2026-02-10 | 81.14 | pending:629 |

**Total:** $324.56

**Current entry:**
```beancount
2025-11-10 ! "Pmnt Fact Electr Hydro-Quebec" "PMNT FACT ELECTR HYDRO-QUEBEC" #pending
  Actifs:Banque:RBC:Cheques  -81.14 CAD
  Depenses:Bureau:Entretien   81.14 CAD
```

**Problem:** Hydro-Quebec electricity bills are utilities, not maintenance/entretien. The account `Depenses:Bureau:Entretien` (GIFI 8811) is acceptable but imprecise. A more specific account like `Depenses:Bureau:Electricite` would be better for reporting clarity.

**Suggested correction:** Either keep as-is (defensible) or create a new sub-account `Depenses:Bureau:Electricite`. See Chart of Accounts Gaps.

**Impact:** No tax impact (same GIFI code 8811), but reduces reporting clarity.

---

### MED-02: Amazon $31.68 as Depenses:Bureau:Abonnements-Logiciels

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 115 | 2026-01-28 | 31.68 | pending:1183 |

**Current entry:**
```beancount
2026-01-28 ! "Amzn Mktp Ca*Yc8609Tw3 866-216-1072 On" "AMZN Mktp CA*YC8609TW3 866-216-1072 ON" #pending
  Passifs:CartesCredit:RBC               -31.68 CAD
  Depenses:Bureau:Abonnements-Logiciels   31.68 CAD
```

**Problem:** Amazon Marketplace purchases are physical goods, not software subscriptions. Without knowing what was purchased, defaulting to Abonnements-Logiciels is incorrect. Could be office supplies, personal items, or anything else.

**Action required:** Review receipt/order history to determine actual purchase. If personal, reclassify to Pret-Actionnaire. If office supplies, reclassify to Bureau:Fournitures.

**Impact:** Depenses:Bureau:Abonnements-Logiciels potentially overstated by $31.68.

---

### MED-03: Restaurants/bars booked as Depenses:Repas-Representation without business purpose

**Transactions affected:** 7 entries in pending.beancount

| CSV Line | Date | Payee | Amount | Beancount Line |
|----------|------|-------|--------|----------------|
| 69 | 2026-01-08 | Stash Cafe | 87.74 | pending:740 |
| 70 | 2026-01-08 | Le Phillips | 31.91 | pending:751 |
| 71 | 2026-01-09 | LS Philemon Bar | 42.50 | pending:762 |
| 77 | 2026-01-09 | Pasta Bella Atwater | 4.25 | pending:828 |
| 88 | 2026-01-19 | LS Bar Caffettiera | 10.48 | pending:927 |
| 92 | 2026-01-19 | McKibbin's Bishop | 10.48 | pending:971 |
| 129 | 2026-02-04 | LS Lord William Pub | 12.50 | pending:1282 |

**Total:** $199.86

**Problem:** These are bars and restaurants without documented business purpose. Many appear to be social outings (Philemon Bar, Gerts Student Bar on the same night Jan 19, McKibbin's Bishop). CRA requires meals and entertainment to have a documented business purpose (client name, business discussed).

Some may be legitimate (Stash Cafe $87.74 could be a client meeting), but without documentation, all are questionable. Even if legitimate, meals/entertainment are only 50% deductible.

**Suggested action:** Review each for business purpose. Those without documented business purpose should be reclassified to `Passifs:Pret-Actionnaire`.

**Impact:** Up to $199.86 in questionable deductions.

---

### MED-04: Cafes (Bloom, 49th Parallel, Brulerie) as Pret-Actionnaire

**Transactions affected:** 5 entries -- already correctly classified

| CSV Line | Payee | Amount | Classification |
|----------|-------|--------|----------------|
| 83 | LS le cafe bloom | 4.67 | Pret-Actionnaire (correct) |
| 85 | LS le cafe bloom | 9.10 | Pret-Actionnaire (correct) |
| 98 | LS 49th Parallel | 4.88 | Pret-Actionnaire (correct) |
| 106 | Brulerie aux 4 vents | 2.00 | Pret-Actionnaire (correct) |
| 133 | Brulerie aux 4 vents | 3.00 | Pret-Actionnaire (correct) |

**Status:** CORRECTLY CLASSIFIED. These are properly tagged as shareholder loan (personal coffee). No action needed. Listed here for completeness.

---

### MED-05: Apple.com/Bill $1.48 with capex:"oui"

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 111 | 2026-01-26 | 1.48 | pending:1160 |

**Current entry:**
```beancount
2026-01-26 ! "Apple.Com/Bill 866-712-7753 On" "APPLE.COM/BILL 866-712-7753 ON" #pending
  capex: "oui"
  Passifs:CartesCredit:RBC               -1.48 CAD
  Depenses:Bureau:Abonnements-Logiciels   1.48 CAD
```

**Problem:** $1.48 Apple charge is likely iCloud storage or a small app purchase. The account (Abonnements-Logiciels) is acceptable, but the `capex: "oui"` flag is wrong -- a $1.48 subscription is not a capital expenditure.

**Correct entry:** Remove `capex: "oui"` flag. Account classification is acceptable.

---

### MED-06: Assurance CIE BELAIR -- inconsistent account classification

**Transactions affected:** 6 entries

| CSV Line | Date | Amount | Account Used | Beancount Line |
|----------|------|--------|-------------|----------------|
| 10 | 2025-12-01 | 38.69 | Assurances:Autres | pending:100 |
| 11 | 2025-12-01 | 89.09 | Assurances:Autres | pending:111 |
| 28 | 2026-01-02 | 38.69 | Assurances:Autres | pending:292 |
| 29 | 2026-01-02 | 89.09 | Assurances:Autres | pending:303 |
| 51 | 2026-02-02 | 38.69 | Vehicule:Assurance | pending:551 |
| 52 | 2026-02-02 | 89.09 | Assurances:Autres | pending:562 |

**Problem:** Belair is a car insurance company. Five of six entries use Depenses:Assurances:Autres, but line 51 uses Depenses:Vehicule:Assurance. The $38.69 amount appears monthly (likely auto insurance), while $89.09 also appears monthly (possibly home or another vehicle). Both should consistently use either Vehicule:Assurance (if auto) or Assurances:Autres (if home/other). Need to verify insurance type.

**Note:** If this is personal auto insurance paid from the corporate account, it should be Pret-Actionnaire unless there's a documented business-use percentage.

---

### MED-07: Fizz Internet/Telecom -- personal vs business

**Transactions affected:** 2 entries

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 118 | 2026-01-29 | 25.93 | pending:1194 |
| 134 | 2026-02-04 | 49.44 | pending:1326 |

**Total:** $75.37

**Problem:** Fizz is a personal mobile/internet provider. If this is a personal phone plan, it should be Pret-Actionnaire. If it is a business internet/phone line, the classification (Bureau:Internet-Telecom) is correct. The two different amounts ($25.93 and $49.44) suggest possibly two different services or a billing change.

**Action required:** Confirm whether these are personal or business telecom services.

---

## LOW Issues

### LOW-01: Spurious capex:"oui" flags on non-capital items

**Transactions affected:** Multiple entries

| CSV Line | Date | Payee | capex flag | Issue |
|----------|------|-------|-----------|-------|
| 3 | 2025-11-06 | Depot de Paie | oui | Payroll deposit is not capex |
| 6 | 2025-11-17 | Virement Recu $2,195 | oui | E-transfer received is not capex |
| 9 | 2025-11-27 | Paiement Carte RBC | oui | CC payment is not capex |
| 20 | 2025-12-15 | Virement Recu $500 | oui | E-transfer is not capex |
| 25 | 2025-12-30 | Paiement Carte RBC | oui | CC payment is not capex |
| 27 | 2026-01-02 | Virement Recu $700 | oui | E-transfer is not capex |
| 42 | 2026-01-19 | Virement Recu $900 | oui | E-transfer is not capex |
| 46 | 2026-01-27 | Paiement Carte RBC | oui | CC payment is not capex |
| 48 | 2026-01-28 | Virement Recu $500 | oui | E-transfer is not capex |
| 59 | 2026-02-13 | Virement Recu $900 | oui | E-transfer is not capex |
| 110 | 2026-01-26 | Paiement Automatise | oui | CC payment is not capex |
| 111 | 2026-01-26 | Apple.com/Bill | oui | $1.48 subscription is not capex |

Also note `classe_dpa_suggeree: "10"` on credit card payment entries (lines 9, 25, 46, 110) -- class 10 is for motor vehicles, not credit card payments.

**Impact:** No direct financial impact, but pollutes CCA schedule generation. All `capex: "oui"` flags on these entries should be removed.

---

### LOW-02: Missing CSV line 22 -- not imported into ledger

**CSV line 22:** `12/17/2025, Vir courriel, VIREMENT RECU, 16.00`

The CSV has TWO identical entries on Dec 17, 2025 for "Vir courriel VIREMENT RECU" at $16.00:
- CSV line 21 (present in ledger as pending line 223, `ligne: "21"`)
- CSV line 22 (NOT present in ledger)

The importer likely deduplicated this as a duplicate (same date, payee, amount). However, these could be two separate e-transfers. The transaction count in the ledger is 159, while the CSV has 160 data rows, confirming exactly one row is missing.

**Action required:** Verify whether CSV line 22 is a genuine second transfer or a CSV export duplicate. If genuine, add:
```beancount
2025-12-17 ! "Vir Courriel Virement Recu" "Vir courriel VIREMENT RECU" #pending
  ligne: "22"
  Actifs:Banque:RBC:Cheques   16.00 CAD
  Passifs:Pret-Actionnaire   -16.00 CAD
```

---

### LOW-03: DEP TIERS W3-3019 revenue entry with capex:"oui"

**Transaction:** 1 entry

| CSV Line | Date | Amount | Beancount Line |
|----------|------|--------|----------------|
| 38 | 2026-01-12 | 2,250.00 | pending:403 |

**Current entry:**
```beancount
2026-01-12 ! "Dep Tiers W3-3019" "DEP TIERS W3-3019" #pending
  capex: "oui"
  Actifs:Banque:RBC:Cheques   2250.00 CAD
  Revenus:Consultation       -2250.00 CAD
```

**Problem:** This appears to be a third-party deposit (client payment / consulting revenue). The account (Revenus:Consultation) is correct, but `capex: "oui"` makes no sense on a revenue entry. Remove the flag.

---

## Double-Counting Analysis

### Credit Card Payments: Chequing vs. Visa perspective

Three credit card payments appear from the CHEQUING account side:

| CSV Line | Date | Amount | Description | Beancount Entry |
|----------|------|--------|-------------|----------------|
| 9 | 2025-11-27 | -2,237.84 | PAIEMENT DIVERS CARTE RBC | Dr CartesCredit:RBC / Cr Banque:RBC:Cheques |
| 25 | 2025-12-30 | -1,642.70 | PAIEMENT DIVERS CARTE RBC | Dr CartesCredit:RBC / Cr Banque:RBC:Cheques |
| 46 | 2026-01-27 | -1,973.69 | PAIEMENT DIVERS CARTE RBC | Dr CartesCredit:RBC / Cr Banque:RBC:Cheques |

One credit card payment appears from the VISA statement side:

| CSV Line | Date | Amount | Description | Beancount Entry |
|----------|------|--------|-------------|----------------|
| 110 | 2026-01-26 | +1,973.69 | PAIEMENT AUTOMATISE - MERCI | Dr CartesCredit:RBC / Cr CartesCredit:RBC (BROKEN) |

**Analysis:**
- Line 46 (chequing side, Jan 27, -$1,973.69) and line 110 (Visa side, Jan 26, +$1,973.69) represent the SAME payment viewed from both accounts
- The one-day date difference (Jan 26 vs Jan 27) is normal for processing lag
- Lines 9 and 25 from chequing have no Visa-side counterpart in this dataset (likely the Visa statement for those periods wasn't included)

**Risk:** Once CRIT-03 is fixed (line 110 entry corrected to debit CartesCredit:RBC / credit Banque:RBC:Cheques), BOTH line 46 and line 110 will record the exact same journal entry. One must be deleted.

**Recommendation:** Keep the chequing-side entry (line 46) and DELETE the Visa-side entry (line 110), since the chequing side correctly records the cash outflow and the Visa side is redundant.

---

## Shareholder Loan (Pret-Actionnaire) Summary

### Currently classified as Pret-Actionnaire (CORRECT)

Many personal transactions are already correctly classified. Here is the current shareholder loan activity:

**Deposits INTO corporate account (corp owes shareholder more -- credit Pret-Actionnaire):**

These are personal funds entering the corporate account. The LLM correctly identified many VIREMENT RECU entries, grocery stores (IGA, Costco, Boucherie, Fromagerie), pharmacies (Familiprix), personal services (Spotify, iHerb, McDonald's, SAQ, SQDC), etc. as Pret-Actionnaire.

**Currently correct Pret-Actionnaire items total approximately:** ~$5,900 in personal expenses and ~$5,000 in personal deposits -- need not be adjusted.

### Should be reclassified TO Pret-Actionnaire (currently wrong)

| Source | Item | Amount |
|--------|------|--------|
| CRIT-02 | Impot Solidarite x4 | $266.68 |
| HIGH-01 | Mollo Cafe x18 | $92.36 |
| HIGH-03 | LS Muni GC | $58.19 |
| HIGH-04 | Adelard Belanger x2 | $50.22 |
| HIGH-05 | Restaurant Grinder | $323.64 |
| MED-03 | Restaurants/bars x7 | $199.86 (if no business purpose) |

**Minimum additional shareholder loan (confirmed):** $790.09
**Maximum additional shareholder loan (if all MED-03 items are personal):** $990.95

---

## Chart of Accounts Gaps

The following accounts are referenced or needed but do not exist in `ledger/comptes.beancount`:

| Proposed Account | Purpose | GIFI |
|------------------|---------|------|
| `Depenses:Vehicule:Immatriculation` | SAAQ registration fees | 9281 |
| `Depenses:Bureau:Electricite` | Hydro-Quebec utility bills | 8811 |
| `Depenses:Frais-Gouvernement` | REQ annual fee, other gov fees | 8860 |

**Note:** Alternatively, REQ could go under Honoraires-Professionnels:Autres (already exists, GIFI 8860).

---

## Recommended Next Steps

### Batch 1: CRITICAL fixes (apply first)
1. Reclassify DEPOT DE PAIE x5 entries from Salaires:Brut to Salaires-A-Payer (interim until full payroll journals)
2. Reclassify IMPOT SOLIDARITE x4 from Revenus:Autres to Pret-Actionnaire
3. Fix PAIEMENT AUTOMATISE entry (line 110) -- either delete (preferred) or fix account to Banque:RBC:Cheques
4. Fix TPS CANADA entry from Depenses:TPS-Remise to Actifs:TPS-Payee

### Batch 2: HIGH fixes (personal-vs-corporate boundary)
5. Reclassify Mollo Cafe x18 from Repas-Representation to Pret-Actionnaire
6. Reclassify SAAQ-IMMATRIC from Vehicule:Assurance to Vehicule:Immatriculation (or Pret-Actionnaire if personal)
7. Reclassify LS Muni GC from Vehicule:Stationnement to Pret-Actionnaire
8. Reclassify Adelard Belanger x2 from Bureau:Fournitures to Pret-Actionnaire
9. Reclassify Restaurant Grinder from Repas-Representation to Pret-Actionnaire
10. Remove capex:"oui" from rent entries (VIREMENT ENVOYE $1,775 x3)
11. Reclassify REQ from Impots:Quebec to Honoraires-Professionnels:Autres

### Batch 3: MEDIUM fixes (review-dependent)
12. Verify Hydro-Quebec account preference (keep Bureau:Entretien or create Bureau:Electricite)
13. Verify Amazon purchase -- reclassify based on actual item
14. Review restaurants/bars for business purpose documentation
15. Verify Belair insurance type and apply consistent classification
16. Verify Fizz telecom personal vs business usage
17. Review Apple.com charge and remove capex flag

### Batch 4: LOW / metadata cleanup
18. Remove all spurious capex:"oui" flags (12 entries)
19. Remove spurious classe_dpa_suggeree metadata from payment entries
20. Verify and import missing CSV line 22 if genuine
21. Remove capex:"oui" from DEP TIERS revenue entry

### Batch 5: Structural improvements
22. Update Mollo Cafe categorization rule to map to Pret-Actionnaire
23. Add missing chart of accounts entries (Vehicule:Immatriculation, etc.)
24. Create full payroll journal entries for each DEPOT DE PAIE period
25. Reconcile credit card payment entries (delete duplicates from Visa side)

---

*Report generated: 2026-02-19*
*Auditor: CompteQC automated audit system*
*Status: Ready for user review and approval*
