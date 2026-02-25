---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - ledger/pending.beancount
  - ledger/2026/01.beancount
  - ledger/2026/02.beancount
  - ledger/comptes.beancount
autonomous: true
requirements: [AUDIT-FIX-01]

must_haves:
  truths:
    - "DEPOT DE PAIE entries credit Passifs:Salaires-A-Payer, not Depenses:Salaires:Brut"
    - "IMPOT SOLIDARITE entries credit Passifs:Pret-Actionnaire, not Revenus:Autres"
    - "PAIEMENT AUTOMATISE line 110 (Visa-side) is deleted -- chequing-side line 46 remains"
    - "TPS CANADA refund credits Actifs:TPS-Payee, not Depenses:TPS-Remise"
    - "Mollo Cafe x18 entries credit Passifs:Pret-Actionnaire, not Depenses:Repas-Representation"
    - "LS Muni GC, Adelard Belanger x2, Restaurant Grinder reclassified to Pret-Actionnaire"
    - "VIREMENT ENVOYE rent entries (x3) have capex:oui flag removed"
    - "REQ annual fee reclassified from Impots:Quebec to Honoraires-Professionnels:Autres"
    - "All spurious capex:oui flags removed from non-capital entries (12 entries)"
    - "SAAQ-IMMATRIC reclassified from Vehicule:Assurance to Vehicule:Immatriculation"
    - "Depenses:Vehicule:Immatriculation account exists in comptes.beancount"
  artifacts:
    - path: "ledger/pending.beancount"
      provides: "Corrected critical and high-severity transaction entries"
    - path: "ledger/2026/01.beancount"
      provides: "Corrected Mollo Cafe entries for January"
    - path: "ledger/2026/02.beancount"
      provides: "Corrected Mollo Cafe entries for February"
    - path: "ledger/comptes.beancount"
      provides: "New Depenses:Vehicule:Immatriculation account"
  key_links:
    - from: "DEPOT DE PAIE entries (pending:19, 76, 145, 269, 529)"
      to: "Passifs:Salaires-A-Payer"
      via: "credit posting change"
      pattern: "Passifs:Salaires-A-Payer"
    - from: "IMPOT SOLIDARITE entries (pending:8, 167, 348, 607)"
      to: "Passifs:Pret-Actionnaire"
      via: "credit posting change"
      pattern: "Passifs:Pret-Actionnaire"
---

<objective>
Apply CRITICAL and HIGH severity corrections from the ledger audit report to pending.beancount, 01.beancount, and 02.beancount, plus metadata cleanup (LOW) and chart-of-accounts additions.

Purpose: The audit identified $2,964.56 in critical misclassifications and ~$1,610 in high-severity personal-vs-corporate violations. These corrections are needed for accurate financial statements and CPA review.
Output: Corrected ledger files with all Batch 1, 2, and 4 fixes applied, plus one new account in comptes.beancount.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/quick/1-audit-and-fix-ledger-categorization-bala/AUDIT-REPORT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Apply Batch 1 CRITICAL fixes to pending.beancount</name>
  <files>ledger/pending.beancount</files>
  <action>
Read ledger/pending.beancount in full, then apply all four CRITICAL corrections exactly as specified in AUDIT-REPORT.md:

CRIT-01 -- DEPOT DE PAIE x5 (pending lines ~19, 76, 145, 269, 529):
Change the credit posting from `Depenses:Salaires:Brut` to `Passifs:Salaires-A-Payer` on each of the 5 entries. Also remove the spurious `capex: "oui"` metadata from the line 3 entry (2025-11-06 $522.67). The debit (Actifs:Banque:RBC:Cheques) is correct and must not change.

CRIT-02 -- IMPOT SOLIDARITE x4 (pending lines ~8, 167, 348, 607):
Change the credit posting from `Revenus:Autres` to `Passifs:Pret-Actionnaire` on each of the 4 entries. The debit (Actifs:Banque:RBC:Cheques) is correct and must not change.

