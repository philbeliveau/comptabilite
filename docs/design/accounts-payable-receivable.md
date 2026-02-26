# Accounts Payable and Accounts Receivable Design

Design document for AP/AR system integration into the CompteQC accounting stack
for a Quebec-based solo IT consulting corporation (CCPC).

---

## 1. Current State Analysis

### Existing Accounts Receivable System

The AR system is already functional with these components:

**Account:** `Actifs:ComptesClients` (GIFI 1060) -- opened in `ledger/comptes.beancount`.

**Data Model** (`src/compteqc/factures/modeles.py`):

- `Facture` -- full invoice with client info, line items, tax calculation, and status tracking.
- `LigneFacture` -- individual line item with quantity, unit price, and per-line tax applicability flags (`tps_applicable`, `tvq_applicable`).
- `InvoiceStatus` -- enum with `DRAFT`, `SENT`, `PAID`, `OVERDUE`.
- Tax calculation is automatic: GST at 5%, QST at 9.975%, computed on applicable lines only.

**Journal Entry Generation** (`src/compteqc/factures/journal.py`):

- `generer_ecriture_facture()` -- creates AR entry on invoice issuance:
  - Debit `Actifs:ComptesClients` (total including taxes)
  - Credit `Revenus:Consultation` (pre-tax subtotal)
  - Credit `Passifs:TPS-Percue` (GST collected)
  - Credit `Passifs:TVQ-Percue` (QST collected)
- `generer_ecriture_paiement()` -- creates payment entry:
  - Debit `Actifs:Banque:RBC:Cheques` (total)
  - Credit `Actifs:ComptesClients` (total)

**Registry** (`src/compteqc/factures/registre.py`):

- `RegistreFactures` -- YAML-based persistence at `ledger/factures/registre.yaml`.
- Operations: `ajouter`, `obtenir`, `lister`, `mettre_a_jour_statut`, `prochain_numero`.
- Sequential numbering: `FAC-YYYY-NNN`.

### Gaps in the Existing AR System

| Gap | Impact | Priority |
|-----|--------|----------|
| No aging calculation | Cannot report overdue amounts by bucket | High |
| No partial payment support | All-or-nothing payment; cannot record installments | Medium |
| No recurring invoice concept | Must manually create monthly retainer invoices | Medium |
| No auto-matching with bank imports | Payment recording is fully manual | Medium |
| Revenue account is hardcoded to `Revenus:Consultation` | Cannot handle Enact product revenue | Low |

### Accounts Payable -- Not Yet Implemented

No AP account exists in the chart of accounts. No bill tracking, no vendor registry, no
ITC/ITR tracking workflow. All expense recording currently goes directly to expense
accounts without an intermediate payable.

---

## 2. Accounts Payable -- New Capability

### 2a. Account Structure

**New account to add to `ledger/comptes.beancount`:**

```beancount
; Accounts Payable -- vendor bills awaiting payment
2025-01-01 open Passifs:ComptesFournisseurs CAD
  gifi: "2010"
```

GIFI 2010 = "Accounts payable and accrued liabilities" -- the standard CRA mapping for
trade payables.

**Optional sub-accounts** (recommended for clarity):

```beancount
; Sub-accounts by vendor type (optional, use if volume warrants it)
2025-01-01 open Passifs:ComptesFournisseurs:Fournisseurs-Reguliers CAD
  gifi: "2010"
2025-01-01 open Passifs:ComptesFournisseurs:Cartes-Credit CAD
  gifi: "2010"
```

For a solo consultant, the flat `Passifs:ComptesFournisseurs` account is likely
sufficient. Sub-accounts can be added later if vendor volume increases.

**Journal Entry Pattern -- Bill Received:**

When a vendor bill (e.g., accountant invoice, software subscription, office supplies)
is recorded:

```beancount
2026-02-15 * "Facture fournisseur FOUR-2026-001 - Cabinet Comptable XYZ"
  Depenses:Honoraires-Professionnels:Comptable  1000.00 CAD
  Actifs:TPS-Payee                                 50.00 CAD
  Actifs:TVQ-Payee                                 99.75 CAD
  Passifs:ComptesFournisseurs                   -1149.75 CAD
```

