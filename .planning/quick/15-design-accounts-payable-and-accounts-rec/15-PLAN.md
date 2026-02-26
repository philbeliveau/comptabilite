---
phase: quick-15
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/design/accounts-payable-receivable.md
autonomous: true
requirements: [APAR-DESIGN]

must_haves:
  truths:
    - "Design document covers both AP and AR workflows for a Quebec solo IT consultant"
    - "Existing AR system (Actifs:ComptesClients, factures module) is analyzed and extended, not replaced"
    - "AP account structure is defined with correct GIFI codes"
    - "GST/QST handling is addressed for both invoices sent and bills received"
    - "Aging report logic is specified for both AP and AR"
    - "Integration points with existing import pipeline and Fava dashboard are identified"
  artifacts:
    - path: "docs/design/accounts-payable-receivable.md"
      provides: "Complete AP/AR design document"
      min_lines: 200
  key_links: []
---

<objective>
Design accounts payable (AP) and accounts receivable (AR) system for the Quebec-based solo IT consulting corporation.

Purpose: Produce a comprehensive design document that covers how AP/AR fits into the existing hledger/beancount-based ledger, what accounts are needed, workflows for tracking invoices and bills, aging reports, and Quebec-specific GST/QST considerations. This is a design-only deliverable -- no code changes.

Output: `docs/design/accounts-payable-receivable.md`
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@ledger/comptes.beancount
@src/compteqc/factures/modeles.py
@src/compteqc/factures/journal.py
@src/compteqc/factures/registre.py

<interfaces>
<!-- Existing AR system components the design must account for -->

From ledger/comptes.beancount:
```beancount
2025-01-01 open Actifs:ComptesClients CAD
  gifi: "1060"
; No AP account exists yet -- design must define one
```

From src/compteqc/factures/modeles.py:
```python
class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"

class Facture(BaseModel):
    numero: str  # e.g. "FAC-2026-001"
    nom_client: str
    adresse_client: str
    date: datetime.date
    date_echeance: datetime.date
    lignes: list[LigneFacture]
    statut: InvoiceStatus
    date_paiement: Optional[datetime.date]
```

From src/compteqc/factures/journal.py:
```python
def generer_ecriture_facture(facture: Facture) -> str:
    # Debit: Actifs:ComptesClients (total)
    # Credit: Revenus:Consultation (sous-total)
    # Credit: Passifs:TPS-Percue (TPS)
    # Credit: Passifs:TVQ-Percue (TVQ)

def generer_ecriture_paiement(facture: Facture) -> str:
    # Debit: Actifs:Banque:RBC:Cheques (total)
    # Credit: Actifs:ComptesClients (-total)
```

