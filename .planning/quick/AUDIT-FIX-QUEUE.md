# Audit Fix Queue

Generated: 2026-02-20
Source: Quick Task 1 (Ledger Audit) + 5 parallel sub-agent audits

---

## Batch A: Code Bugs (no data changes, pure code fixes)

### A1. CRITICAL — Balance sheet `abs()` bug
- **File:** `src/compteqc/mcp/tools/ledger.py` line 193
- **Current:** `total_capitaux = sum(abs(v) for v in capitaux.values()) + resultat_net`
- **Fix:** `total_capitaux = sum(-v for v in capitaux.values()) + resultat_net`
- **Why:** `abs()` treats contra-equity accounts (Dividendes-Declares) as positive, breaking the accounting equation. Off by $219 on current data.

### A2. MEDIUM — Canada Employment Amount wrong
- **File:** `src/compteqc/quebec/paie/impot_federal.py` line 20
- **Current:** `CREDIT_EMPLOI_CANADA = Decimal("1428")`
- **Fix:** `CREDIT_EMPLOI_CANADA = Decimal("1501")`
- **Why:** T4127 122nd edition Table 8.2 says $1,501 for 2026. Causes ~$10/year over-withholding.

### A3. MEDIUM — Missing Quebec "deduction pour travailleur"
- **File:** `src/compteqc/quebec/paie/impot_quebec.py`
- **Fix:** Add $1,450 deduction (6% of eligible work income, max $1,450) before applying Quebec tax brackets
- **Why:** Causes ~$348/year over-withholding. Already has a TODO comment noting this omission.

### A4. LOW — Federal K constants off by $4-5
- **File:** `src/compteqc/quebec/rates.py` lines 139-154
- **Current → Fix:**
  - Bracket 3 K: `10237` → `10241`
  - Bracket 4 K: `15680` → `15685`
  - Bracket 5 K: `26019` → `26024`
- **Why:** ~$4/year max impact. Only affects salaries > $117K.

### A5. HIGH — Auto-approve threshold inconsistency
- **File 1:** `src/compteqc/categorisation/pipeline.py` line 185: uses `confiance > 0.95` (strict)
- **File 2:** `src/compteqc/mcp/tools/categorisation.py` line 112: uses `confiance >= 0.95`
- **Fix:** Harmonize both to `confiance > 0.95` (strict) for safety
- **Why:** MCP tool auto-approves at exactly 0.95, pipeline does not. Inconsistent behavior.

---

## Batch B: Categorization Pipeline Fixes (code changes affecting future imports)

### B1. CRITICAL — Fix Mollo Cafe rule
- **File:** `rules/categorisation.yaml`
- **Current:** `compte: Depenses:Repas-Representation` for `Mollo Cafe Montreal`
- **Fix:** `compte: Passifs:Pret-Actionnaire`
- **Why:** Personal daily coffee ($4-5) auto-approved as business meals. Will recur on every future import.

### B2. CRITICAL — Raise auto-rule generation threshold
- **File:** `src/compteqc/categorisation/feedback.py`
- **Current:** `SEUIL_AUTO_REGLE = 2`
- **Fix:** `SEUIL_AUTO_REGLE = 5`
- **Why:** Two wrong corrections create a permanent bad rule. 5 is a safer minimum.

### B3. HIGH — Fix LLM prompt contradictions
- **File:** `src/compteqc/categorisation/llm.py`
- **Fix 1:** Remove lines 103-105 that say "use Depenses:Salaires:Brut for DEPOT DE PAIE" — contradicts line 91 which says "NE PAS utiliser pour les imports bancaires"
- **Fix 2:** Add explicit guidance: "IMPOT SOLIDARITE GOUV. QUEBEC = personal tax credit, classify as Passifs:Pret-Actionnaire"
- **Fix 3:** Add guidance: large VIREMENT RECU (>$500) should get lower confidence (0.60) and flag for review
- **Fix 4:** Add known vendor corrections: "Adelard Belanger = grocery/food at Atwater Market, NOT office supplies"
- **Why:** Prompt is the root cause of systematic LLM misclassifications.

### B4. HIGH — Expand ML training to include Pret-Actionnaire
- **File:** `src/compteqc/categorisation/ml.py`
- **Current:** `_extraire_donnees_entrainement` only considers `Depenses:*` accounts
- **Fix:** Also include `Passifs:Pret-Actionnaire` as a trainable class
- **Why:** Personal expenses are the most common category but ML can never learn them.