Breakdown:
- **Debit** `Depenses:XXX` -- pre-tax expense amount mapped to chart of accounts
- **Debit** `Actifs:TPS-Payee` -- GST paid, accumulates as Input Tax Credit (ITC)
- **Debit** `Actifs:TVQ-Payee` -- QST paid, accumulates as Input Tax Refund (ITR)
- **Credit** `Passifs:ComptesFournisseurs` -- total amount owed to vendor

**Journal Entry Pattern -- Bill Payment:**

When the bill is paid:

```beancount
2026-03-01 * "Paiement facture fournisseur FOUR-2026-001 - Cabinet Comptable XYZ"
  Passifs:ComptesFournisseurs   1149.75 CAD
  Actifs:Banque:RBC:Cheques    -1149.75 CAD
```

For credit card payments:

```beancount
2026-03-01 * "Paiement facture fournisseur FOUR-2026-001 - Cabinet Comptable XYZ"
  Passifs:ComptesFournisseurs   1149.75 CAD
  Passifs:CartesCredit:RBC     -1149.75 CAD
```

### 2b. Bill Data Model

A new `FactureFournisseur` (vendor bill) model, mirroring the existing `Facture` pattern:

```python
"""Modeles de donnees pour les factures fournisseurs (AP)."""

from __future__ import annotations

import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator

from compteqc.factures.modeles import TAUX_TPS, TAUX_TVQ, QUANTIZE_CENT


class BillStatus(str, Enum):
    """Statut d'une facture fournisseur."""

    RECEIVED = "received"     # Bill received, not yet approved
    APPROVED = "approved"     # Approved for payment
    PAID = "paid"             # Fully paid
    PARTIAL = "partial"       # Partially paid
    DISPUTED = "disputed"     # Under dispute with vendor


class LigneFactureFournisseur(BaseModel):
    """Ligne d'une facture fournisseur."""

    description: str
    montant: Decimal  # Pre-tax amount for this line
    categorie_depense: str  # Maps to chart of accounts, e.g. "Depenses:Bureau:Abonnements-Logiciels"
    tps_applicable: bool = True
    tvq_applicable: bool = True

    @field_validator("montant", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v


class FactureFournisseur(BaseModel):
    """Facture fournisseur (vendor bill) for accounts payable tracking."""

    numero_reference: str          # Vendor's invoice number
    numero_interne: str            # Internal tracking number, e.g. "FOUR-2026-001"
    fournisseur: str               # Vendor name
    date_facture: datetime.date    # Invoice date
    date_echeance: datetime.date   # Due date
    lignes: list[LigneFactureFournisseur]
    statut: BillStatus = BillStatus.RECEIVED
    date_paiement: Optional[datetime.date] = None
    methode_paiement: Optional[str] = None  # "cheque", "virement", "carte-credit"
    montant_paye: Decimal = Decimal("0")
    notes: str = ""

    @field_validator("montant_paye", mode="before")
    @classmethod
    def _coerce_decimal(cls, v: object) -> Decimal:
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v

    @property
    def montant_ht(self) -> Decimal:
        """Total pre-tax amount across all lines."""
        return sum((l.montant for l in self.lignes), Decimal("0"))

    @property
    def tps(self) -> Decimal:
        """GST (5%) on applicable lines."""
        base = sum(
            (l.montant for l in self.lignes if l.tps_applicable),
            Decimal("0"),
        )
        return (base * TAUX_TPS).quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    @property
    def tvq(self) -> Decimal:
        """QST (9.975%) on applicable lines."""
        base = sum(
            (l.montant for l in self.lignes if l.tvq_applicable),
            Decimal("0"),
        )
        return (base * TAUX_TVQ).quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    @property
    def total(self) -> Decimal:
        """Total amount including taxes."""
        return self.montant_ht + self.tps + self.tvq

    @property
    def solde(self) -> Decimal:
        """Outstanding balance (total - amount paid)."""
        return self.total - self.montant_paye
```

### 2c. Registry

A YAML-based bill registry, mirroring `RegistreFactures`:

```python
class RegistreFournisseurs:
    """Registre de factures fournisseurs persistant en YAML."""

    def __init__(self, chemin: Path | None = None) -> None:
        self.chemin = chemin or Path("ledger/fournisseurs/registre.yaml")
        self._factures: list[FactureFournisseur] = []
        self._charger()

    # Same pattern as RegistreFactures:
    # _charger(), _sauvegarder(), ajouter(), obtenir(), lister(),
    # mettre_a_jour_statut(), prochain_numero()

    def prochain_numero(self, annee: int) -> str:
        """Next internal bill number: FOUR-YYYY-NNN."""
        prefix = f"FOUR-{annee}-"
        numeros_existants = [
            int(f.numero_interne.replace(prefix, ""))
            for f in self._factures
            if f.numero_interne.startswith(prefix)
        ]
        prochain = max(numeros_existants, default=0) + 1
        return f"{prefix}{prochain:03d}"

    def lister_impayees(self) -> list[FactureFournisseur]:
        """List unpaid or partially paid bills."""
        return [
            f for f in self._factures
            if f.statut in (BillStatus.RECEIVED, BillStatus.APPROVED, BillStatus.PARTIAL)
        ]
```

**Storage location:** `ledger/fournisseurs/registre.yaml`

This mirrors the existing `ledger/factures/registre.yaml` pattern, keeping AP and AR
registries as sibling directories under `ledger/`.

---

## 3. Accounts Receivable -- Enhancements to Existing

### 3a. Aging Logic

**Aging Buckets:**

| Bucket | Days Past Due |
|--------|---------------|
| Current | 0-30 days |
| 30-60 | 31-60 days |
| 60-90 | 61-90 days |
| 90+ | 91+ days |

**Calculation logic:**

```python
from datetime import date

def calculer_age_jours(date_echeance: date, date_reference: date | None = None) -> int:
    """Calculate days past due. Negative means not yet due."""
    ref = date_reference or date.today()
    return (ref - date_echeance).days

def classifier_age(jours: int) -> str:
    """Classify into aging bucket."""
    if jours <= 30:
        return "current"
    elif jours <= 60:
        return "30-60"
    elif jours <= 90:
        return "60-90"
    else:
        return "90+"
```

**Aging Report Output Format:**

```
AR Aging Report as of 2026-02-26
=================================

Client              Invoice       Amount     Bucket    Days Past Due
-----------------   ----------    --------   -------   -------------
Acme Corp           FAC-2026-001  5,750.00   Current           12
Beta Inc            FAC-2026-002  8,625.00   30-60             45
Gamma Ltd           FAC-2025-011  3,450.00   90+              120

Summary:
  Current (0-30):     $5,750.00
  30-60 days:         $8,625.00
  60-90 days:             $0.00
  90+ days:           $3,450.00
  ---------------------------
  Total Outstanding: $17,825.00
```

### 3b. Partial Payments

**Model enhancement** -- add `montant_paye` to `Facture`:

```python
class Facture(BaseModel):
    # ... existing fields ...
    montant_paye: Decimal = Decimal("0")  # NEW: accumulated partial payments

    @property
    def solde(self) -> Decimal:
        """Outstanding balance."""
        return self.total - self.montant_paye

    @property
    def est_paye_integralement(self) -> bool:
        """True if fully paid (balance is zero or negative)."""
        return self.solde <= 0
```

**Status derivation** -- instead of adding a `PARTIAL` enum value, derive status from
the payment state to keep the model simple:

```python
def determiner_statut(facture: Facture, date_reference: date | None = None) -> InvoiceStatus:
    """Determine invoice status based on payment and due date."""
    if facture.est_paye_integralement:
        return InvoiceStatus.PAID
    ref = date_reference or date.today()
    if ref > facture.date_echeance:
        return InvoiceStatus.OVERDUE
    if facture.statut == InvoiceStatus.DRAFT:
        return InvoiceStatus.DRAFT
    return InvoiceStatus.SENT
```

If a `PARTIAL` status is needed for explicit UI display, it can be added to the
`InvoiceStatus` enum:

```python
class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIAL = "partial"   # NEW
    PAID = "paid"
    OVERDUE = "overdue"
```

**Partial Payment Journal Entry:**

```beancount
2026-02-20 * "Paiement partiel facture FAC-2026-002 - Beta Inc"
  Actifs:Banque:RBC:Cheques   3000.00 CAD
  Actifs:ComptesClients       -3000.00 CAD
```

The `ComptesClients` balance for this invoice decreases by the partial amount.
The remaining balance stays in AR until the next payment.

### 3c. Recurring Invoices

**Template Model:**

