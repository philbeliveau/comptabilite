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

## 8. UI/UX Design -- Fava Extension

This section defines the frontend layer for the AP/AR system as a Fava extension tab.
It bridges the backend design (Sections 1-7) to a concrete implementation using the
existing CompteQC design system (CSS classes, Jinja2 templates, Chart.js patterns).

### 8.1 Tab Overview: "Comptes a payer / a recevoir"

**Extension class:** `ComptesFournisseursExtension(FavaExtensionBase)`

Registered like other CompteQC tabs, with the `@extension_endpoint` decorator pattern
for form submissions and JSON data endpoints.

```python
class ComptesFournisseursExtension(FavaExtensionBase):
    """Fava extension for AP/AR management."""

    report_title = "Comptes a payer / a recevoir"

    def kpis(self) -> dict:
        """KPI data for the header row."""
        ...

    @extension_endpoint
    def creer_facture(self, request):
        """POST endpoint: create AR invoice."""
        ...

    @extension_endpoint
    def creer_facture_fournisseur(self, request):
        """POST endpoint: create AP bill."""
        ...

    @extension_endpoint
    def aging_data(self, request):
        """JSON endpoint: aging chart data."""
        ...
```

**Full page layout wireframe:**

```
+------------------------------------------------------------------+
|  cqc-page-header                                                 |
|  [h2] Comptes a payer / a recevoir                               |
|  [span.cqc-subtitle] Position au 2026-02-26                     |
+------------------------------------------------------------------+
|  cqc-kpi-row                                                     |
|  +------------+ +------------+ +------------+ +------------+     |
|  | Comptes    | | En retard  | | Comptes    | | Position   |     |
|  | clients    | | (AR)       | | fourniss.  | | nette      |     |
|  | $17,825.00 | | $3,450.00  | | $4,299.50  | | $13,525.50 |     |
|  +------------+ +------------+ +------------+ +------------+     |
+------------------------------------------------------------------+
|  cqc-tab-toggle                                                  |
|  [ Factures clients (AR) ]  [ Factures fournisseurs (AP) ]       |
+------------------------------------------------------------------+
|  Content area (switches between AR and AP)                       |
|                                                                  |
|  +-- Action button: "+ Nouvelle facture" ----------------------+ |
|  +-- Invoice/Bill list table (.cqc-table) --------------------+ |
|  +-- Aging stacked bar chart (Chart.js) ----------------------+ |
+------------------------------------------------------------------+
```

### 8.2 KPI Row

Four KPIs using the `.cqc-kpi-row > .cqc-kpi` pattern (identical to `TableauBordExtension`):

```html
<div class="cqc-kpi-row">
  <div class="cqc-kpi">
    <div class="cqc-kpi-label">Comptes clients (AR)</div>
    <div class="cqc-kpi-value {{ 'cqc-error' if kpis.ar_en_retard > 0 else '' }}"
         data-value="{{ kpis.ar_total }}" data-decimals="2" data-suffix=" $">
      {{ "{:,.2f}".format(kpis.ar_total) }} $
    </div>
  </div>
  <div class="cqc-kpi">
    <div class="cqc-kpi-label">En retard (AR)</div>
    <div class="cqc-kpi-value cqc-error"
         data-value="{{ kpis.ar_en_retard }}" data-decimals="2" data-suffix=" $">
      {{ "{:,.2f}".format(kpis.ar_en_retard) }} $
      <span class="cqc-badge cqc-badge-danger">{{ kpis.ar_en_retard_count }}</span>
    </div>
  </div>
  <div class="cqc-kpi">
    <div class="cqc-kpi-label">Comptes fournisseurs (AP)</div>
    <div class="cqc-kpi-value"
         data-value="{{ kpis.ap_total }}" data-decimals="2" data-suffix=" $">
      {{ "{:,.2f}".format(kpis.ap_total) }} $
    </div>
  </div>
  <div class="cqc-kpi">
    <div class="cqc-kpi-label">Position nette</div>
    <div class="cqc-kpi-value {{ 'cqc-success' if kpis.position_nette > 0 else 'cqc-error' }}"
         data-value="{{ kpis.position_nette }}" data-decimals="2" data-suffix=" $">
      {{ "{:,.2f}".format(kpis.position_nette) }} $
    </div>
  </div>
</div>
```