From src/compteqc/factures/registre.py:
```python
class RegistreFactures:
    # YAML-based invoice registry at ledger/factures/registre.yaml
    # Methods: ajouter, obtenir, lister, mettre_a_jour_statut, prochain_numero
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write AP/AR design document</name>
  <files>docs/design/accounts-payable-receivable.md</files>
  <action>
Create a comprehensive design document at `docs/design/accounts-payable-receivable.md` covering the following sections:

**1. Current State Analysis**
- Document the existing AR system: `Actifs:ComptesClients` account, Facture model, journal entry generation, YAML registry, invoice statuses (draft/sent/paid/overdue).
- Note what works well and what gaps exist (e.g., no aging calculation, no partial payment support, no recurring invoice concept).

**2. Accounts Payable -- New Capability**

2a. Account Structure:
- Define `Passifs:ComptesFournisseurs` (GIFI 2010 -- Accounts payable and accrued liabilities) for the chart of accounts.
- Optionally define sub-accounts if useful (e.g., by vendor category or by recurring vs one-time).
- Explain the AP journal entry pattern for a bill received:
  - Debit: Depenses:XXX (expense category) for the pre-tax amount
  - Debit: Actifs:TPS-Payee (ITC -- GST paid on purchases)
  - Debit: Actifs:TVQ-Payee (ITR -- QST paid on purchases)
  - Credit: Passifs:ComptesFournisseurs (total amount)
- Explain the payment entry:
  - Debit: Passifs:ComptesFournisseurs
  - Credit: Actifs:Banque:RBC:Cheques (or credit card)

2b. Bill Data Model:
- Design a `Facture Fournisseur` (vendor bill) model analogous to the existing Facture model.
- Fields: numero_reference (vendor's invoice number), fournisseur (vendor name), date_facture, date_echeance, montant_ht (pre-tax), tps, tvq, total, statut (received/approved/paid/disputed), categorie_depense (maps to chart of accounts), date_paiement, methode_paiement.
- Use Pydantic, consistent with existing Facture model patterns.

2c. Registry:
- Design a YAML-based bill registry analogous to RegistreFactures, stored at `ledger/fournisseurs/registre.yaml`.

**3. Accounts Receivable -- Enhancements to Existing**

3a. Aging Logic:
- Define aging buckets: Current (0-30 days), 30-60 days, 60-90 days, 90+ days.
- Specify how aging is calculated from `date_echeance` for unpaid invoices.
- Design an aging report output format (table with client, invoice number, amount, bucket).

3b. Partial Payments:
- Design how partial payments would work: add `montant_paye` field to Facture, generate partial payment journal entries reducing ComptesClients by the partial amount.
- Define a `PARTIAL` status or use paid amount vs total to determine status.

3c. Recurring Invoices:
- Design a recurring invoice template concept for the monthly consulting retainer pattern (common for solo consultants).
- Template stores: client info, line items, frequency (monthly), next generation date.

**4. GST/QST Considerations**

- AR side: Already handled (TPS-Percue, TVQ-Percue on invoice creation). Document the flow.
- AP side: ITCs (Input Tax Credits) for GST and ITRs (Input Tax Refunds) for QST. Explain how `Actifs:TPS-Payee` and `Actifs:TVQ-Payee` accumulate ITCs/ITRs from bills, and how these net against collected amounts at filing time.
- Note: Some expenses are not ITC/ITR eligible (meals at 50%, personal portion of mixed-use items). Design a `tps_applicable`/`tvq_applicable` flag per line, consistent with LigneFacture.

**5. Aging Reports**

- Design both AR aging and AP aging reports.
- AR aging: Outstanding invoices by client, bucketed by days past due.
- AP aging: Outstanding bills by vendor, bucketed by days past due.
- Summary: Total AR outstanding, total AP outstanding, net position.
- Output formats: CLI table output, Fava extension panel (future), CSV export for CPA.

**6. Integration Points**

- Transaction import pipeline: When a bank transaction matches a known AR invoice payment (by amount + client name), auto-suggest the payment journal entry linking to the invoice. Same for AP bill payments.
- AI categorization: When a new expense is categorized, if it has a future payment date or comes from a credit card statement with a different vendor invoice, suggest creating an AP entry.
- Fava dashboard: Describe a future dashboard panel showing AR/AP summary (total outstanding, overdue count, aging chart).
- MCP server: Describe tools for querying AR/AP status, creating bills, marking payments.

**7. Implementation Roadmap**

- Phase A: Add `Passifs:ComptesFournisseurs` to chart of accounts + bill data model + registry (mirrors existing facture pattern).
- Phase B: Add aging calculation logic for both AR and AP + CLI commands (`cqc fournisseur add`, `cqc fournisseur list`, `cqc fournisseur pay`).
- Phase C: Add recurring invoice templates + auto-matching in import pipeline.
- Phase D: Fava dashboard integration (AR/AP summary panel, aging chart).

Format the document with clear headers, code examples for Beancount journal entries, and Pydantic model sketches. Use French account names consistent with the existing chart of accounts. Write the document in English (design docs are for technical reference).
  </action>
  <verify>
    <automated>test -f docs/design/accounts-payable-receivable.md && wc -l docs/design/accounts-payable-receivable.md | awk '{if ($1 >= 200) print "PASS: " $1 " lines"; else print "FAIL: only " $1 " lines"}'</automated>
  </verify>
  <done>Design document exists at docs/design/accounts-payable-receivable.md with at least 200 lines covering: current AR analysis, new AP account structure with GIFI codes, bill data model, aging reports for both AR and AP, GST/QST ITC/ITR handling, integration points with existing pipeline, and phased implementation roadmap.</done>
</task>

</tasks>

<verification>
- Document covers all 7 major sections
- Beancount journal entry examples are syntactically correct (French account names, CAD currency)
- GIFI codes are referenced for new accounts
- Existing Facture/RegistreFactures patterns are respected and extended, not replaced
- GST/QST ITC/ITR flow is correctly described
</verification>

<success_criteria>
- Complete design document at docs/design/accounts-payable-receivable.md (200+ lines)
- AP account structure defined with correct GIFI codes
- AR enhancements (aging, partial payments, recurring) designed
- GST/QST handling specified for both sides
- Implementation roadmap with clear phases
</success_criteria>

<output>
After completion, create `.planning/quick/15-design-accounts-payable-and-accounts-rec/15-SUMMARY.md`
</output>