CRIT-03 -- PAIEMENT AUTOMATISE (pending line ~1147, 2026-01-26, $1,973.69):
DELETE this entire transaction block (the Visa-side entry with both legs to Passifs:CartesCredit:RBC). The chequing-side entry (PAIEMENT DIVERS CARTE RBC, line 46, ~pending:493) already records this payment correctly and must remain untouched.

CRIT-04 -- TPS CANADA (pending line ~359, 2026-01-05, $89.56):
Change the credit posting from `Depenses:TPS-Remise` to `Actifs:TPS-Payee`. The debit (Actifs:Banque:RBC:Cheques) is correct and must not change.
  </action>
  <verify>Run: python -m beancount.scripts.bean_check ledger/main.beancount 2>&1 | head -40
Expected: no errors (or only pre-existing errors unrelated to these entries).</verify>
  <done>All 5 DEPOT DE PAIE entries credit Passifs:Salaires-A-Payer; all 4 IMPOT SOLIDARITE entries credit Passifs:Pret-Actionnaire; PAIEMENT AUTOMATISE Visa-side entry is absent; TPS CANADA entry credits Actifs:TPS-Payee.</done>
</task>

<task type="auto">
  <name>Task 2: Apply Batch 2 HIGH fixes and Batch 4 metadata cleanup across all ledger files</name>
  <files>ledger/pending.beancount, ledger/2026/01.beancount, ledger/2026/02.beancount, ledger/comptes.beancount</files>
  <action>
Read each file, apply the following corrections, then write back.

--- HIGH fixes in pending.beancount ---

HIGH-01 Mollo Cafe -- NOT in pending.beancount (those are in 01.beancount / 02.beancount -- handled below).

HIGH-02 SAAQ-IMMATRIC (pending line ~506, 2026-01-27, $400.86):
Change `Depenses:Vehicule:Assurance` to `Depenses:Vehicule:Immatriculation` (account to be added in comptes.beancount).

HIGH-03 LS Muni GC (pending line ~850, 2026-01-11, $58.19):
Change `Depenses:Vehicule:Stationnement` to `Passifs:Pret-Actionnaire`.

HIGH-04 Adelard Belanger x2 (pending lines ~806 and ~1092):
Change `Depenses:Bureau:Fournitures` to `Passifs:Pret-Actionnaire` on both entries.

HIGH-05 Restaurant Grinder (pending line ~1480, 2026-02-13, $323.64):
Change `Depenses:Repas-Representation` to `Passifs:Pret-Actionnaire`.

HIGH-06 VIREMENT ENVOYE rent x3 (pending lines ~122, 314, 573):
Remove the `capex: "oui"` metadata line from each of the three $1,775.00 rent entries. Account classification (Depenses:Bureau:Loyer) is correct -- do not change it.

HIGH-07 REQ annual fee (pending line ~707, 2026-01-06, $41.00):
Change `Depenses:Impots:Quebec` to `Depenses:Honoraires-Professionnels:Autres`.

--- HIGH fixes in 01.beancount and 02.beancount ---

HIGH-01 Mollo Cafe x9 in 01.beancount (dates: 2026-01-07, 01-13 x2, 01-20, 01-21, 01-26, 01-27, 01-28, 01-29):
Change `Depenses:Repas-Representation` to `Passifs:Pret-Actionnaire` on all 9 entries.

HIGH-01 Mollo Cafe x9 in 02.beancount (dates: 2026-02-01, 02-02, 02-03, 02-04, 02-09, 02-10, 02-12, 02-16, 02-17):
Change `Depenses:Repas-Representation` to `Passifs:Pret-Actionnaire` on all 9 entries.

--- Batch 4 metadata cleanup in pending.beancount ---

Remove spurious `capex: "oui"` and `classe_dpa_suggeree: "10"` metadata from these entries (by payee/date -- identify each block by the ligne: metadata which matches the CSV line numbers):