**Python `kpis()` method:**

```python
def kpis(self) -> dict:
    registre_ar = RegistreFactures()
    registre_ap = RegistreFournisseurs()
    today = date.today()

    ar_impayees = [f for f in registre_ar.lister() if f.solde > 0]
    ap_impayees = registre_ap.lister_impayees()

    ar_total = sum(f.solde for f in ar_impayees)
    ar_en_retard = [f for f in ar_impayees if today > f.date_echeance]
    ap_total = sum(f.solde for f in ap_impayees)

    return {
        "ar_total": ar_total,
        "ar_en_retard": sum(f.solde for f in ar_en_retard),
        "ar_en_retard_count": len(ar_en_retard),
        "ap_total": ap_total,
        "position_nette": ar_total - ap_total,
    }
```

### 8.3 Sub-tab Toggle

Two-button toggle switching between AR and AP list views. Default: AR tab shown.

```html
<style>
  .cqc-tab-toggle {
    display: flex;
    gap: 0;
    margin: 16px 0;
    border: 1px solid var(--cqc-border);
    border-radius: 6px;
    overflow: hidden;
    width: fit-content;
  }
  .cqc-tab-toggle button {
    padding: 8px 20px;
    border: none;
    background: var(--cqc-bg-secondary);
    color: var(--cqc-text);
    cursor: pointer;
    font-size: var(--cqc-font-sm);
    font-weight: var(--cqc-weight-medium);
    transition: background 0.15s, color 0.15s;
  }
  .cqc-tab-toggle button.active {
    background: var(--cqc-blue-600);
    color: #fff;
  }
  .cqc-tab-toggle button:not(.active):hover {
    background: var(--cqc-bg-tertiary);
  }
</style>

<div class="cqc-tab-toggle">
  <button class="active" onclick="showTab('ar')">Factures clients (AR)</button>
  <button onclick="showTab('ap')">Factures fournisseurs (AP)</button>
</div>

<div id="tab-ar"> ... AR content ... </div>
<div id="tab-ap" style="display: none;"> ... AP content ... </div>
```

```javascript
function showTab(tab) {
  var tabs = document.querySelectorAll('.cqc-tab-toggle button');
  tabs.forEach(function(btn) { btn.classList.remove('active'); });
  event.target.classList.add('active');

  document.getElementById('tab-ar').style.display = (tab === 'ar') ? '' : 'none';
  document.getElementById('tab-ap').style.display = (tab === 'ap') ? '' : 'none';
}
```

### 8.4 Invoice/Bill List Table

Both AR and AP lists use `.cqc-table` with status badges and aging color indicators.

**AR Table wireframe:**

```
+-------+----------+----------+-----------+-----------+--------+---------+----------+---------+
| #     | Client   | Date     | Echeance  | Total     | Paye   | Solde   | Statut   | Actions |
+-------+----------+----------+-----------+-----------+--------+---------+----------+---------+
| green | FAC-     | Acme     | 2026-     | 2026-     | 5,750  | 0.00    | 5,750.00 | [ENVOYE]|
| left  | 2026-003 | Corp     | 02-01     | 03-03     | .00    |         |          | [Payer] |
| border|          |          |           |           |        |         |          | [Voir]  |
+-------+----------+----------+-----------+-----------+--------+---------+----------+---------+
| red   | FAC-     | Gamma    | 2025-     | 2025-     | 3,450  | 0.00    | 3,450.00 | [90+]   |
| left  | 2025-011 | Ltd      | 10-28     | 11-27     | .00    |         |          | [Payer] |
| border|          |          |           |           |        |         |          | [Voir]  |
+-------+----------+----------+-----------+-----------+--------+---------+----------+---------+
```

**AR columns:** Numero, Client, Date, Echeance, Total, Paye, Solde, Statut, Actions

**AP columns:** Numero interne, Fournisseur, Ref fournisseur, Date facture, Echeance,
Total, Paye, Solde, Statut, Actions

**Status badges** using `.cqc-badge` variants:

