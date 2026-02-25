# Phase 2: Quebec Domain Logic - Research

**Researched:** 2026-02-19
**Domain:** Quebec/federal payroll formulas, GST/QST tracking, CCA depreciation, shareholder loan monitoring
**Confidence:** HIGH (payroll formulas, GST/QST math), MEDIUM (Quebec income tax withholding detail, CCA plugin compatibility)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Payroll workflow**: On-demand CLI trigger (e.g. `compteqc payroll run 5000`) -- no schedule, user initiates each run. Consistent salary amount expected (same gross each time, occasional adjustments). Full breakdown output by default: gross, every deduction line (QPP, RQAP, EI, federal tax, Quebec tax), every employer contribution (FSS, CNESST, etc.), net pay. YTD totals must stop contributions at annual maximums (QPP, EI, RQAP).
- **GST/QST tax treatment on expenses**: Auto-calculate GST (5%) and QST (9.975%) from transaction total by default. Tax treatment rules: category default (taxable/exempt/zero-rated) + vendor-level override. Vendor override wins when it exists; new vendors default to "taxable" until confirmed. GST and QST always tracked separately (never combined 14.975% rate).
- **GST/QST filing periods**: Filing frequency is configurable (annual or quarterly) -- system asks or reads from config. Summaries generated per filing period: GST collected, QST collected, ITCs, ITRs, net remittance. Monthly drill-down available within each period.
- **GST/QST on revenue**: Per-client tax treatment rules (not "always charge both"). Quebec clients: GST + QST. Out-of-province Canadian clients: GST only. International clients: no GST/QST. Per-product-type rules also supported (for Enact vs consulting).
- **CCA & asset registration**: Auto-flag transactions over configurable threshold (default $500) as potential CAPEX. System proposes CCA class, user confirms or overrides. Manual CLI registration also available for assets not in bank feed.
- **CCA pool tracking**: Pool-level UCC tracking per CCA class (mirrors CRA approach). Individual assets listed for reference but CCA calculated at pool level.
- **Asset disposal**: Both paths: CLI command for explicit disposal + auto-detect from sale transactions in bank feed. System calculates recapture or terminal loss and posts entries.
- **Shareholder loan triggers**: Auto-detect potential personal transactions and flag for confirmation. User confirms: "business", "personal/loan", or "ignore". Explicitly categorized personal expenses always hit shareholder loan automatically. System never silently posts ambiguous items to shareholder loan.
- **Shareholder loan alerts (s.15(2))**: Graduated escalation: alert at 9 months, 11 months, and 30 days before inclusion date. No spammy monthly alerts.
- **Shareholder loan repayment**: Both methods supported: personal deposits to corp account + salary offset. Clear audit trail on every repayment regardless of method.
- **Shareholder loan direction**: Bidirectional tracking on a single net balance. Positive = shareholder owes corp, negative = corp owes shareholder. Full detail of each movement preserved.

### Claude's Discretion
- Payroll corrections: choose correction approach cleanest for CPA review (reversal + new entry vs adjustment delta)
- CCA depreciation: choose safest approach for CPA review (auto-generate with review vs auto-post)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Summary

Phase 2 implements four Quebec-specific domain modules on top of the Phase 1 Beancount ledger: a payroll engine, GST/QST tax tracking, CCA (capital cost allowance) depreciation, and shareholder loan monitoring. Each module is a pure Python calculation engine that produces Beancount transactions.

The payroll engine is the most complex module. It must implement two independent withholding formula systems: the federal T4127 formulas (with 16.5% Quebec abatement) and the Quebec TP-1015.F-V formulas, plus five contribution calculations (QPP base+additional, RQAP, EI, FSS, CNESST, labour standards). All rates and thresholds for 2026 are verified from official sources (Retraite Quebec, Revenu Quebec, CRA). The critical design pattern is: all rates/thresholds live in a single `rates.py` config module indexed by year, all calculations use `Decimal` math, and YTD tracking prevents over-contribution at annual maximums.

GST/QST tracking is mathematically simpler but architecturally pervasive: every expense transaction needs tax extraction and every revenue transaction needs tax application, with per-category and per-vendor/client treatment rules. CCA is a straightforward declining-balance calculation with half-year rule and pool-level tracking. The shareholder loan module is primarily a monitoring/alerting system with deadline calculations based on the corporation's fiscal year-end.