```python
class ModeleFactureRecurrente(BaseModel):
    """Template for generating recurring invoices (e.g., monthly retainer)."""

    identifiant: str              # e.g. "REC-ACME-MENSUEL"
    nom_client: str
    adresse_client: str = ""
    lignes: list[LigneFacture]    # Reuse existing LigneFacture
    frequence: str = "mensuel"    # "mensuel", "trimestriel", "annuel"
    jour_generation: int = 1      # Day of month/quarter to generate
    prochaine_generation: datetime.date  # Next generation date
    actif: bool = True
    notes: str = ""
```

**Workflow:**

1. User creates a recurring template via CLI: `cqc facture template add`
2. System stores template in `ledger/factures/modeles-recurrents.yaml`
3. On the generation date (or when user runs `cqc facture generate-recurring`):
   - Create a new `Facture` from the template
   - Assign next sequential number (`FAC-YYYY-NNN`)
   - Set `date_echeance` based on standard payment terms (Net 30)
   - Add to `RegistreFactures`
   - Generate the Beancount journal entry
   - Advance `prochaine_generation` to next period

**Common use case:** Monthly consulting retainer of $X per month to a single client.
The template eliminates repetitive invoice creation.

---

## 4. GST/QST Considerations

### AR Side -- Already Implemented

The existing system correctly handles tax collection on invoices:

```
Invoice issued:
  Debit  Actifs:ComptesClients        $1,149.75  (total)
  Credit Revenus:Consultation         $1,000.00  (pre-tax)
  Credit Passifs:TPS-Percue              $50.00  (5% GST collected)
  Credit Passifs:TVQ-Percue              $99.75  (9.975% QST collected)
```

`Passifs:TPS-Percue` and `Passifs:TVQ-Percue` accumulate collected taxes as
liabilities to be remitted to CRA and Revenu Quebec.

### AP Side -- New ITC/ITR Tracking

When the corporation pays GST/QST on business purchases, it can claim:
- **Input Tax Credits (ITCs)** for GST paid -- via `Actifs:TPS-Payee`
- **Input Tax Refunds (ITRs)** for QST paid -- via `Actifs:TVQ-Payee`

These accounts already exist in the chart of accounts (GIFI 1300).

```
Bill recorded:
  Debit  Depenses:Bureau:Abonnements-Logiciels  $100.00  (pre-tax)
  Debit  Actifs:TPS-Payee                          $5.00  (ITC)
  Debit  Actifs:TVQ-Payee                          $9.98  (ITR)
  Credit Passifs:ComptesFournisseurs             -$114.98  (total)
```

### Net Remittance Calculation

At GST/QST filing time (quarterly or annually):

```
GST Net Remittance = Passifs:TPS-Percue (collected) - Actifs:TPS-Payee (paid)
QST Net Remittance = Passifs:TVQ-Percue (collected) - Actifs:TVQ-Payee (paid)
```

If net is positive: corporation owes the government.
If net is negative: corporation gets a refund.

**Filing journal entry example (GST):**

```beancount
2026-04-30 * "Remise TPS T1 2026 - Trimestre 1"
  Passifs:TPS-Percue            2500.00 CAD  ; Clear collected GST
  Actifs:TPS-Payee              -800.00 CAD  ; Clear ITCs claimed
  Actifs:Banque:RBC:Cheques    -1700.00 CAD  ; Net payment to CRA
```

### Expenses with Restricted ITC/ITR Eligibility

Some expenses have limited or no ITC/ITR eligibility:

| Expense Type | ITC/ITR Rate | Notes |
|-------------|--------------|-------|
| Meals and entertainment | 50% | Only 50% of GST/QST is claimable as ITC/ITR |
| Personal portion of mixed-use | 0% | e.g., personal use portion of vehicle |
| Club memberships | 0% | Not eligible for ITC/ITR |
| Most business expenses | 100% | Full ITC/ITR available |

**Per-line tax applicability** is already supported via `tps_applicable` and
`tvq_applicable` flags on `LigneFacture` and `LigneFactureFournisseur`. For the
50% meals case, the recommended approach is:

```python
class LigneFactureFournisseur(BaseModel):
    # ... existing fields ...
    tps_applicable: bool = True
    tvq_applicable: bool = True
    taux_itc: Decimal = Decimal("1.0")  # 1.0 = 100%, 0.5 = 50% (meals)
    taux_itr: Decimal = Decimal("1.0")  # Same for QST
```