| Status    | CSS Class            | Color  | Used For               |
|-----------|----------------------|--------|------------------------|
| DRAFT     | `cqc-badge-draft`    | Gray   | AR draft invoices      |
| RECEIVED  | `cqc-badge-draft`    | Gray   | AP bills just received |
| SENT      | `cqc-badge-sent`     | Blue   | AR invoices sent       |
| APPROVED  | `cqc-badge-sent`     | Blue   | AP bills approved      |
| PARTIAL   | `cqc-badge-partial`  | Orange | Partial payment        |
| PAID      | `cqc-badge-paid`     | Green  | Fully paid             |
| OVERDUE   | `cqc-badge-overdue`  | Red    | Past due date          |
| DISPUTED  | `cqc-badge-overdue`  | Red    | Under dispute          |

**Aging row color** -- subtle left border indicating age:

```css
.cqc-aging-current  { border-left: 3px solid var(--cqc-green-500); }
.cqc-aging-30-60    { border-left: 3px solid var(--cqc-yellow-500); }
.cqc-aging-60-90    { border-left: 3px solid var(--cqc-orange-500); }
.cqc-aging-90-plus  { border-left: 3px solid var(--cqc-red-500); }
```

**Jinja2 template for AR table:**

```html
<div class="cqc-card-flush">
  <table class="cqc-table">
    <caption class="cqc-sr-only">Factures clients en cours</caption>
    <thead>
      <tr>
        <th>Numero</th><th>Client</th><th>Date</th><th>Echeance</th>
        <th class="montant">Total</th><th class="montant">Paye</th>
        <th class="montant">Solde</th><th>Statut</th><th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for f in factures_ar %}
      {% set age_class = 'cqc-aging-current' if f.jours_retard <= 30
                    else 'cqc-aging-30-60' if f.jours_retard <= 60
                    else 'cqc-aging-60-90' if f.jours_retard <= 90
                    else 'cqc-aging-90-plus' %}
      <tr class="{{ age_class }}">
        <td>{{ f.numero }}</td>
        <td>{{ f.nom_client }}</td>
        <td>{{ f.date }}</td>
        <td>{{ f.date_echeance }}</td>
        <td class="montant">{{ "{:,.2f}".format(f.total) }} $</td>
        <td class="montant">{{ "{:,.2f}".format(f.montant_paye) }} $</td>
        <td class="montant">{{ "{:,.2f}".format(f.solde) }} $</td>
        <td>
          {% if f.statut == 'draft' %}
            <span class="cqc-badge cqc-badge-draft">Brouillon</span>
          {% elif f.statut == 'sent' %}
            <span class="cqc-badge cqc-badge-sent">Envoye</span>
          {% elif f.statut == 'partial' %}
            <span class="cqc-badge cqc-badge-partial">Partiel</span>
          {% elif f.statut == 'paid' %}
            <span class="cqc-badge cqc-badge-paid">Paye</span>
          {% elif f.statut == 'overdue' %}
            <span class="cqc-badge cqc-badge-overdue">En retard</span>
          {% endif %}
        </td>
        <td class="cqc-cell-flex">
          <form method="POST" action="{{ pay_url }}" style="margin:0;">
            <input type="hidden" name="numero" value="{{ f.numero }}">
            <button type="submit" class="cqc-btn cqc-btn-sm">Payer</button>
          </form>
          <a href="{{ url_for('report', report_name='context', entry_hash=f.entry_hash) }}"
             class="cqc-btn cqc-btn-sm cqc-btn-outline">Voir</a>
        </td>
      </tr>
      {% endfor %}
      {% if not factures_ar %}
      <tr><td colspan="9" class="cqc-empty-state">Aucune facture client en cours.</td></tr>
      {% endif %}
    </tbody>
  </table>
</div>
```

### 8.5 Aging Stacked Bar Chart

Chart.js horizontal stacked bar chart showing AR and AP by aging bucket.

**Chart container (same pattern as `TableauBordExtension`):**

```html
<div class="cqc-card">
  <h3>Vieillissement AR / AP</h3>
  <div class="cqc-chart-container"
       id="chart-aging-apar"
       data-chart='{{ extension.aging_chart_json() }}'
       data-chart-type="bar">
    <canvas role="img" aria-label="Graphique de vieillissement des comptes"></canvas>
  </div>
</div>
```

**Chart.js configuration:**