**Primary recommendation:** Build each domain as an independent Python module under `src/compteqc/quebec/` with pure functions that take inputs and return Beancount transactions. No Beancount plugins -- instead, use the existing CLI to orchestrate. Keep `rates.py` as the single source of truth for all rates/thresholds. Implement payroll first (highest complexity, highest value), then GST/QST (pervasive impact), then CCA (year-end only), then shareholder loan (monitoring layer).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PAY-01 | User can run payroll for a given gross salary amount and pay period | CLI command `cqc paie lancer <montant>` triggers payroll engine. Engine takes gross amount, pay period number, returns complete breakdown. Verified T4127 + TP-1015.F-V formula structures. |
| PAY-02 | System calculates QPP base (5.3%), QPP additional 1 (1.0%), QPP additional 2 (4.0%) with correct maximums and exemptions | QPP rates verified via Retraite Quebec: base 5.3% on $3,500-$74,600 (max $3,768.30), additional 1 1.0% same range (max $711.00), additional 2 4.0% on $74,600-$85,000 (max $416.00). All per employee+employer. |
| PAY-03 | System calculates RQAP employer (0.602%) and employee (0.430%) contributions | RQAP rates verified: employer 0.602%, employee 0.430%, MIE $103,000. Max employer $620.06, max employee $442.90. |
| PAY-04 | System calculates EI at Quebec rate (employer 1.82%, employee 1.30%) with MIE cap | EI Quebec rates verified via CRA: employee 1.30%, employer 1.82% (1.4x), MIE $68,900. Max employee $895.70, max employer $1,253.98. |
| PAY-05 | System calculates FSS (1.65% for payroll under $1M, service sector) | FSS rate verified via Revenu Quebec: 1.65% for service sector with total payroll <= $1M. Employer-only contribution on total payroll. |
| PAY-06 | System calculates CNESST based on assigned classification rate | CNESST rate is employer-specific (assigned by CNESST). System uses configurable rate in rates.py. MIE $103,000. |
| PAY-07 | System calculates labour standards contribution (0.06%) | Rate verified: 0.06% on earnings up to $103,000. Max $61.80. Employer-only. |
| PAY-08 | System calculates federal income tax withholding with Quebec 16.5% abatement | T4127 formula verified: T3 = (R x A) - K - K1 - K2Q - K3 - K4; T1 = T3 - (0.165 x T3). 2026 brackets: 14%/20.5%/26%/29%/33%. BPAF $16,452. |
| PAY-09 | System calculates Quebec provincial income tax withholding using TP-1015.F-V formulas | TP-1015.F-V 2026 formulas: annualize gross, apply QC brackets (14%/19%/24%/25.75%), subtract personal credits ($18,952 basic), de-annualize. PDF available but not machine-parseable; formulas reconstructable from research doc variables. |
| PAY-10 | System tracks year-to-date totals and stops contributions at annual maximums | YTD tracking required for QPP (base max $3,768.30, add1 $711.00, add2 $416.00), RQAP ($620.06/$442.90), EI ($1,253.98/$895.70). Store YTD in a persistent state file or derive from existing ledger entries. |
| PAY-11 | Payroll generates complete journal entries (salary expense, deductions, employer contributions, net pay) | Beancount transaction creation verified via `data.Transaction.__new__` and `data.create_simple_posting`. Multi-posting transaction with ~15 legs covering gross, each deduction, each employer contribution, net pay. |
| PAY-12 | All payroll rates are config-driven in rates.py, updatable annually | Pure Python dict/dataclass indexed by year. All rate constants in one file. Pattern verified as standard approach. |
| TAX-01 | System tracks GST collected (5%) and QST collected (9.975%) on revenue separately | Existing accounts: `Passifs:TPS-Percue` and `Passifs:TVQ-Percue`. Revenue transactions add postings to these liability accounts. |
| TAX-02 | System tracks GST paid and QST paid on business expenses for ITC/ITR claims | Existing accounts: `Actifs:TPS-Payee` and `Actifs:TVQ-Payee`. Expense transactions add postings to these asset accounts. |
| TAX-03 | GST and QST are calculated separately per line item, each rounded independently (never combined rate) | Reverse calculation from tax-included total: pre_tax = total / 1.14975; GST = round(pre_tax * 0.05, 2); QST = round(pre_tax * 0.09975, 2). Each rounded independently to $0.01. |
| TAX-04 | System generates net GST/QST remittance summary by filing period | beanquery can sum `Passifs:TPS-Percue` and `Actifs:TPS-Payee` by date range. Net = collected - ITCs. Configurable filing periods (annual/quarterly). |
| TAX-05 | System handles GST/QST-exempt items (financial services, etc.) | Tax treatment config (YAML): per-category default + per-vendor override. Categories: taxable (default), exempt (e.g. financial services, insurance), zero-rated (e.g. basic groceries, exports). |
| TAX-06 | Automated reconciliation check ensures GST and QST returns derive from identical transaction sets | Validation query: every transaction with a TPS posting must have a matching TVQ posting (and vice versa), except for exempt/zero-rated items. Flag mismatches. |
| CCA-01 | System tracks capital assets by CCA class (8, 10, 12, 50, 54) | CCA classes and rates verified via CRA: Class 8 (20%), Class 10 (30%), Class 12 (100%), Class 50 (55%), Class 54 (30%). Pool-level UCC tracking per class. |
| CCA-02 | Half-year rule automatically applied for new acquisitions | First year: CCA calculated on 50% of net addition to class. Formula: CCA_base = UCC_opening + (net_addition x 0.5); CCA = CCA_base x rate. |
| CCA-03 | Declining balance depreciation calculated per class with correct rates | Standard declining balance: CCA = UCC x rate. UCC_next = UCC - CCA. Applied at pool level, not individual asset level. |
| CCA-04 | UCC (undepreciated capital cost) schedule maintained per class | Data model: per-class record with opening UCC, additions, disposals (proceeds or cost, whichever is less), net additions, half-year adjustment, CCA claimed, closing UCC. |
| CCA-05 | System handles disposals and recapture/terminal loss calculations | Disposal reduces UCC by lesser of proceeds and original cost. If UCC goes negative: recapture (add to income). If class is empty and UCC > 0: terminal loss (deductible expense). |
| CCA-06 | CCA entries generated as Beancount transactions for year-end | Generate one transaction per CCA class: Dr Depenses:Amortissement, Cr Actifs:Immobilisations:Amortissement-Cumule. Use `data.Transaction.__new__` with metadata linking to CCA schedule. |
| LOAN-01 | Dedicated shareholder loan account (1800) tracks all personal-vs-business transactions | Existing account: `Passifs:Pret-Actionnaire` (GIFI 2480). Bidirectional: positive = shareholder owes corp, negative = corp owes shareholder. |
| LOAN-02 | System computes repayment deadline (fiscal year-end + 1 year) per s.15(2) | Deadline = fiscal_year_end + 1 year. For Dec 31 FYE: loan made in 2026 must be repaid by Dec 31, 2027. Each loan advance tracked with its own deadline. |
| LOAN-03 | Alerts at 9 months, 11 months, and 30 days before inclusion date | Three alert thresholds per loan: (deadline - 9 months), (deadline - 11 months), (deadline - 30 days). CLI command `cqc pret-actionnaire statut` shows current balance and upcoming deadlines. |
| LOAN-04 | System flags circular loan-repayment-reborrow patterns | Detection: if a repayment is followed by a new advance of similar amount within a short window (configurable, e.g. 30 days), flag as potential s.15(2.6) issue. |
| CLI-04 | User can run payroll via CLI command | `cqc paie lancer <montant_brut>` with options for pay period override, dry-run mode, and salary offset against shareholder loan. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| beancount | 3.2.0 | Ledger engine (from Phase 1) | Already in use. `data.Transaction.__new__` and `data.create_simple_posting` for creating transactions programmatically. [HIGH -- verified Phase 1 + Context7] |
| pydantic | 2.x | Rate config validation, payroll models | Validates rates.py config, payroll input/output models. Already a dependency. [HIGH] |
| typer | 0.24.0 | CLI commands (from Phase 1) | Extends Phase 1 CLI with `paie`, `tps-tvq`, `dpa`, `pret-actionnaire` subcommands. [HIGH] |
| rich | latest | Terminal output formatting | Payroll breakdown tables, CCA schedules, alert formatting. Already a dependency. [HIGH] |
| pyyaml | latest | Tax treatment rules config | GST/QST category/vendor rules in YAML. Already a dependency. [HIGH] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Testing with extensive fixtures | Payroll calculations need comprehensive test coverage against known-good values. [HIGH] |
| freezegun | latest | Date mocking for alert tests | Shareholder loan deadline alerts need deterministic date testing. [HIGH] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom payroll engine | beancount-plugins depreciation plugin | The davidastephens plugin has a CRA method with half-year rule, but it's designed for Beancount v2 (compatibility unverified with v3), only handles depreciation (not payroll/GST), and configuration via plugin strings is fragile. Building custom gives full control. |
| Custom CCA module | beancount-plugins flexible_depreciation | Plugin supports CRA method with 50% first-year rule and declining balance. However: unknown v3 compatibility, limited to metadata-driven approach, no pool-level tracking (individual asset only), no disposal/recapture handling. Build custom for CRA-compliant pool-level CCA. |
| YAML tax rules | Database-backed rules | YAML is sufficient for ~20-50 vendor overrides and ~10 category defaults. Database adds complexity without value at this scale. Revisit if vendor list exceeds 200+. |

**No new dependencies needed.** Phase 2 uses only libraries already installed in Phase 1, plus `freezegun` for testing.