This allows the journal entry generator to compute:
- ITC = GST amount * `taux_itc`
- ITR = QST amount * `taux_itr`
- Non-claimable portion goes to the expense account directly.

**Example -- Meals at 50%:**

```beancount
2026-02-20 * "Repas client - Restaurant Le Festin"
  Depenses:Repas-Representation   50.00 CAD  ; Pre-tax
  Actifs:TPS-Payee                 1.25 CAD  ; 50% of $2.50 GST (ITC)
  Depenses:Repas-Representation    1.25 CAD  ; 50% non-claimable GST -> expense
  Actifs:TVQ-Payee                 2.49 CAD  ; 50% of $4.99 QST (ITR)
  Depenses:Repas-Representation    2.50 CAD  ; 50% non-claimable QST -> expense
  Passifs:ComptesFournisseurs    -57.49 CAD  ; Total
```

---

## 5. Aging Reports

### AR Aging Report

**Purpose:** Show outstanding customer invoices bucketed by days past due date.

**Data source:** `RegistreFactures.lister()` filtered to non-paid invoices.

**Columns:**

| Column | Source |
|--------|--------|
| Client | `facture.nom_client` |
| Invoice # | `facture.numero` |
| Invoice Date | `facture.date` |
| Due Date | `facture.date_echeance` |
| Total | `facture.total` |
| Paid | `facture.montant_paye` |
| Outstanding | `facture.solde` |
| Days Past Due | `(reference_date - date_echeance).days` |
| Bucket | Current / 30-60 / 60-90 / 90+ |

**Summary section:**

```
AR Aging Summary
  Current (0-30 days):  $XX,XXX.XX  (N invoices)
  31-60 days:           $XX,XXX.XX  (N invoices)
  61-90 days:           $XX,XXX.XX  (N invoices)
  91+ days:             $XX,XXX.XX  (N invoices)
  ----------------------------------------
  Total AR Outstanding: $XX,XXX.XX  (N invoices)
```

### AP Aging Report

**Purpose:** Show outstanding vendor bills bucketed by days past due date.

**Data source:** `RegistreFournisseurs.lister_impayees()`

**Columns:** Same structure as AR, but with vendor name instead of client name.

| Column | Source |
|--------|--------|
| Vendor | `facture.fournisseur` |
| Bill # | `facture.numero_interne` |
| Vendor Ref | `facture.numero_reference` |
| Bill Date | `facture.date_facture` |
| Due Date | `facture.date_echeance` |
| Total | `facture.total` |
| Paid | `facture.montant_paye` |
| Outstanding | `facture.solde` |
| Days Past Due | `(reference_date - date_echeance).days` |
| Bucket | Current / 30-60 / 60-90 / 90+ |

### Combined AP/AR Summary

```
AP/AR Position as of 2026-02-26
================================

Total Accounts Receivable:  $17,825.00  (3 invoices outstanding)
Total Accounts Payable:      $4,299.50  (2 bills outstanding)
                            ----------
Net Position (AR - AP):     $13,525.50

Cash Impact Next 30 Days:
  Expected collections:      $5,750.00  (1 invoice current)
  Expected payments:         $2,149.75  (1 bill due)
  Net cash flow:             $3,600.25
```

### Output Formats

| Format | Use Case | Implementation |
|--------|----------|----------------|
| CLI table | Quick check via `cqc aging ar` / `cqc aging ap` | Rich or tabulate library |
| CSV export | CPA deliverable package | Standard CSV with headers |
| Fava extension panel | Dashboard integration (future) | HTML table in extension template |
| JSON endpoint | MCP server queries | FastAPI/Fava JSON endpoint |

---

## 6. Integration Points

### 6.1 Transaction Import Pipeline

**Current flow:** Bank CSV -> normalize -> AI categorize -> Beancount entry.

**AR auto-matching enhancement:**

When a bank deposit is imported:
1. Check amount against outstanding AR invoices (from `RegistreFactures`)
2. If exact match on amount + client name pattern: auto-suggest payment entry
3. If close match (within $0.01 tolerance for rounding): suggest with lower confidence
4. Generate: `generer_ecriture_paiement(facture)` and mark invoice as paid