```python
def aging_chart_json(self) -> str:
    """JSON for Chart.js horizontal stacked bar chart."""
    # Compute aging buckets for AR and AP
    ar_aging = calculer_vieillissement_ar(self.registre_ar)
    ap_aging = calculer_vieillissement_ap(self.registre_ap)

    config = {
        "type": "bar",
        "data": {
            "labels": ["Comptes clients (AR)", "Comptes fournisseurs (AP)"],
            "datasets": [
                {
                    "label": "Courant (0-30j)",
                    "data": [float(ar_aging["current"]), float(ap_aging["current"])],
                    "backgroundColor": "var(--cqc-blue-200)",
                },
                {
                    "label": "31-60 jours",
                    "data": [float(ar_aging["30-60"]), float(ap_aging["30-60"])],
                    "backgroundColor": "var(--cqc-blue-400)",
                },
                {
                    "label": "61-90 jours",
                    "data": [float(ar_aging["60-90"]), float(ap_aging["60-90"])],
                    "backgroundColor": "var(--cqc-blue-600)",
                },
                {
                    "label": "91+ jours",
                    "data": [float(ar_aging["90+"]), float(ap_aging["90+"])],
                    "backgroundColor": "var(--cqc-blue-800)",
                },
            ],
        },
        "options": {
            "indexAxis": "y",
            "responsive": True,
            "plugins": {
                "legend": {"position": "bottom"},
                "tooltip": {
                    "callbacks": {
                        "label": "function(ctx) { return ctx.dataset.label + ': ' + ctx.parsed.x.toLocaleString('fr-CA', {style:'currency',currency:'CAD'}) }"
                    }
                }
            },
            "scales": {
                "x": {
                    "stacked": True,
                    "ticks": {"callback": "function(v) { return v.toLocaleString('fr-CA') + ' $' }"}
                },
                "y": {"stacked": True}
            }
        }
    }
    return json.dumps(config)
```

**Visual representation:**

```
Comptes clients (AR)  |  ████ Courant  ████████ 31-60j        ████ 91+
Comptes fourn. (AP)   |  ████ Courant  ████ 31-60j
                      +--------------------------------------------------
                      0     $5,000   $10,000   $15,000   $20,000
                         Courant  31-60j  61-90j  91+
```

The chart uses the same registry `Map` with `destroy-on-navigate` lifecycle pattern
for SPA safety, as documented in the `ThemeQCExtension.js` chart initialization code.

### 8.6 "+Nouvelle facture" Form (AR Creation)

Button at the top of the AR sub-tab opens an inline form within a `.cqc-card`.

**Wireframe:**

```
+------------------------------------------------------------------+
|  [+ Nouvelle facture]  (cqc-btn cqc-btn-primary)                 |
+------------------------------------------------------------------+
|  cqc-card (hidden by default, slides open on click)              |
|                                                                  |
|  Client: [____________________] (autocomplete from registry)     |
|  Date:   [2026-02-26]  Echeance: [2026-03-28] (auto Net 30)     |
|                                                                  |
|  Lignes:                                                         |
|  +----+---------------------------+-----+----------+-----+-----+|
|  | #  | Description               | Qte | Prix/u   | TPS | TVQ ||
|  +----+---------------------------+-----+----------+-----+-----+|
|  | 1  | [Consultation fevrier    ] | [1] | [5000.00]| [x] | [x]||
|  | 2  | [Frais de deplacement   ] | [1] | [ 250.00]| [x] | [x]||
|  +----+---------------------------+-----+----------+-----+-----+|
|  [+ Ajouter une ligne]                                           |
|                                                                  |
|  Notes: [_______________________________________________]        |
|                                                                  |
|  +-------------------+                                           |
|  | Sous-total: 5,250.00 $                                        |
|  | TPS (5%):     262.50 $                                        |
|  | TVQ (9.975%): 523.69 $                                        |
|  | Total:      6,036.19 $                                        |
|  +-------------------+                                           |
|                                                                  |
|  [Creer la facture] (cqc-btn cqc-btn-success)                   |
+------------------------------------------------------------------+
```

**Key behaviors:**

- Client field uses autocomplete populated from `RegistreFactures` existing client names.
- Date defaults to today; Echeance auto-fills to Date + 30 days (Net 30).
- Dynamic line rows: "Ajouter une ligne" button appends a new row via JavaScript.
- TPS and TVQ checkboxes default to checked; uncheck for tax-exempt lines.
- Totals calculated live in JavaScript as user types (no server round-trip).
- Submit: `POST` to `@extension_endpoint` `creer_facture`, which creates the `Facture`
  object, adds to `RegistreFactures`, generates the Beancount journal entry, and redirects
  back to the AR tab.