```bash
uv add --dev freezegun
```

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)
```
src/compteqc/
├── quebec/                          # NEW: Quebec domain logic
│   ├── __init__.py
│   ├── rates.py                     # All rates/thresholds by year
│   ├── paie/                        # Payroll engine
│   │   ├── __init__.py
│   │   ├── moteur.py                # Core payroll calculation engine
│   │   ├── cotisations.py           # QPP, RQAP, EI, FSS, CNESST, labour standards
│   │   ├── impot_federal.py         # Federal tax withholding (T4127)
│   │   ├── impot_quebec.py          # Quebec tax withholding (TP-1015.F-V)
│   │   ├── journal.py               # Beancount transaction generation
│   │   └── ytd.py                   # Year-to-date tracking
│   ├── taxes/                       # GST/QST tracking
│   │   ├── __init__.py
│   │   ├── calcul.py                # Tax extraction/application math
│   │   ├── traitement.py            # Tax treatment rules engine
│   │   └── sommaire.py              # Filing period summaries
│   ├── dpa/                         # CCA (deduction pour amortissement)
│   │   ├── __init__.py
│   │   ├── classes.py               # CCA class definitions and rates
│   │   ├── registre.py              # Asset registry and pool tracking
│   │   ├── calcul.py                # Depreciation calculations
│   │   └── journal.py               # Beancount transaction generation
│   └── pret_actionnaire/            # Shareholder loan
│       ├── __init__.py
│       ├── suivi.py                 # Loan tracking and balance
│       ├── alertes.py               # s.15(2) deadline alerts
│       └── detection.py             # Personal transaction detection
├── cli/
│   ├── paie.py                      # NEW: `cqc paie` subcommands
│   ├── taxes.py                     # NEW: `cqc tps-tvq` subcommands
│   ├── dpa.py                       # NEW: `cqc dpa` subcommands
│   └── pret_actionnaire.py          # NEW: `cqc pret-actionnaire` subcommands
rules/
├── categorisation.yaml              # (from Phase 1)
└── taxes.yaml                       # NEW: GST/QST treatment rules
```

### Pattern 1: Centralized Rate Configuration (rates.py)

**What:** A single Python module containing all rates, thresholds, and maximums indexed by tax year.
**When to use:** Every calculation in every domain module references rates.py.
**Why:** Rates change annually. A single update point prevents scattered magic numbers.

```python
# src/compteqc/quebec/rates.py
from decimal import Decimal
from dataclasses import dataclass

@dataclass(frozen=True)
class TauxQPP:
    """Taux du Regime de rentes du Quebec pour une annee donnee."""
    taux_base: Decimal          # 5.3% in 2026
    taux_supplementaire_1: Decimal  # 1.0% in 2026
    taux_supplementaire_2: Decimal  # 4.0% in 2026
    exemption: Decimal          # $3,500
    mga: Decimal                # Maximum des gains admissibles ($74,600 in 2026)
    mgap: Decimal               # MGA supplementaire ($85,000 in 2026)
    max_base: Decimal           # $3,768.30
    max_supp1: Decimal          # $711.00
    max_supp2: Decimal          # $416.00

@dataclass(frozen=True)
class TauxRQAP:
    taux_employeur: Decimal     # 0.602%
    taux_employe: Decimal       # 0.430%
    mra: Decimal                # Maximum des revenus assurables ($103,000)
    max_employeur: Decimal      # $620.06
    max_employe: Decimal        # $442.90

@dataclass(frozen=True)
class TauxAE:
    taux_employe: Decimal       # 1.30% (Quebec rate)
    taux_employeur: Decimal     # 1.82% (1.4x)
    mra: Decimal                # $68,900
    max_employe: Decimal        # $895.70
    max_employeur: Decimal      # $1,253.98

@dataclass(frozen=True)
class TauxFSS:
    taux_service_petite: Decimal  # 1.65% (payroll <= $1M, service sector)
    seuil_masse_salariale: Decimal  # $1,000,000

@dataclass(frozen=True)
class TrancheFederale:
    seuil: Decimal
    taux: Decimal
    constante_k: Decimal

@dataclass(frozen=True)
class TrancheQuebec:
    seuil: Decimal
    taux: Decimal
    constante: Decimal

@dataclass(frozen=True)
class TauxAnnuels:
    annee: int
    qpp: TauxQPP
    rqap: TauxRQAP
    ae: TauxAE
    fss: TauxFSS
    cnesst_taux: Decimal            # Configurable per employer
    normes_travail_taux: Decimal    # 0.06%
    normes_travail_max_gains: Decimal  # $103,000
    tranches_federales: list        # List[TrancheFederale]
    tranches_quebec: list           # List[TrancheQuebec]
    montant_personnel_federal: Decimal  # $16,452
    montant_personnel_quebec: Decimal   # $18,952
    abattement_quebec: Decimal      # 0.165 (16.5%)
    tps_taux: Decimal               # 0.05
    tvq_taux: Decimal               # 0.09975

TAUX_2026 = TauxAnnuels(
    annee=2026,
    qpp=TauxQPP(
        taux_base=Decimal("0.053"),
        taux_supplementaire_1=Decimal("0.01"),
        taux_supplementaire_2=Decimal("0.04"),
        exemption=Decimal("3500"),
        mga=Decimal("74600"),
        mgap=Decimal("85000"),
        max_base=Decimal("3768.30"),
        max_supp1=Decimal("711.00"),
        max_supp2=Decimal("416.00"),
    ),
    rqap=TauxRQAP(
        taux_employeur=Decimal("0.00602"),
        taux_employe=Decimal("0.00430"),
        mra=Decimal("103000"),
        max_employeur=Decimal("620.06"),
        max_employe=Decimal("442.90"),
    ),
    ae=TauxAE(
        taux_employe=Decimal("0.0130"),
        taux_employeur=Decimal("0.0182"),
        mra=Decimal("68900"),
        max_employe=Decimal("895.70"),
        max_employeur=Decimal("1253.98"),
    ),
    fss=TauxFSS(
        taux_service_petite=Decimal("0.0165"),
        seuil_masse_salariale=Decimal("1000000"),
    ),
    cnesst_taux=Decimal("0.0080"),  # Default placeholder; user must configure
    normes_travail_taux=Decimal("0.0006"),
    normes_travail_max_gains=Decimal("103000"),
    # ... tax brackets defined below in Code Examples
    tranches_federales=[],  # Populated in actual implementation
    tranches_quebec=[],     # Populated in actual implementation
    montant_personnel_federal=Decimal("16452"),
    montant_personnel_quebec=Decimal("18952"),
    abattement_quebec=Decimal("0.165"),
    tps_taux=Decimal("0.05"),
    tvq_taux=Decimal("0.09975"),
)

# Registry for multi-year support
TAUX = {2026: TAUX_2026}

def obtenir_taux(annee: int) -> TauxAnnuels:
    if annee not in TAUX:
        raise ValueError(f"Taux non disponibles pour l'annee {annee}. Annees disponibles: {sorted(TAUX.keys())}")
    return TAUX[annee]
```

### Pattern 2: Pure Calculation Functions with Decimal Math

**What:** All calculation functions are pure (no side effects), take Decimal inputs, return Decimal outputs, never use float.
**When to use:** Every payroll, GST/QST, and CCA calculation.