```python
def suggerer_rapprochement_ar(
    transaction: TransactionImportee,
    registre: RegistreFactures,
) -> list[tuple[Facture, float]]:
    """Suggest AR invoice matches for an imported bank deposit.

    Returns list of (invoice, confidence_score) tuples.
    """
    suggestions = []
    for facture in registre.lister_impayees():
        score = 0.0
        # Amount match (highest weight)
        if abs(transaction.montant - facture.solde) < Decimal("0.02"):
            score += 0.7
        # Client name match (fuzzy)
        if similarity(transaction.description, facture.nom_client) > 0.6:
            score += 0.3
        if score > 0.5:
            suggestions.append((facture, score))
    return sorted(suggestions, key=lambda x: x[1], reverse=True)
```

**AP auto-matching enhancement:**

When a bank withdrawal or credit card charge is imported:
1. Check amount against outstanding AP bills (from `RegistreFournisseurs`)
2. If exact match on amount + vendor name: auto-suggest AP payment entry
3. Generate payment entry clearing `Passifs:ComptesFournisseurs`

### 6.2 AI Categorization Integration

**Current flow:** Transaction -> LLM categorization -> expense account suggestion.

**AP creation trigger:**

When the AI categorizer encounters a transaction that suggests an unpaid bill:
- Credit card statement entry with a vendor invoice reference
- Bank debit matching a known recurring vendor
- The system can suggest creating an AP entry if the vendor has not yet been recorded

**Workflow:**

```
Transaction imported -> AI categorizes as "Depenses:Honoraires-Professionnels:Comptable"
  -> System checks: Is there an open AP bill from this vendor for this amount?
     -> YES: Suggest linking as AP payment (clear ComptesFournisseurs)
     -> NO:  Create direct expense entry (skip AP for simple transactions)
             OR suggest creating AP bill if invoice date differs from payment date
```

**Heuristic:** For a solo consultant, most expenses are paid immediately (credit card,
bank transfer). AP is primarily useful for:
- Professional fees (accountant, lawyer) billed Net 30
- Large purchases with payment terms
- Any bill received before payment date

### 6.3 Fava Dashboard Integration

**New dashboard panel: AP/AR Summary**

Add to the existing CompteQC Fava extension:

```
+------------------------------------------+
|  Accounts Receivable / Accounts Payable  |
+------------------------------------------+
|                                          |
|  AR Outstanding:     $17,825.00          |
|  AR Overdue:          $3,450.00  (1)     |
|                                          |
|  AP Outstanding:      $4,299.50          |
|  AP Overdue:              $0.00  (0)     |
|                                          |
|  Net Position:       $13,525.50          |
|                                          |
|  [View AR Aging]  [View AP Aging]        |
+------------------------------------------+
```

**Aging chart (Chart.js):**

Stacked bar chart showing AR and AP by aging bucket:

```
  Current  |  ████████████  $5,750  (AR)
           |  ████  $2,150  (AP)
  30-60    |  ████████████████  $8,625  (AR)
           |  ████  $2,150  (AP)
  60-90    |  (empty)
  90+      |  ██████  $3,450  (AR)
```

### 6.4 MCP Server Tools

**New MCP tools for AP/AR management:**

| Tool | Description | Parameters |
|------|-------------|------------|
| `ap_list` | List vendor bills (all or filtered by status) | `status?`, `vendor?` |
| `ap_add` | Record a new vendor bill | `vendor`, `amount`, `category`, `due_date` |
| `ap_pay` | Record payment of a vendor bill | `bill_id`, `amount?`, `payment_method` |
| `ar_list` | List customer invoices (already exists, enhance) | `status?`, `client?` |
| `ar_aging` | Generate AR aging report | `as_of_date?` |
| `ap_aging` | Generate AP aging report | `as_of_date?` |
| `apar_summary` | Combined AP/AR position summary | `as_of_date?` |

**MCP tool example:**

```python
@mcp_tool("ap_add")
def ajouter_facture_fournisseur(
    fournisseur: str,
    numero_reference: str,
    montant_ht: Decimal,
    categorie_depense: str,
    date_facture: str,
    date_echeance: str,
    tps_applicable: bool = True,
    tvq_applicable: bool = True,
    notes: str = "",
) -> dict:
    """Record a new vendor bill in accounts payable."""
    # 1. Create FactureFournisseur
    # 2. Add to RegistreFournisseurs
    # 3. Generate Beancount journal entry
    # 4. Return confirmation with bill ID and entry preview
    ...
```

---

## 7. Implementation Roadmap

### Phase A: Foundation -- AP Account and Data Model