**Form field mapping to `Facture` model:**

| Form Field   | Model Field        | Notes                          |
|-------------|--------------------|--------------------------------|
| Client      | `nom_client`       | Text with autocomplete         |
| Date        | `date`             | Date picker, default today     |
| Echeance    | `date_echeance`    | Date picker, default +30 days  |
| Description | `LigneFacture.description` | Per line               |
| Qte         | `LigneFacture.quantite`    | Integer, default 1     |
| Prix/u      | `LigneFacture.prix_unitaire` | Decimal              |
| TPS         | `LigneFacture.tps_applicable` | Checkbox, default on |
| TVQ         | `LigneFacture.tvq_applicable` | Checkbox, default on |
| Notes       | `notes`            | Free text                      |

This brings `cqc facture creer` CLI functionality to the web interface.

### 8.7 "+Nouvelle facture fournisseur" Form (AP Creation)

Button at the top of the AP sub-tab opens an inline `.cqc-card` form.

**Wireframe:**

```
+------------------------------------------------------------------+
|  [+ Nouvelle facture fournisseur]  (cqc-btn cqc-btn-primary)    |
+------------------------------------------------------------------+
|  cqc-card (hidden by default, slides open on click)              |
|                                                                  |
|  Fournisseur: [__________________] (autocomplete from registry)  |
|  Ref fournisseur: [INV-2026-0042]                                |
|  Date facture: [2026-02-15]  Echeance: [2026-03-17]             |
|                                                                  |
|  Lignes:                                                         |
|  +----+------------------+----------+-----------+-----+-----+---+|
|  | #  | Description      | Montant  | Categorie | TPS | TVQ |ITC||
|  +----+------------------+----------+-----------+-----+-----+---+|
|  | 1  | [Honoraires     ]| [1000.00]| [Depenses | [x] | [x] |1.0|
|  |    |  comptabilite   ]|          |  :Honorai |     |     |   ||
|  |    |                  |          |  res-Pro  |     |     |   ||
|  |    |                  |          |  :Compt.] |     |     |   ||
|  +----+------------------+----------+-----------+-----+-----+---+|
|  | 2  | [Repas client   ]| [  50.00]| [Depenses | [x] | [x] |0.5|
|  |    |                  |          |  :Repas-R |     |     |   ||
|  |    |                  |          |  epresen.]|     |     |   ||
|  +----+------------------+----------+-----------+-----+-----+---+|
|  [+ Ajouter une ligne]                                           |
|                                                                  |
|  Notes: [_______________________________________________]        |
|                                                                  |
|  +-------------------+                                           |
|  | Sous-total: 1,050.00 $                                        |
|  | TPS (5%):      52.50 $                                        |
|  | TVQ (9.975%): 104.74 $                                        |
|  | Total:      1,207.24 $                                        |
|  +-------------------+                                           |
|  | ITC reclamable:  51.25 $ (TPS a 100% + 50%)                  |
|  | ITR reclamable: 102.25 $ (TVQ a 100% + 50%)                  |
|  +-------------------+                                           |
|                                                                  |
|  [Creer la facture] (cqc-btn cqc-btn-success)                   |
+------------------------------------------------------------------+
```

**Key differences from AR form:**