```python
# src/compteqc/quebec/paie/cotisations.py
from decimal import Decimal, ROUND_HALF_UP

def calculer_qpp_base_employe(
    salaire_brut_periode: Decimal,
    cumul_annuel: Decimal,
    taux: "TauxQPP",
    nb_periodes: int,
) -> Decimal:
    """Calcule la cotisation QPP de base pour une periode de paie.

    Args:
        salaire_brut_periode: Salaire brut pour cette periode
        cumul_annuel: Cotisations QPP base deja versees cette annee (YTD)
        taux: Taux QPP pour l'annee courante
        nb_periodes: Nombre de periodes de paie dans l'annee

    Returns:
        Cotisation QPP base employe pour cette periode
    """
    exemption_periode = (taux.exemption / nb_periodes).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    gains_cotisables = max(
        Decimal("0"),
        min(salaire_brut_periode, taux.mga / nb_periodes) - exemption_periode
    )
    cotisation = (gains_cotisables * taux.taux_base).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    # Cap at annual maximum minus YTD
    reste = max(Decimal("0"), taux.max_base - cumul_annuel)
    return min(cotisation, reste)
```

### Pattern 3: Transaction Generator (Beancount Journal Entries)

**What:** A module that takes calculation results and produces Beancount transaction objects.
**When to use:** After payroll calculations, CCA depreciation, GST/QST adjustments.

```python
# src/compteqc/quebec/paie/journal.py
from beancount.core import data, amount
from beancount.core.number import D
from decimal import Decimal
import datetime

def generer_transaction_paie(
    date_paie: datetime.date,
    resultats: "ResultatPaie",
    comptes: dict[str, str],
) -> data.Transaction:
    """Genere une transaction Beancount complete pour une paie.

    La transaction a ~15 postings:
    - Dr Depenses:Salaires:Brut (salaire brut)
    - Cr Passifs:Retenues-A-Payer (each employee deduction)
    - Cr Actifs:Banque:RBC:Cheques (net pay)
    - Dr Depenses:Salaires:RRQ-Employeur (employer QPP)
    - Dr Depenses:Salaires:RQAP-Employeur (employer RQAP)
    - Dr Depenses:Salaires:AE-Employeur (employer EI)
    - Dr Depenses:Salaires:FSS (employer FSS)
    - Dr Depenses:Salaires:CNESST (employer CNESST)
    - Dr Depenses:Salaires:Normes-Travail (employer labour standards)
    - Cr Passifs:Cotisations-Employeur (total employer contributions payable)
    """
    meta = data.new_metadata("<paie>", 0)
    meta["type"] = "paie"
    meta["periode"] = str(resultats.numero_periode)
    meta["brut"] = str(resultats.brut)

    txn = data.Transaction(
        meta=meta,
        date=date_paie,
        flag="*",
        payee=None,
        narration=f"Paie #{resultats.numero_periode} - Salaire brut {resultats.brut} CAD",
        tags=frozenset({"paie"}),
        links=frozenset(),
        postings=[],
    )

    # Salary expense (debit)
    data.create_simple_posting(txn, "Depenses:Salaires:Brut", resultats.brut, "CAD")

    # Employee deductions (credits to liability)
    data.create_simple_posting(txn, "Passifs:Retenues-A-Payer", -resultats.qpp_employe, "CAD")
    data.create_simple_posting(txn, "Passifs:Retenues-A-Payer", -resultats.rqap_employe, "CAD")
    data.create_simple_posting(txn, "Passifs:Retenues-A-Payer", -resultats.ae_employe, "CAD")
    data.create_simple_posting(txn, "Passifs:Retenues-A-Payer", -resultats.impot_federal, "CAD")
    data.create_simple_posting(txn, "Passifs:Retenues-A-Payer", -resultats.impot_quebec, "CAD")

    # Net pay (credit to bank)
    data.create_simple_posting(txn, "Actifs:Banque:RBC:Cheques", -resultats.net, "CAD")

    # Employer contributions (debit to expense)
    data.create_simple_posting(txn, "Depenses:Salaires:RRQ-Employeur", resultats.qpp_employeur, "CAD")
    data.create_simple_posting(txn, "Depenses:Salaires:RQAP-Employeur", resultats.rqap_employeur, "CAD")
    data.create_simple_posting(txn, "Depenses:Salaires:AE-Employeur", resultats.ae_employeur, "CAD")
    data.create_simple_posting(txn, "Depenses:Salaires:FSS", resultats.fss, "CAD")
    data.create_simple_posting(txn, "Depenses:Salaires:CNESST", resultats.cnesst, "CAD")
    data.create_simple_posting(txn, "Depenses:Salaires:Normes-Travail", resultats.normes_travail, "CAD")

    # Employer contributions payable (credit to liability)
    data.create_simple_posting(
        txn, "Passifs:Cotisations-Employeur",
        -(resultats.qpp_employeur + resultats.rqap_employeur + resultats.ae_employeur
          + resultats.fss + resultats.cnesst + resultats.normes_travail),
        "CAD"
    )

    return txn
```

### Pattern 4: GST/QST Tax Extraction from Total

**What:** Reverse-calculate GST and QST from a tax-included total amount.
**When to use:** Every business expense imported from bank feed (amounts are tax-included).

```python
# src/compteqc/quebec/taxes/calcul.py
from decimal import Decimal, ROUND_HALF_UP

TAUX_COMBINE = Decimal("1.14975")  # 1 + 0.05 + 0.09975

def extraire_taxes(
    total_ttc: Decimal,
    taux_tps: Decimal = Decimal("0.05"),
    taux_tvq: Decimal = Decimal("0.09975"),
) -> tuple[Decimal, Decimal, Decimal]:
    """Extrait TPS et TVQ d'un montant TTC (taxes incluses).

    Returns:
        (montant_avant_taxes, tps, tvq)

    Note: TPS et TVQ sont arrondis independamment au cent pres.
    La somme avant_taxes + tps + tvq peut differer du total de +/- $0.01.
    """
    avant_taxes = (total_ttc / (Decimal("1") + taux_tps + taux_tvq)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    tps = (avant_taxes * taux_tps).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tvq = (avant_taxes * taux_tvq).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return avant_taxes, tps, tvq
```

### Pattern 5: CCA Pool-Level Calculation

**What:** Track UCC per CCA class at the pool level, calculate annual CCA with half-year rule.
**When to use:** Year-end CCA calculation and asset management.

```python
# src/compteqc/quebec/dpa/calcul.py
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass

@dataclass
class PoolDPA:
    """Etat d'un pool de DPA (CCA) pour une classe donnee."""
    classe: int
    taux: Decimal
    ucc_ouverture: Decimal = Decimal("0")
    acquisitions: Decimal = Decimal("0")
    dispositions: Decimal = Decimal("0")

    @property
    def additions_nettes(self) -> Decimal:
        return self.acquisitions - self.dispositions

    def calculer_dpa(self) -> Decimal:
        """Calcule la DPA pour l'annee avec regle du demi-taux sur additions nettes."""
        if self.additions_nettes > 0:
            # Half-year rule on net additions
            base = self.ucc_ouverture + (self.additions_nettes * Decimal("0.5"))
        else:
            base = self.ucc_ouverture + self.additions_nettes

        if base <= 0:
            return Decimal("0")

        dpa = (base * self.taux).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return dpa

    @property
    def ucc_fermeture(self) -> Decimal:
        return self.ucc_ouverture + self.additions_nettes - self.calculer_dpa()

    @property
    def recapture(self) -> Decimal:
        """Recapture si UCC apres dispositions est negatif."""
        ucc_apres = self.ucc_ouverture - self.dispositions
        if ucc_apres < 0:
            return abs(ucc_apres)
        return Decimal("0")

    @property
    def perte_finale(self) -> Decimal:
        """Perte finale si classe vide et UCC > 0."""
        # Only if no assets remain in class and UCC > 0
        # Requires checking asset registry (external)
        return Decimal("0")  # Placeholder -- needs asset count check
```