Entries where capex flag must be removed (already corrected entries above do not need this step again; focus on remaining ones):
- ligne: "6" (2025-11-17, VIREMENT RECU $2,195) -- remove capex:"oui"
- ligne: "9" (2025-11-27, PAIEMENT CARTE RBC) -- remove capex:"oui" and classe_dpa_suggeree:"10"
- ligne: "20" (2025-12-15, VIREMENT RECU $500) -- remove capex:"oui"
- ligne: "25" (2025-12-30, PAIEMENT CARTE RBC) -- remove capex:"oui" and classe_dpa_suggeree:"10"
- ligne: "27" (2026-01-02, VIREMENT RECU $700) -- remove capex:"oui"
- ligne: "38" (2026-01-12, DEP TIERS W3-3019 $2,250 revenue) -- remove capex:"oui"
- ligne: "42" (2026-01-19, VIREMENT RECU $900) -- remove capex:"oui"
- ligne: "46" (2026-01-27, PAIEMENT CARTE RBC $1,973.69) -- remove capex:"oui" and classe_dpa_suggeree:"10"
- ligne: "48" (2026-01-28, VIREMENT RECU $500) -- remove capex:"oui"
- ligne: "59" (2026-02-13, VIREMENT RECU $900) -- remove capex:"oui"
- ligne: "111" (2026-01-26, Apple.com/Bill $1.48) -- remove capex:"oui" only (keep Abonnements-Logiciels account)

Note: CRIT-03 (ligne: "110") has already been deleted in Task 1, so skip it here.

--- Add new account to comptes.beancount ---

Find the `Depenses:Vehicule` account block in comptes.beancount. Add after the existing Vehicule sub-accounts:
```
2020-01-01 open Depenses:Vehicule:Immatriculation  CAD
  description: "Frais d'immatriculation SAAQ"
```
Use the same open date as the other Vehicule accounts in that file.
  </action>
  <verify>Run: python -m beancount.scripts.bean_check ledger/main.beancount 2>&1 | head -40
Also spot-check: grep -n "Mollo" ledger/2026/01.beancount ledger/2026/02.beancount | head -20 (should show Passifs:Pret-Actionnaire)
And: grep -n "capex" ledger/pending.beancount | wc -l (should be much lower than before)</verify>
  <done>No new beancount errors; Mollo Cafe entries show Pret-Actionnaire; all 11 spurious capex flags are gone from non-capital entries; Depenses:Vehicule:Immatriculation account exists in comptes.beancount; SAAQ entry uses the new account.</done>
</task>

</tasks>

<verification>
After both tasks:
1. `python -m beancount.scripts.bean_check ledger/main.beancount` -- no new errors
2. Grep confirms: no IMPOT SOLIDARITE entry credits Revenus:Autres
3. Grep confirms: no DEPOT DE PAIE entry credits Depenses:Salaires:Brut
4. Grep confirms: PAIEMENT AUTOMATISE (Visa-side) transaction block is absent from pending.beancount
5. Grep confirms: TPS CANADA entry credits Actifs:TPS-Payee
6. Grep confirms: all 18 Mollo Cafe entries credit Passifs:Pret-Actionnaire
</verification>

<success_criteria>
- All 4 CRITICAL issues resolved in pending.beancount
- All 7 HIGH issues resolved across pending.beancount, 01.beancount, 02.beancount
- All Batch 4 metadata flags cleaned (12 capex entries, 4 classe_dpa entries)
- Depenses:Vehicule:Immatriculation added to comptes.beancount
- bean_check passes with no new errors
- $2,964.56 in critical misclassifications corrected; ~$1,610 in high-severity issues corrected
</success_criteria>

<output>
After completion, create `.planning/quick/3-fix-ledger-issues-from-audit/3-SUMMARY.md` using the summary template.
</output>