### B5. MEDIUM — Add US SaaS vendor tax rules
- **File:** `rules/taxes.yaml`
- **Fix:** Add `tps_seulement` rules for: Anthropic, OpenRouter, Perplexity, Railway, Spotify, Microsoft
- **Why:** These US vendors should charge GST only (no QST). Currently only AWS is flagged.

---

## Batch C: Architecture / Tax Pipeline (larger changes)

### C1. CRITICAL — Build tax decomposition step in import pipeline
- **Files:** `src/compteqc/ingestion/rbc_carte.py`, `rbc_cheques.py`, `categorisation/pipeline.py`
- **What:** After categorization determines the expense account, call `determiner_traitement_depense()` then `extraire_taxes_selon_traitement()` to split transactions into 4 postings (base + TPS + TVQ)
- **Why:** TPS/TVQ is ALL ZEROS. No transaction posts to tax accounts. The tax calculation code exists but is never invoked during import. This means:
  - Zero ITCs being tracked (lost tax refunds)
  - Zero collected tax being tracked (compliance risk)
  - The sommaire TPS/TVQ report is useless
- **Scope:** Medium — the tax modules are already built, they just need to be wired into the pipeline

### C2. MEDIUM — Add year-carry-forward for shareholder loan
- **File:** `src/compteqc/quebec/pret_actionnaire/suivi.py` lines 110-117
- **Current:** Filters `entry.date.year != annee` — excludes all prior-year transactions
- **Fix:** Either remove the year filter or add opening balance carry-forward logic
- **Why:** 2025 shareholder loan activity ($3,247.90) is invisible to the tracker

### C3. MEDIUM — Add opening balance for bank account
- **File:** `ledger/main.beancount` or a new `ledger/2025/opening.beancount`
- **Fix:** Add pad/balance directive before first imported transaction (2025-11-05)
- **Why:** Bank account shows -$1,732.20 because prior balance was never recorded

---

## Batch D: Ledger Data Corrections (already partially done in quick-3)

Quick task 3 (commit cd6268c) already applied CRITICAL and HIGH corrections:
- Reclassified DEPOT DE PAIE x5 from Salaires:Brut to Salaires-A-Payer
- Reclassified IMPOT SOLIDARITE x4 from Revenus:Autres to Pret-Actionnaire
- Fixed PAIEMENT AUTOMATISE broken entry
- Fixed TPS CANADA from TPS-Remise to TPS-Payee
- Reclassified Mollo Cafe x18 from Repas-Representation to Pret-Actionnaire
- Fixed SAAQ from Vehicule:Assurance to proper account
- Fixed LS Muni GC from Vehicule:Stationnement to Pret-Actionnaire
- Fixed Adelard Belanger from Bureau:Fournitures to Pret-Actionnaire
- Fixed Restaurant Grinder from Repas-Representation to Pret-Actionnaire
- Removed capex flags from rent entries
- Fixed REQ from Impots:Quebec to Honoraires-Professionnels:Autres
- Removed 12 spurious capex flags

### Remaining data corrections (not yet applied):
- D1. Verify and import missing CSV line 22 (Dec 17 VIREMENT RECU $16.00)
- D2. Review Amazon $31.68 purchase — reclassify based on actual item
- D3. Review 7 restaurants/bars for business purpose documentation
- D4. Verify Belair insurance type (auto vs home) and apply consistent classification
- D5. Verify Fizz telecom personal vs business usage
- D6. Create full payroll journal entries for each DEPOT DE PAIE period
- D7. Delete duplicate CC payment entry (line 110 Visa side vs line 46 chequing side)

---

## Execution Order

1. **Batch A** (code bugs) — safe, no data impact, pure fixes
2. **Batch B** (categorization) — prevents future errors
3. **Batch D remaining** (data corrections) — requires user input for some items
4. **Batch C** (architecture) — larger scope, plan separately

---

## Reference: Sub-Agent Reports

- Balance sheet audit: Agent a8d5c43
- Payroll audit: Agent a3ce870
- TPS/TVQ audit: Agent acabaa9
- Shareholder loan audit: Agent afdc498
- Categorization audit: Agent a67a49c
- Original audit report: `.planning/quick/1-audit-and-fix-ledger-categorization-bala/AUDIT-REPORT.md`