### Pattern 6: Shareholder Loan Deadline Tracking

**What:** Calculate s.15(2) inclusion dates and generate graduated alerts.
**When to use:** Shareholder loan monitoring, CLI status command.

```python
# src/compteqc/quebec/pret_actionnaire/alertes.py
import datetime
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta

@dataclass
class AlertePret:
    date_avance: datetime.date
    montant: "Decimal"
    date_inclusion: datetime.date  # Fiscal year-end + 1 year
    alerte_9_mois: datetime.date
    alerte_11_mois: datetime.date
    alerte_30_jours: datetime.date

def calculer_dates_alerte(
    date_avance: datetime.date,
    fin_exercice: datetime.date,
) -> AlertePret:
    """Calcule les dates d'alerte s.15(2) pour une avance a l'actionnaire.

    La date d'inclusion est la fin de l'exercice fiscal de la societe
    dans lequel l'avance a ete faite, plus 1 an.

    Exemple: avance en juin 2026, exercice Dec 31 ->
    inclusion = Dec 31, 2027
    alerte 9 mois avant = Mar 31, 2027
    alerte 11 mois avant = Jan 31, 2027
    alerte 30 jours avant = Dec 1, 2027
    """
    # Find the fiscal year-end that contains the advance date
    if date_avance <= fin_exercice:
        fin_exercice_applicable = fin_exercice
    else:
        fin_exercice_applicable = fin_exercice.replace(year=fin_exercice.year + 1)

    date_inclusion = fin_exercice_applicable + relativedelta(years=1)

    return AlertePret(
        date_avance=date_avance,
        montant=Decimal("0"),  # Set by caller
        date_inclusion=date_inclusion,
        alerte_9_mois=date_inclusion - relativedelta(months=9),
        alerte_11_mois=date_inclusion - relativedelta(months=11),
        alerte_30_jours=date_inclusion - datetime.timedelta(days=30),
    )
```

### Anti-Patterns to Avoid

- **Float arithmetic anywhere in tax/payroll calculations:** All money math must use `Decimal`. Even intermediate calculations. A single float conversion can cause $0.01 discrepancies that compound across a year of payroll.
- **Hardcoded rates in calculation functions:** All rates must come from `rates.py`. A hardcoded `0.053` in a QPP function is a bug waiting for January 1 of next year.
- **Calculating QPP base + additional as a single 6.3% rate:** The base (5.3%) and additional 1 (1.0%) have the same earnings range but separate maximums. They must be tracked and capped independently for YTD purposes.
- **Combining GST and QST into a single 14.975% rate:** User decision: always track separately. Each rounded independently. This matters for CPA reconciliation and filing.
- **Using a Beancount plugin for payroll/CCA:** Plugins run at load time (passive). Payroll and CCA are on-demand operations (active). Use the CLI to orchestrate, not plugins.
- **Storing YTD state only in memory:** YTD payroll totals must survive between CLI invocations. Derive from existing ledger entries (query all `paie`-tagged transactions) or persist to a JSON state file. Deriving from ledger is preferred (single source of truth).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decimal rounding for taxes | Custom rounding logic | `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` | Python's Decimal handles banker's rounding, tax rounding (ROUND_HALF_UP), etc. correctly |
| Date arithmetic for s.15(2) deadlines | Manual date math | `python-dateutil` `relativedelta` | Month arithmetic is tricky (leap years, 30/31 days). dateutil handles it correctly |
| Beancount transaction creation | Manual string formatting of .beancount files | `beancount.core.data.Transaction` + `create_simple_posting` | Beancount's data API ensures valid transactions that pass bean-check |
| YTD payroll accumulation | Custom state file | `beanquery` against existing ledger entries | Query `SELECT sum(position) WHERE account ~ 'Passifs:Retenues-A-Payer' AND tag = 'paie' AND year = 2026` to derive YTD from ledger (single source of truth) |
| Tax bracket calculation | Manual if/else chains | Lookup table with constants | Federal T4127 uses R (rate) and K (constant) per bracket: `tax = R * A - K`. Same pattern for Quebec. Avoids bracket boundary bugs |

**Key insight:** The domain logic is entirely custom (no off-the-shelf Quebec payroll library exists in Python). But the infrastructure (Decimal math, Beancount transactions, date arithmetic, CLI framework) is all standard library or established packages. The custom work is encoding the formulas from T4127 and TP-1015.F-V into tested Python functions.

## Common Pitfalls