**Scope:**
- Add `Passifs:ComptesFournisseurs` (GIFI 2010) to `ledger/comptes.beancount`
- Create `src/compteqc/fournisseurs/` module mirroring `factures/`:
  - `modeles.py` -- `FactureFournisseur`, `BillStatus`, `LigneFactureFournisseur`
  - `journal.py` -- `generer_ecriture_facture_fournisseur()`, `generer_ecriture_paiement_fournisseur()`
  - `registre.py` -- `RegistreFournisseurs` (YAML-based, at `ledger/fournisseurs/registre.yaml`)
- Unit tests for all models and journal entry generation

**Estimated effort:** 1 plan (2-3 tasks)

### Phase B: Aging and CLI Commands

**Scope:**
- Implement aging calculation module (`src/compteqc/vieillissement.py`):
  - `calculer_vieillissement_ar()` -- AR aging from `RegistreFactures`
  - `calculer_vieillissement_ap()` -- AP aging from `RegistreFournisseurs`
  - `rapport_position_apar()` -- combined summary
- Add `montant_paye` and `solde` to existing `Facture` model (AR partial payments)
- CLI commands:
  - `cqc fournisseur add` -- interactively create a vendor bill
  - `cqc fournisseur list [--status STATUS]` -- list bills
  - `cqc fournisseur pay NUMERO [--amount AMOUNT]` -- record payment
  - `cqc aging ar` -- AR aging report
  - `cqc aging ap` -- AP aging report
  - `cqc aging summary` -- combined position

**Estimated effort:** 1 plan (3-4 tasks)

### Phase C: Smart Features -- Recurring Invoices and Auto-Matching

**Scope:**
- Recurring invoice templates:
  - `ModeleFactureRecurrente` model
  - Storage in `ledger/factures/modeles-recurrents.yaml`
  - `cqc facture template add/list/generate` CLI commands
- Auto-matching in import pipeline:
  - AR match: bank deposits against outstanding invoices
  - AP match: bank withdrawals against outstanding bills
  - Confidence scoring and suggestion workflow

**Estimated effort:** 1-2 plans (4-6 tasks)

### Phase D: Dashboard and MCP Integration

**Scope:**
- Fava extension panel for AP/AR summary on the dashboard
- Chart.js aging visualization (stacked bar chart)
- MCP server tools: `ap_list`, `ap_add`, `ap_pay`, `ar_aging`, `ap_aging`, `apar_summary`
- CSV export for CPA package (aging reports as schedules)

**Estimated effort:** 1-2 plans (4-6 tasks)

### Priority and Dependencies

```
Phase A (Foundation)
  |
  +-- Phase B (Aging + CLI)
  |     |
  |     +-- Phase D (Dashboard + MCP)
  |
  +-- Phase C (Recurring + Auto-match)
```

Phase A is the prerequisite. Phases B and C can run in parallel after A.
Phase D depends on B for aging data but can start in parallel with C.

---

## Appendix: GIFI Code Reference

| Account | GIFI | Description |
|---------|------|-------------|
| `Actifs:ComptesClients` | 1060 | Accounts receivable |
| `Actifs:TPS-Payee` | 1300 | GST input tax credits |
| `Actifs:TVQ-Payee` | 1300 | QST input tax refunds |
| `Passifs:ComptesFournisseurs` | 2010 | Accounts payable and accrued liabilities |
| `Passifs:TPS-Percue` | 2620 | GST collected (liability) |
| `Passifs:TVQ-Percue` | 2620 | QST collected (liability) |

## Appendix: File Structure After Implementation

```
ledger/
  comptes.beancount          # Chart of accounts (add ComptesFournisseurs)
  factures/
    registre.yaml            # AR invoice registry (existing)
    modeles-recurrents.yaml  # Recurring invoice templates (new, Phase C)
  fournisseurs/
    registre.yaml            # AP bill registry (new, Phase A)

src/compteqc/
  factures/
    modeles.py               # AR models (enhance with montant_paye)
    journal.py               # AR journal entries (existing)
    registre.py              # AR registry (existing)
  fournisseurs/              # NEW module (Phase A)
    __init__.py
    modeles.py               # AP models (FactureFournisseur, BillStatus)
    journal.py               # AP journal entries
    registre.py              # AP registry (RegistreFournisseurs)
  vieillissement.py          # Aging calculations (new, Phase B)
```