- `Fournisseur` autocompletes from `RegistreFournisseurs` existing vendor names.
- `Ref fournisseur` is free text (the vendor's own invoice number).
- `Categorie` dropdown is populated from chart of accounts expense categories
  (accounts under `Depenses:*` in `ledger/comptes.beancount`).
- `taux_itc` column (default 1.0, set to 0.5 for meals) controls partial ITC eligibility.
- `taux_itr` column (default 1.0) controls partial ITR eligibility.
- ITC/ITR summary shown below totals so user sees the tax credit impact.

**Form field mapping to `FactureFournisseur` model:**

| Form Field       | Model Field                       | Notes                    |
|-----------------|-----------------------------------|--------------------------|
| Fournisseur     | `fournisseur`                     | Autocomplete             |
| Ref fournisseur | `numero_reference`                | Vendor's invoice number  |
| Date facture    | `date_facture`                    | Date picker              |
| Echeance        | `date_echeance`                   | Date picker, default +30 |
| Description     | `LigneFactureFournisseur.description` | Per line             |
| Montant         | `LigneFactureFournisseur.montant`     | Pre-tax amount       |
| Categorie       | `LigneFactureFournisseur.categorie_depense` | Dropdown       |
| TPS             | `LigneFactureFournisseur.tps_applicable`    | Checkbox         |
| TVQ             | `LigneFactureFournisseur.tvq_applicable`    | Checkbox         |
| ITC             | `LigneFactureFournisseur.taux_itc`          | 1.0 or 0.5       |
| Notes           | `notes`                           | Free text                |

### 8.8 Receipt-to-AP Pipeline UX

The primary AP entry path for a solo consultant is **receipt-driven**, not manual form
entry. This flow connects the existing `RecusExtension` upload to AP bill creation.

**Flow:**

```
1. User uploads receipt       2. AI extracts data       3. NEW: "Creer AP?" prompt
   in Recus tab                  (existing flow)            appears after extraction
   [Drag & drop PDF]          -> vendor, date,           -> Button navigates to AP tab
                                 amount, tax                 with form pre-filled
                                 breakdown

4. AP form pre-filled         5. User confirms
   from extraction data       -> FactureFournisseur created
   [Adjust category,          -> Beancount entry generated
    verify amounts]           -> Redirect to AP list
```

**Wireframe -- Receipt extraction result with AP creation prompt:**

```
+------------------------------------------------------------------+
|  cqc-card  (after receipt upload + AI extraction)                 |
|                                                                  |
|  Recu telecharge et analyse                                      |
|  Fichier:      2026-02-24.cabinet-comptable.pdf                  |
|  Fournisseur:  Cabinet Comptable XYZ                             |
|  Date:         2026-02-15                                        |
|  Total:        1,149.75 $                                        |
|  TPS:             50.00 $                                        |
|  TVQ:             99.75 $                                        |
|  Confiance:    92%                                               |
|                                                                  |
|  +-- Correspondances proposees (existing) ---+                   |
|  |  ... match table with Lier buttons ...    |                   |
|  +-------------------------------------------+                   |
|                                                                  |
|  +-- NEW SECTION -----------------------------------------+      |
|  |  Creer une entree AP a partir de ce recu?              |      |
|  |  [Creer facture fournisseur] (cqc-btn cqc-btn-primary) |      |
|  +--------------------------------------------------------+      |
+------------------------------------------------------------------+
```

**Implementation notes:**

- The "Creer facture fournisseur" button navigates to the AP/AR tab with query
  parameters pre-filling the form: `?prefill=1&fournisseur=Cabinet+Comptable+XYZ
  &date=2026-02-15&montant=1000.00&tps=50.00&tvq=99.75`
- The AP form JavaScript reads URL query parameters on page load and fills fields.
- This is the most common AP workflow: upload receipt, extract, create AP, done.
  Manual form entry is the fallback for bills without a scannable document.

### 8.9 Auto-matching UX in Approval Queue

Enhancement to the existing `ApprobationExtension` to show AP/AR match suggestions
alongside the AI categorization confidence.

**When a bank deposit matches an AR invoice** (per Section 6.1 matching logic):

```
+------------------------------------------------------------------+
|  Approval queue row (existing)                                   |
+------+----------+------------------+----------+------------------+
| [x]  | 2026-03-05| Virement Acme   | 5,750.00 | Revenus:Consult.|
+------+----------+------------------+----------+------------------+
|      | >> Correspond a FAC-2026-003 - Acme Corp (5,750.00 $)     |
|      |    Confiance: 97%                                         |
|      |    [Lier comme paiement AR] (cqc-btn cqc-btn-sm)          |
+------+----+------------------------------------------------------+
```

**When a bank withdrawal matches an AP bill:**

```
+------------------------------------------------------------------+
|  Approval queue row (existing)                                   |
+------+----------+------------------+----------+------------------+
| [x]  | 2026-03-01| Paiement Cabinet| 1,149.75 | Depenses:Honor. |
+------+----------+------------------+----------+------------------+
|      | >> Correspond a FOUR-2026-001 - Cabinet Comptable          |
|      |    (1,149.75 $) - Confiance: 95%                          |
|      |    [Lier comme paiement AP] (cqc-btn cqc-btn-sm)          |
+------+----+------------------------------------------------------+
```

**Jinja2 template addition for match row (inside the existing approval table):**

```html
{% if txn.match_apar %}
<tr class="cqc-match-suggestion">
  <td></td>
  <td colspan="6">
    <div class="cqc-match-info">
      <span class="cqc-match-arrow">&raquo;</span>
      Correspond a <strong>{{ txn.match_apar.numero }}</strong>
      &mdash; {{ txn.match_apar.nom }}
      ({{ "{:,.2f}".format(txn.match_apar.montant) }} $)
      <span class="cqc-text-muted">Confiance: {{ txn.match_apar.confiance }}%</span>
      <form method="POST"
            action="/{{ g.beancount_file_slug }}/extension/{{ extension.name }}/lier_apar"
            style="display: inline; margin-left: 12px;">
        <input type="hidden" name="txn_index" value="{{ loop.index0 }}">
        <input type="hidden" name="numero" value="{{ txn.match_apar.numero }}">
        <input type="hidden" name="type" value="{{ txn.match_apar.type }}">
        <button type="submit" class="cqc-btn cqc-btn-sm">
          Lier comme paiement {{ txn.match_apar.type|upper }}
        </button>
      </form>
    </div>
  </td>
</tr>
{% endif %}
```

**CSS for match suggestion row:**

```css
.cqc-match-suggestion td {
  border-top: none !important;
  padding-top: 0;
  padding-bottom: 12px;
}
.cqc-match-info {
  background: var(--cqc-blue-50);
  border-left: 3px solid var(--cqc-blue-400);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
  font-size: var(--cqc-font-sm);
}
.cqc-match-arrow {
  color: var(--cqc-blue-600);
  font-weight: var(--cqc-weight-bold);
  margin-right: 4px;
}
```

**Lier button behavior:** Same POST redirect pattern as the existing "Lier" button in
`RecusExtension` -- intentional page navigation for clear confirmation. The endpoint
records the payment (clears AR or AP balance), generates the Beancount payment entry,
and redirects back to the approval queue.

### 8.10 Dashboard Homepage Integration

New KPI on the `TableauBordExtension` for the AP/AR net position.

**Addition to existing KPI row in `TableauBordExtension.html`:**

```html
<!-- After existing "En attente" KPI -->
<div class="cqc-kpi">
  <div class="cqc-kpi-label">Position AR/AP</div>
  <div class="cqc-kpi-value {{ 'cqc-success' if kpis.position_apar >= 0 else 'cqc-error' }}"
       data-value="{{ kpis.position_apar }}" data-decimals="2" data-suffix=" $">
    {{ "{:,.2f}".format(kpis.position_apar) }} $
  </div>
  <a href="/{{ g.beancount_file_slug }}/extension/ComptesFournisseursExtension/"
     class="cqc-text-muted" style="font-size: var(--cqc-font-xs);">
    Voir detail
  </a>
</div>
```

**Python method addition to `TableauBordExtension`:**

```python
def _position_apar(self) -> Decimal:
    """Net AR/AP position for dashboard KPI."""
    from compteqc.factures.registre import RegistreFactures
    from compteqc.fournisseurs.registre import RegistreFournisseurs

    registre_ar = RegistreFactures()
    registre_ap = RegistreFournisseurs()

    ar_total = sum(
        f.solde for f in registre_ar.lister() if f.solde > 0
    )
    ap_total = sum(
        f.solde for f in registre_ap.lister_impayees()
    )
    return ar_total - ap_total
```

The KPI turns green when AR exceeds AP (net positive cash position) and red when
AP exceeds AR (more owed than owed to the corporation). Clicking the value navigates
to the full AP/AR tab for detail.

### 8.11 Solo Consultant Workflow Summary

The realistic day-to-day workflow for a solo IT consultant with ~$230K revenue:

**Accounts Payable (most common path: receipt-driven)**

```
Weekly: Upload receipts
  |
  v
Recus tab -> Drag & drop PDF/image -> AI extracts vendor, date, amount, taxes
  |
  v
"Creer AP?" prompt -> Click -> AP form pre-filled -> Adjust category if needed -> Confirm
  |
  v
FactureFournisseur created + Beancount entry written
  |
  v
Later: Bank statement imported -> Approval queue matches payment to AP -> "Lier" -> Done
```

**Key insight:** Most AP entries come from receipt upload, not manual form entry.
The manual form (Section 8.7) is a fallback for bills without a scannable document
(e.g., verbal agreements, email-only invoices).

**Accounts Receivable (most common path: recurring template)**

```
Monthly: Recurring template auto-generates invoice
  |
  v
Review generated invoice -> Send to client
  |
  v
Later: Bank deposit arrives -> Approval queue matches deposit to AR -> "Lier" -> Done
```

**Key insight:** Most AR entries come from recurring templates (Phase C in roadmap).
The manual invoice form (Section 8.6) is for one-off projects or ad-hoc billing.

**Typical vendor volume for a solo consultant:**

| Vendor Type                  | Frequency  | AP Method          |
|------------------------------|------------|--------------------|
| CPA (accountant)             | Quarterly  | Receipt upload     |
| Software subscriptions       | Monthly    | Bank import match  |
| Cloud hosting (AWS, etc.)    | Monthly    | Bank import match  |
| Office supplies              | Occasional | Receipt upload     |
| Professional development     | Occasional | Receipt upload     |
| Meals & entertainment (50%)  | Occasional | Receipt upload     |

**Weekly review workflow:**

1. Glance at KPI row: any overdue amounts? Any negative net position?
2. Review approval queue: confirm auto-matches (AR deposits, AP payments).
3. Upload any new receipts: let AI extract and create AP entries.
4. Monthly: verify recurring invoice was generated and sent.

The system is designed so that most interactions take **under 5 minutes per week**
during normal operations, with the AI handling extraction, matching, and categorization.

### 8.12 Updated Implementation Roadmap

The existing Phases A-D (Section 7) cover backend logic. Adding Phases D' and E for
the UI layer and cross-tab integration.

**Phase D (updated): Dashboard, MCP Integration, and Fava Extension Tab**

Original Phase D scope, plus:
- Create `ComptesFournisseursExtension(FavaExtensionBase)` with Jinja2 template
- KPI row (Section 8.2): query both registries, compute net position
- Sub-tab toggle (Section 8.3): JavaScript AR/AP switching
- AR and AP list tables (Section 8.4): status badges, aging row colors
- Chart.js aging visualization (Section 8.5): horizontal stacked bar chart
- Form endpoints for AR creation (Section 8.6) and AP creation (Section 8.7)
- Dashboard KPI integration (Section 8.10): `position_apar` on `TableauBordExtension`

**Phase E (new): Receipt-to-AP Pipeline and Auto-matching UX**

- Receipt extraction to AP creation prompt (Section 8.8):
  - Add "Creer facture fournisseur" button to `RecusExtension` extraction result
  - Query parameter pre-fill on AP form
- Approval queue matching suggestions (Section 8.9):
  - Enhance `ApprobationExtension` to call `suggerer_rapprochement_ar/ap`
  - Display match suggestion rows with "Lier" buttons
  - `lier_apar` endpoint: record payment, clear AR/AP, generate Beancount entry
- End-to-end integration testing

**Updated dependency diagram:**

```
Phase A (Foundation: AP account, data model, registry)
  |
  +-- Phase B (Aging calculation + CLI commands)
  |     |
  |     +-- Phase D (Dashboard + MCP + Fava extension tab)
  |           |
  |           +-- Phase E (Receipt-to-AP pipeline + auto-matching UX)
  |
  +-- Phase C (Recurring invoices + auto-matching logic)
        |
        +-- Phase E (uses auto-matching logic from Phase C)
```

Phase E depends on both D (Fava extension exists) and C (matching logic exists).
This reflects that the UI integration layer requires both the presentation foundation
and the matching algorithms.

**Estimated effort for new phases:**

| Phase | Scope                              | Estimated Plans | Estimated Tasks |
|-------|------------------------------------|-----------------|-----------------|
| D     | Fava tab + forms + chart + MCP     | 2-3 plans       | 8-12 tasks      |
| E     | Receipt-to-AP + approval matching  | 1-2 plans       | 4-6 tasks       |

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