### Pitfall 1: QPP Rate Confusion (QPP vs CPP)
**What goes wrong:** Using CPP rates (5.95%) instead of QPP rates (5.3% base + 1.0% additional 1 = 6.3% combined) for Quebec employees. The combined rate looks similar but the split and maximums are different.
**Why it happens:** CRA T4032 tables show CPP by default. Quebec employees use QPP (administered by Retraite Quebec), which has different rates and breakpoints. The T4127 guide uses `0.0630` for the combined QPP rate in the K2Q formula, which can be misread.
**How to avoid:** Always reference Retraite Quebec for QPP rates, not CRA for CPP. The key difference: QPP base is 5.3% (not CPP's 5.95%), and QPP has a separate "additional 1" at 1.0%. Both have "additional 2" at 4.0% on $74,600-$85,000.
**Warning signs:** Annual QPP maximum doesn't match expected $3,768.30 (base) or $4,479.30 (base + additional 1).

### Pitfall 2: Federal Tax Rate Change for 2026 (14% not 15%)
**What goes wrong:** Using the old 15% lowest federal bracket rate instead of the new 14% rate effective January 1, 2026.
**Why it happens:** Most online calculators and guides still reference the 2025 rate of 15%. The change to 14% was announced and takes effect in 2026.
**How to avoid:** The T4127 122nd Edition (January 2026) confirms: lowest federal rate is 14%. All K constants and bracket calculations must use 14%. This also affects K2Q credit calculations (which use the lowest rate: `0.14 * ...`).
**Warning signs:** Federal withholding is slightly higher than expected. K2Q credits are slightly wrong.

### Pitfall 3: Rounding Discrepancies in GST/QST Extraction
**What goes wrong:** Extracting GST and QST from a total produces amounts that don't sum back to the original total (off by $0.01).
**Why it happens:** When you reverse-calculate from a tax-included total, rounding GST and QST independently to $0.01 can cause a $0.01 discrepancy because: `floor(total / 1.14975 * 0.05) + floor(total / 1.14975 * 0.09975) + floor(total / 1.14975)` may not equal `total`.
**How to avoid:** Accept the $0.01 discrepancy -- this is normal and expected in Canadian tax calculations. The pre-tax amount should be the "plug" value: `pre_tax = total - gst - qst`. Document this behavior. The CPA expects it.
**Warning signs:** bean-check balance errors if you don't handle the rounding plug.

### Pitfall 4: Shareholder Loan Inclusion Date Miscalculation
**What goes wrong:** Computing the s.15(2) inclusion date as "loan date + 1 year" instead of "fiscal year-end + 1 year".
**Why it happens:** The ITA says the loan must be repaid "within one year after the end of the taxation year of the lender in which the loan was made." The key phrase is "end of the taxation year" -- not the loan date.
**How to avoid:** For Dec 31 FYE: any loan made in 2026 (whether January or December) has an inclusion date of December 31, 2027. The deadline is always relative to the fiscal year-end that contains the loan, not the loan date itself.
**Warning signs:** Alerts fire too early or too late. Loans made in December appear to have a shorter deadline than loans made in January (they shouldn't -- both have the same deadline).

### Pitfall 5: CCA Half-Year Rule on Net Additions (Not Gross)
**What goes wrong:** Applying the half-year rule to gross acquisitions instead of net additions (acquisitions minus disposals).
**Why it happens:** Simplified examples often show the half-year rule on a single purchase. When there are both acquisitions and disposals in the same year, the half-year rule applies to the *net* addition to the class.
**How to avoid:** Calculate: `net_addition = acquisitions - disposals_at_lesser_of_cost_or_proceeds`. If net_addition > 0, apply 50% rule. If net_addition < 0, no half-year adjustment needed.
**Warning signs:** CCA claimed exceeds CPA's calculation for years with both purchases and sales.

### Pitfall 6: FSS Calculated Per-Pay-Period Instead of Annually
**What goes wrong:** Applying FSS rate to each paycheque's gross amount instead of the total annual payroll.
**Why it happens:** Other contributions (QPP, RQAP, EI) are calculated per pay period with annual caps. FSS is different: it's an employer-only contribution based on total annual payroll, but remitted periodically.
**How to avoid:** FSS is calculated as: `total_annual_payroll * rate`. For periodic remittance, divide the estimated annual amount by the number of pay periods. Reconcile at year-end.
**Warning signs:** FSS total doesn't match `total_salary_expense * 1.65%`.

### Pitfall 7: Circular Loan-Repayment-Reborrow (s.15(2.6))
**What goes wrong:** Shareholder repays loan before deadline, then immediately reborrows. CRA treats this as if the original loan was never repaid.
**Why it happens:** s.15(2.6) exception requires that "repayment was not part of a series of loans or other transactions and repayments." If a repayment is followed by a new advance of similar amount within a short period, CRA will argue it's a series.
**How to avoid:** Flag any reborrow within 30-60 days of a repayment as potential circular pattern. Alert the user. Do not auto-clear the original loan deadline just because a repayment was recorded.
**Warning signs:** Shareholder loan balance drops to zero then immediately jumps back up.

## Code Examples

### Complete Federal Tax Withholding Calculation (T4127 for Quebec)

```python
# Source: T4127 122nd Edition (January 2026) - CRA
# Verified: 2026-02-19

from decimal import Decimal, ROUND_HALF_UP

# 2026 Federal tax brackets (R=rate, K=constant)
TRANCHES_FEDERALES_2026 = [
    # (seuil_max, taux, constante_K)
    (Decimal("58523"), Decimal("0.14"), Decimal("0")),
    (Decimal("117045"), Decimal("0.205"), Decimal("3804")),
    (Decimal("181440"), Decimal("0.26"), Decimal("10237")),
    (Decimal("258482"), Decimal("0.29"), Decimal("15680")),
    (Decimal("999999999"), Decimal("0.33"), Decimal("26019")),
]

def calculer_impot_federal_quebec(
    revenu_annualise: Decimal,
    montant_personnel: Decimal,
    credits_qpp: Decimal,
    credits_ae: Decimal,
    credits_rqap: Decimal,
) -> Decimal:
    """Calcule l'impot federal annuel pour un employe du Quebec.

    Formule T4127:
    T3 = (R * A) - K - K1 - K2Q - K3 - K4
    T1 = T3 - (0.165 * T3)  [Quebec abatement]

    Args:
        revenu_annualise: A = revenu imposable annualise
        montant_personnel: TC from TD1 form (basic personal amount)
        credits_qpp: Annual QPP employee contributions (for K2Q)
        credits_ae: Annual EI employee premiums (for K2Q)
        credits_rqap: Annual RQAP employee premiums (for K2Q)

    Returns:
        T1 = impot federal annuel apres abattement Quebec
    """
    A = revenu_annualise

    # Find applicable bracket
    R = Decimal("0")
    K = Decimal("0")
    for seuil, taux, constante in TRANCHES_FEDERALES_2026:
        if A <= seuil:
            R = taux
            K = constante
            break

    # K1 = basic personal tax credit
    K1 = (Decimal("0.14") * montant_personnel).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # K2Q = QPP + EI + RQAP credits (Quebec-specific)
    # QPP credit uses base rate portion only: contributions * (0.053/0.063)
    qpp_base_portion = (credits_qpp * Decimal("0.053") / Decimal("0.063")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    K2Q = (Decimal("0.14") * (qpp_base_portion + credits_ae + credits_rqap)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # K4 = Canada employment credit (fixed amount)
    K4 = (Decimal("0.14") * Decimal("1428")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # T3 = basic federal tax
    T3 = max(Decimal("0"), (R * A) - K - K1 - K2Q - K4)

    # T1 = federal tax after Quebec abatement (16.5%)
    T1 = max(Decimal("0"), T3 - (Decimal("0.165") * T3))

    return T1.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### Quebec Provincial Tax Withholding (TP-1015.F-V)

```python
# Source: TP-1015.F-V (2026-01) - Revenu Quebec
# Note: Exact variable names from TP-1015.F-V; formula reconstructed from
# research document + official rate tables. MEDIUM confidence on exact step
# ordering -- validate against WebRAS calculator.

TRANCHES_QUEBEC_2026 = [
    # (seuil_max, taux, constante)
    (Decimal("54345"), Decimal("0.14"), Decimal("0")),
    (Decimal("108680"), Decimal("0.19"), Decimal("2717")),
    (Decimal("132245"), Decimal("0.24"), Decimal("5151")),
    (Decimal("999999999"), Decimal("0.2575"), Decimal("7465")),
]

def calculer_impot_quebec(
    revenu_annualise: Decimal,
    montant_personnel: Decimal,
    credits_qpp: Decimal,
    credits_rqap: Decimal,
) -> Decimal:
    """Calcule l'impot provincial Quebec annuel.

    Formule simplifiee TP-1015.F-V:
    Y = (T * A) - K - K1 - E
    Ou:
    - A = revenu imposable annualise
    - T, K = taux et constante de la tranche applicable
    - K1 = credit personnel de base
    - E = credits pour cotisations (QPP + RQAP)

    Args:
        revenu_annualise: Revenu imposable annualise (G * P - deductions)
        montant_personnel: Montant personnel de base Quebec ($18,952 en 2026)
        credits_qpp: Cotisations QPP employe annuelles
        credits_rqap: Cotisations RQAP employe annuelles

    Returns:
        Impot Quebec annuel
    """
    A = revenu_annualise

    # Find applicable bracket
    T_rate = Decimal("0")
    K_const = Decimal("0")
    for seuil, taux, constante in TRANCHES_QUEBEC_2026:
        if A <= seuil:
            T_rate = taux
            K_const = constante
            break

    # K1 = credit de base (taux le plus bas * montant personnel)
    K1 = (Decimal("0.14") * montant_personnel).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # E = credits pour cotisations (QPP + RQAP)
    E = (Decimal("0.14") * (credits_qpp + credits_rqap)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Y = impot provincial
    Y = max(Decimal("0"), (T_rate * A) - K_const - K1 - E)

    return Y.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### GST/QST Tax Treatment Rules (YAML Config)

```yaml
# rules/taxes.yaml
# Regles de traitement fiscal GST/QST
# Priorite: vendeur > categorie > defaut (taxable)

defaut: taxable  # Nouveaux vendeurs = taxable jusqu'a confirmation

categories:
  # Depenses toujours exemptes de TPS/TVQ
  exempt:
    - "Depenses:Frais-Bancaires"      # Services financiers
    - "Depenses:Interet:Bancaire"      # Interets
    - "Depenses:Assurances:*"          # Primes d'assurance
    - "Depenses:Salaires:*"            # Salaires (pas de TPS/TVQ)

  # Depenses a taux zero (differentes d'exemptes pour le reporting)
  zero:
    - "Depenses:Formation"             # Certaines formations (selon le cas)

  # Toutes les autres categories = taxable (defaut)

vendeurs:
  # Vendeurs avec traitement special (override le defaut de la categorie)
  exempt:
    - payee_regex: ".*BANQUE.*|.*RBC.*|.*DESJARDINS.*"
      raison: "Services financiers"
    - payee_regex: ".*ASSURANCE.*|.*INTACT.*"
      raison: "Primes d'assurance"
    - payee_regex: ".*HYDRO.*QUEBEC.*"
      raison: "Services publics exempts"  # NOTE: verify -- electricity may be taxable

  # Vendeurs avec TPS seulement (hors Quebec)
  tps_seulement:
    - payee_regex: ".*AMAZON.*WEB.*SERVICES.*"
      raison: "Fournisseur hors Quebec"

clients:
  # Regles TPS/TVQ sur les revenus par client
  tps_tvq:  # Quebec clients: both taxes
    - client_regex: ".*PROCOM.*"
    - client_regex: ".*FORMATION.*"

  tps_seulement:  # Out-of-province Canadian
    - client_regex: ".*ACME-TORONTO.*"

  aucune_taxe:  # International
    - client_regex: ".*INTERNATIONAL.*"
```

### YTD Tracking from Ledger (Preferred Approach)

```python
# src/compteqc/quebec/paie/ytd.py
from decimal import Decimal
from beancount import loader
from beanquery import run_query

def obtenir_cumuls_annuels(
    chemin_ledger: str,
    annee: int,
) -> dict[str, Decimal]:
    """Extrait les cumuls annuels de cotisations depuis le ledger.

    Derive les YTD directement des transactions existantes (single source of truth).
    Cherche les transactions avec le tag 'paie' pour l'annee donnee.
    """
    entries, errors, options = loader.load_file(chemin_ledger)

    # Total des retenues QPP employe versees cette annee
    query = f"""
        SELECT sum(position) as total
        WHERE account = 'Passifs:Retenues-A-Payer'
          AND 'paie' IN tags
          AND year = {annee}
          AND ANY_META('type-retenue') = 'qpp-base'
    """
    # This is a simplified example -- actual implementation needs
    # per-deduction-type metadata on each posting to distinguish
    # QPP base from QPP additional from RQAP from EI etc.
    #
    # Alternative: use separate liability sub-accounts:
    #   Passifs:Retenues:QPP-Base
    #   Passifs:Retenues:QPP-Supp1
    #   Passifs:Retenues:RQAP
    #   Passifs:Retenues:AE
    #   Passifs:Retenues:Impot-Federal
    #   Passifs:Retenues:Impot-Quebec
    # This makes YTD queries trivial via beanquery sum by account.

    pass  # Implementation depends on account structure decision
```

## Discretion Recommendations

### 1. Payroll Corrections: Use Reversal + New Entry
**Recommendation:** When a payroll needs correction, generate a full reversal transaction (negating every posting from the original) followed by a complete new payroll transaction with corrected amounts.
**Rationale:** This approach is the standard CPA-friendly method. Both the error and correction are visible in the ledger. The CPA can see exactly what changed. An adjustment delta is harder to audit because it doesn't show the original intent. Reversals also make it trivial to reconcile (original + reversal = zero, new entry stands alone).

### 2. CCA Depreciation: Auto-Generate with Review Flag
**Recommendation:** Generate CCA entries automatically at year-end (via `cqc dpa calculer`) but flag them with `!` (needs review) and display the full schedule for user approval before committing.
**Rationale:** CCA is discretionary (a corporation can claim less than the maximum). Auto-generating with review lets the user see the proposed amounts, adjust if needed (e.g., claim less CCA in a loss year), and approve. This is safer than auto-posting (which removes the discretionary element) and more convenient than fully manual entry.

### 3. Separate Liability Sub-Accounts for YTD Tracking
**Recommendation:** Instead of a single `Passifs:Retenues-A-Payer` account, use separate sub-accounts for each deduction type. This eliminates the need for metadata-based queries to derive YTD totals.
**Rationale:** `Passifs:Retenues:QPP-Base`, `Passifs:Retenues:QPP-Supp1`, `Passifs:Retenues:RQAP`, etc. makes beanquery YTD calculations trivial: `SELECT sum(position) WHERE account = 'Passifs:Retenues:QPP-Base' AND year = 2026`. No metadata parsing needed. The CPA also gets a cleaner breakdown of amounts owing per remittance category.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Federal lowest bracket 15% | 14% for 2026+ | T4127 122nd Edition (Jan 2026) | All federal tax calculations and K2Q credits must use 0.14, not 0.15 |
| QPP single rate 5.4% | QPP base (5.3%) + additional 1 (1.0%) + additional 2 (4.0%) | Phased 2019-2025, fully implemented 2025 | Three-tier QPP calculation required with separate maximums |
| CPP2/QPP2 on earnings above YMPE | 4.0% on $74,600-$85,000 (2026) | CPP2/QPP2 introduced January 2024 | New tier with distinct earnings range and maximum |
| beancount-plugins depreciation | Custom CCA module | Ongoing | v2 plugin has CRA method but no v3 compatibility confirmed; pool-level tracking and disposal handling not supported |

**Deprecated/outdated:**
- Federal 15% lowest rate: replaced by 14% effective 2026
- Single-tier QPP: replaced by three-tier system (base + additional 1 + additional 2)
- Many online payroll calculators still show 2025 rates -- always verify against official 2026 publications

## Open Questions

1. **Exact TP-1015.F-V formula variable mapping**
   - What we know: The general structure (annualize, apply brackets, subtract credits, de-annualize). Quebec tax brackets and personal amounts for 2026 are confirmed.
   - What's unclear: The exact variable names (G, F, H, J, etc.) and intermediate step ordering from the TP-1015.F-V PDF (which couldn't be machine-parsed). The formula for handling the "deduction for workers" (~$1,450) and other Quebec-specific deductions.
   - Recommendation: Validate implementation against Revenu Quebec's WebRAS calculator (https://www.revenuquebec.ca/en/online-services/tools/webras/) with test cases. Run 3-5 salary scenarios through WebRAS and compare outputs. This is the authoritative validation method. **MEDIUM confidence on Quebec tax withholding until validated against WebRAS.**

2. **CNESST classification rate for IT consulting**
   - What we know: CNESST rates are employer-specific, assigned by classification unit. IT consulting is low-risk office work (typically 0.5%-1.5%).
   - What's unclear: The exact rate assigned to this specific corporation. The classification unit code for IT consulting.
   - Recommendation: Make the CNESST rate configurable in rates.py with a sensible default (0.80%). User must update with their actual rate from their annual CNESST classification notice.

3. **Liability sub-account structure for payroll remittances**
   - What we know: Separate sub-accounts for each deduction type simplify YTD tracking and CPA reporting.
   - What's unclear: Whether the existing Phase 1 chart of accounts needs modification (currently has single `Passifs:Retenues-A-Payer` and `Passifs:Cotisations-Employeur`).
   - Recommendation: Expand to ~10 sub-accounts during Phase 2 implementation. This is a chart of accounts modification that requires updating `comptes.beancount`. Plan this as a Phase 2 task.

4. **beancount-plugins flexible_depreciation v3 compatibility**
   - What we know: The plugin exists, supports CRA method with half-year rule, and is installable via PyPI.
   - What's unclear: Whether it works with Beancount v3 (3.2.0). The plugin repository shows no recent updates or v3 compatibility notes.
   - Recommendation: Do NOT depend on this plugin. Build a custom CCA module. The CCA calculation is straightforward (declining balance + half-year rule) and we need pool-level tracking and disposal handling that the plugin doesn't provide. The plugin is useful as a reference for the metadata format pattern.

5. **GST/QST on electricity (Hydro-Quebec)**
   - What we know: Many utilities are GST/QST taxable. Financial services and insurance are exempt.
   - What's unclear: Whether Hydro-Quebec electricity charges include GST/QST (they typically do for commercial accounts).
   - Recommendation: Default Hydro-Quebec to "taxable" in the vendor rules. User can override if their specific billing doesn't include tax. Flag as LOW confidence item for user verification.

## Sources

### Primary (HIGH confidence)
- [Retraite Quebec - QPP contribution rates 2026](https://www.retraitequebec.gouv.qc.ca/en/employeur/role_rrq/Pages/cotisations.aspx) - QPP base 5.3%, additional 1 1.0%, additional 2 4.0%, exemption $3,500, MGA $74,600, MGAP $85,000
- [T4127 122nd Edition - Payroll Deductions Formulas (January 2026)](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4127-payroll-deductions-formulas/t4127-jan/t4127-jan-payroll-deductions-formulas-computer-programs.html) - Federal tax brackets, K constants, K2Q formula, Quebec abatement 16.5%, 2026 lowest rate 14%
- [TP-1015.F-V (2026-01) - Formulas to Calculate Source Deductions](https://www.revenuquebec.ca/en/online-services/forms-and-publications/current-details/tp-1015-f-v/) - Quebec income tax withholding formulas (PDF, 590KB)
- [Revenu Quebec - FSS contribution rates](https://www.revenuquebec.ca/en/businesses/source-deductions-and-employer-contributions/calculating-source-deductions-and-employer-contributions/employer-contributions-to-the-health-services-fund/) - 1.65% for service sector, payroll <= $1M
- [CRA - CCA classes of depreciable property](https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/sole-proprietorships-partnerships/report-business-income-expenses/claiming-capital-cost-allowance/classes-depreciable-property.html) - Class 8 (20%), 10 (30%), 12 (100%), 50 (55%), 54 (30%)
- [ITA Section 15(2) - Shareholder loans](https://laws-lois.justice.gc.ca/eng/acts/I-3.3/section-15.html) - Inclusion rules, one-year repayment window after fiscal year-end
- Context7 `/websites/beancount_github_io_index` - Plugin API, Transaction creation, create_simple_posting
- [Nethris - QPP rates hub](https://nethris.com/legislation/quebec-pension-plan/) - QPP base 6.30% combined (5.3% + 1.0%), max $4,479.30, YAMPE $85,000
- Project research document `research/quebec_incorporation_reference.md` - Comprehensive rates reference (verified against official sources)

### Secondary (MEDIUM confidence)
- [T4032-QC January 2026 General Information](https://www.canada.ca/en/revenue-agency/services/forms-publications/payroll/t4032-payroll-deductions-tables/t4032qc-jan/t4032qc-january-general-information.html) - EI Quebec rate 1.30% employee, 1.82% employer, MIE $68,900
- [beancount-plugins depreciation (GitHub)](https://github.com/davidastephens/beancount-plugins) - CRA method with half-year rule, metadata format. Unknown v3 compatibility.
- [CNESST Schedule of Rates](https://www.cnesst.gouv.qc.ca/en/forms-and-publications/schedule-rates) - Rate structure (specific IT consulting rate not found)
- [Accumulated Depreciation for Beancount (beancount.io)](https://beancount.io/blog/2025/08/23/accumulated-depreciation) - Depreciation patterns in Beancount

### Tertiary (LOW confidence)
- Quebec income tax withholding exact formula step ordering - TP-1015.F-V PDF could not be machine-parsed. Formula reconstructed from: research document rates, Revenu Quebec web pages, and T4127 Quebec-specific sections. Must validate against WebRAS.
- Hydro-Quebec GST/QST treatment - assumed taxable for commercial accounts, needs user verification
- CNESST IT consulting rate - estimated 0.80%, actual rate must come from employer's classification notice

## Metadata

**Confidence breakdown:**
- Payroll contribution rates (QPP, RQAP, EI, FSS, labour standards): HIGH -- verified against official sources (Retraite Quebec, Revenu Quebec, CRA)
- Federal tax withholding (T4127): HIGH -- formula structure and 2026 brackets verified from CRA publication
- Quebec tax withholding (TP-1015.F-V): MEDIUM -- brackets and personal amounts confirmed, exact formula step ordering needs WebRAS validation
- GST/QST math: HIGH -- reverse calculation formula is standard, rounding behavior documented
- CCA calculations: HIGH -- declining balance + half-year rule well-documented by CRA
- Shareholder loan s.15(2): HIGH -- ITA section verified, deadline calculation confirmed from multiple legal sources
- Architecture patterns: HIGH -- builds on verified Phase 1 patterns (Beancount data API, Typer CLI, YAML config)

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (rates are annual; architecture is stable)
