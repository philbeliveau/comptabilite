# Phase 1: Ledger Foundation and Import Pipeline - Research

**Researched:** 2026-02-19
**Domain:** Beancount v3 double-entry ledger, CSV/OFX import, rule-based categorization, CLI
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Plan comptable (Chart of Accounts)**
  - Granularite moderee (~50-60 comptes) : assez detaille pour etre utile sans devenir du bruit
  - Revenu unique pour l'instant (pas de split consulting vs Enact) ; on separera quand Enact genere des revenus
  - Noms de comptes en francais (ex: "Depenses:Bureau:Abonnements-Logiciels", "Revenus:Consultation")
  - Mappage GIFI : a la discretion de Claude (metadata Beancount ou fichier separe)

- **Import et normalisation**
  - Deux comptes a importer : compte-cheques RBC + carte de credit RBC
  - Les deux formats disponibles (CSV et OFX/QFX) -- Claude choisit le meilleur ou supporte les deux
  - Devise CAD uniquement pour la Phase 1 (pas de multi-devises)
  - Deduplication : a la discretion de Claude (approche la plus sure pour l'exactitude comptable)

- **Categorisation par regles**
  - Format des regles : a la discretion de Claude (YAML, Python, ou autre selon les conventions Beancount)
  - Transactions sans correspondance : postees dans un compte "Non-classe" (holding account) pour revue ulterieure
  - Pas de pre-chargement de regles -- on commence vide et on batit au fur et a mesure des imports
  - Suggestion automatique de regles apres categorisation manuelle : a la discretion de Claude

- **CLI**
  - Nom de commande : `cqc` (CompteQC)
  - Langue de l'interface CLI : francais (messages, aide, erreurs, prompts)
  - Format de sortie par defaut des rapports : a la discretion de Claude
  - Flux d'import quotidien : a la discretion de Claude (balance entre vitesse et securite)

- **Hard constraints from CLAUDE.md:**
  - All monetary amounts must use Decimal (never float)
  - Ledger data as plain-text .beancount files under git version control with auto-commit on changes
  - bean-check must pass after every import
  - System must not silently invent categories or numbers

### Claude's Discretion
- Stockage du mappage GIFI (metadata vs fichier separe)
- Choix de format d'import prefere (CSV vs OFX) ou support des deux
- Strategie de deduplication des transactions
- Format de definition des regles de categorisation
- Suggestion automatique de regles apres correction manuelle
- Format de sortie par defaut (table, plain text, etc.)
- Design du flux import -> revue -> post (une etape ou plusieurs)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

## Summary

Phase 1 builds the foundation: a working Beancount v3 ledger with a Quebec-appropriate chart of accounts (GIFI-mapped, French names, ~50-60 accounts), importers for RBC chequing and credit card transactions (CSV and OFX), a rule-based categorization engine, and a CLI (`cqc`) with French-language interface for import and reporting.

The technical stack is well-established and verified. Beancount 3.2.0 is the current stable release on PyPI, with beangulp 0.2.0 as the official import framework (replacing the old `beancount.ingest`). Fava 1.30.12 is compatible with Beancount v3. The beangulp `csvbase.Importer` provides a declarative column-mapping pattern ideal for RBC CSV parsing, and `ofxtools` 0.9.5 handles OFX/QFX parsing. For the CLI, Typer 0.24.0 with Rich provides a clean French-language interface. All amounts flow through Python `Decimal` natively in Beancount.

**Primary recommendation:** Use beangulp `csvbase.Importer` for CSV and a custom `beangulp.Importer` with `ofxtools` for OFX. Support both formats. Implement GIFI mapping as Beancount metadata on account `open` directives. Use YAML for categorization rules. Build a two-step import flow: extract to staging file, then review and merge into monthly ledger files.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Beancount v3 as double-entry ledger engine with immutable append-only journal | Beancount 3.2.0 verified on PyPI. v3 architecture is modular (beangulp, beanquery separate). Plain-text files are inherently append-only. |
| FOUND-02 | Chart of accounts GIFI-mapped (1000-6999) for Quebec IT consultant CCPC | GIFI codes verified via CRA RC4088. Beancount supports arbitrary metadata on `open` directives for GIFI mapping. Account hierarchy uses colon separator. |
| FOUND-03 | All monetary amounts as Python Decimal, GST/QST stored separately | Beancount natively uses `Decimal` for all amounts. GST/QST are Phase 2 but account structure must accommodate them now. |
| FOUND-04 | Plain-text .beancount files, git-versioned with auto-commit | Beancount `include` directive enables multi-file organization. Git auto-commit is a simple subprocess call after successful bean-check. |
| FOUND-05 | Modular project structure (ledger/, src/ingestion/, src/quebec/, src/mcp/, src/fava_ext/, src/cli/) | Standard Python project structure with uv. `ledger/` holds .beancount files, `src/` holds Python code organized by domain. |
| INGEST-01 | Import RBC business bank account from CSV | RBC CSV format: "Date","Description","Transaction","Debit","Credit","Total". Dates in YYYY-MM-DD. Use beangulp csvbase.Importer with declarative column mapping. |
| INGEST-02 | Import RBC business credit card from CSV | RBC credit card CSV uses similar column structure. May have "Transaction Date","Posting Date","Description","Credit","Debit","Amount". Separate importer needed. |
| INGEST-03 | Import RBC transactions from OFX/QFX | RBC supports OFX/QFX download. Use ofxtools 0.9.5 to parse. OFX provides FITID for reliable deduplication. Build beangulp.Importer wrapping ofxtools. |
| INGEST-04 | Normalize transactions (date, amount CAD, payee, description, memo) | beangulp extract produces Beancount Transaction objects with date, payee, narration, postings. Normalize in extract() method. |
| INGEST-05 | Archive raw files in data/processed/ with import metadata | beangulp has built-in `archive` command that moves files to dated directories. Extend with import metadata in a sidecar JSON file. |
| CAT-01 | Rule-based engine with configurable YAML/TOML rules | No existing Beancount rule engine matches this need. Build custom YAML-based matcher (payee regex -> account mapping). Apply in beangulp importer's finalize() or post-extract hook. |
| CLI-01 | Import bank files via CLI | Typer 0.24.0 with subcommands: `cqc importer <file>`. French-language help and messages. |
| CLI-06 | Query ledger balances and run reports via CLI | beanquery 0.2.0 provides SQL-like queries on Beancount data. Wrap in Typer commands: `cqc soldes`, `cqc rapport`. |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| beancount | 3.2.0 | Double-entry ledger engine | 10+ year track record, Python-native, Decimal math, active development. v3 is modular. [HIGH -- verified PyPI 2026-02-19] |
| beangulp | 0.2.0 | Import framework | Official Beancount import framework, replaces old beancount.ingest. csvbase.Importer for declarative CSV mapping. [HIGH -- verified PyPI] |
| beanquery | 0.2.0 | SQL-like ledger queries | Separated from core in v3. `SELECT account, sum(amount) WHERE ...` on ledger data. [HIGH -- verified PyPI] |
| fava | 1.30.12 | Web UI for ledger browsing | Production-quality Beancount web UI. Compatible with Beancount v3. Not used in Phase 1 CLI but ledger must be Fava-compatible for Phase 4. [HIGH -- verified PyPI] |
| ofxtools | 0.9.5 | OFX/QFX file parsing | Pure Python, handles OFXv1 (SGML) and v2 (XML). Amounts as Decimal. Active maintenance. [HIGH -- verified PyPI] |
| typer | 0.24.0 | CLI framework | Type-hint based CLI. Subcommand support. Built on Click. [HIGH -- verified PyPI] |
| rich | latest | Terminal formatting | Tables, progress bars, colored output. Pairs with Typer. [HIGH] |
| pydantic | 2.x | Data validation | Transaction models, rule config validation. Already a FastAPI dep for future phases. [HIGH] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | latest | Parse YAML rule files | Rule-based categorization config. Human-readable format. [HIGH] |
| gitpython | latest | Git auto-commit | Programmatic git add/commit after import. Alternative: subprocess calls to git CLI. [MEDIUM] |
| pytest | latest | Testing framework | With test fixtures for sample CSV/OFX files. [HIGH] |
| ruff | latest | Linting + formatting | Single tool, replaces Black + isort + flake8. [HIGH] |
| uv | 0.10.x | Package/project management | 10-100x faster than pip. Handles Python versions, lockfiles. [HIGH] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| beangulp csvbase | beancount-reds-importers | reds-importers has a banking importer framework with OFX support built in, but adds a dependency layer. beangulp csvbase is official and simpler for 2 importers. |
| ofxtools | ofxparse | ofxparse is older, stale maintenance. ofxtools actively maintained, handles both OFX v1/v2. |
| YAML rules | Python dict/TOML rules | YAML is the most human-readable for payee-regex-to-account mappings. TOML is stricter but less flexible for lists. Python dicts work but are harder for non-developers to edit. |
| gitpython | subprocess git calls | gitpython adds a dependency. Subprocess calls are simpler for basic add/commit. Recommend subprocess for Phase 1 simplicity. |
| Typer | Click | Typer wraps Click with type hints. Cleaner API for new projects. |

**Installation:**
```bash
uv init compteqc
cd compteqc
uv python install 3.12
uv python pin 3.12

# Core
uv add beancount beangulp beanquery fava ofxtools

# CLI
uv add typer rich

# Data validation + rules
uv add pydantic pyyaml

# Dev
uv add --dev pytest pytest-cov ruff mypy
```

## Architecture Patterns

### Recommended Project Structure
```
compteqc/
├── pyproject.toml
├── ledger/                          # Beancount files (git-versioned)
│   ├── main.beancount               # Root file with includes + options
│   ├── comptes.beancount            # Chart of accounts (open directives)
│   ├── 2026/
│   │   ├── 01.beancount             # Monthly transaction files
│   │   ├── 02.beancount
│   │   └── ...
│   └── staging.beancount            # Newly imported, pending review
├── data/
│   ├── imports/                     # Drop zone for bank downloads
│   └── processed/                   # Archived raw files after import
├── rules/
│   └── categorisation.yaml          # Rule-based categorization rules
├── src/
│   └── compteqc/
│       ├── __init__.py
│       ├── cli/                     # Typer CLI commands
│       │   ├── __init__.py
│       │   ├── app.py               # Main Typer app
│       │   ├── importer.py          # cqc importer subcommands
│       │   └── rapports.py          # cqc rapport/soldes subcommands
│       ├── ingestion/               # Bank importers
│       │   ├── __init__.py
│       │   ├── rbc_cheques.py       # RBC chequing CSV importer
│       │   ├── rbc_carte.py         # RBC credit card CSV importer
│       │   ├── rbc_ofx.py           # RBC OFX/QFX importer
│       │   └── normalisation.py     # Common normalization utilities
│       ├── categorisation/          # Rule engine
│       │   ├── __init__.py
│       │   ├── moteur.py            # Rule matching engine
│       │   └── regles.py            # Rule loading and validation
│       ├── ledger/                  # Ledger management
│       │   ├── __init__.py
│       │   ├── fichiers.py          # File organization (monthly split)
│       │   ├── git.py               # Git auto-commit logic
│       │   └── validation.py        # bean-check wrapper
│       └── models/                  # Pydantic models
│           ├── __init__.py
│           └── transaction.py       # Normalized transaction model
└── tests/
    ├── fixtures/                    # Sample CSV, OFX, beancount files
    │   ├── rbc_cheques_sample.csv
    │   ├── rbc_carte_sample.csv
    │   └── rbc_sample.ofx
    ├── test_importers.py
    ├── test_categorisation.py
    └── test_cli.py
```

### Pattern 1: Beangulp CSV Importer with Declarative Column Mapping

**What:** Use beangulp's `csvbase.Importer` to declare how CSV columns map to transaction fields.
**When to use:** For each bank CSV format (RBC chequing, RBC credit card).
**Example:**
```python
# Source: Context7 /beancount/beangulp (verified)
from beangulp.importers import csvbase
from beangulp import mimetypes
from decimal import Decimal

class RBCChequesImporter(csvbase.Importer):
    """Importateur CSV pour compte-cheques RBC."""

    # RBC CSV: "Date","Description","Transaction","Debit","Credit","Total"
    date = csvbase.Date("Date", "%Y-%m-%d")
    narration = csvbase.Columns("Description", sep="; ")
    # RBC uses separate Debit/Credit columns
    # Need custom handling -- see finalize()

    def __init__(self):
        super().__init__(
            account="Actifs:Banque:RBC:Cheques",
            currency="CAD",
            flag="!"  # Flag for review
        )

    def identify(self, filepath):
        mimetype, _ = mimetypes.guess_type(filepath)
        if mimetype != "text/csv":
            return False
        with open(filepath) as fd:
            head = fd.read(256)
        # Check for RBC chequing header pattern
        return '"Date"' in head and '"Description"' in head and '"Debit"' in head

    def metadata(self, filepath, lineno, row):
        meta = super().metadata(filepath, lineno, row)
        meta['source'] = 'rbc-cheques'
        meta['categorisation'] = 'non-classe'
        return meta
```

### Pattern 2: OFX Import with ofxtools

**What:** Parse OFX/QFX files using ofxtools and convert to Beancount transactions.
**When to use:** For OFX/QFX bank downloads (preferred when available -- provides FITID for deduplication).
**Example:**
```python
# Source: ofxtools docs (verified)
import beangulp
from ofxtools.Parser import OFXTree
from beancount.core import data
from decimal import Decimal
import datetime

class RBCOfxImporter(beangulp.Importer):
    """Importateur OFX/QFX pour RBC."""

    def __init__(self, account, account_id):
        self.account_name = account
        self.account_id = account_id

    def identify(self, filepath):
        if not filepath.lower().endswith(('.ofx', '.qfx')):
            return False
        try:
            parser = OFXTree()
            parser.parse(filepath)
            ofx = parser.convert()
            # Check if this file contains our account
            for stmt in ofx.statements:
                if stmt.account.acctid == self.account_id:
                    return True
        except Exception:
            return False
        return False

    def account(self, filepath):
        return self.account_name

    def extract(self, filepath, existing):
        parser = OFXTree()
        parser.parse(filepath)
        ofx = parser.convert()

        entries = []
        for stmt in ofx.statements:
            if stmt.account.acctid != self.account_id:
                continue
            for tx in stmt.transactions:
                meta = data.new_metadata(filepath, 0)
                meta['fitid'] = tx.fitid  # Unique transaction ID from bank
                meta['source'] = 'rbc-ofx'
                meta['categorisation'] = 'non-classe'

                txn = data.Transaction(
                    meta=meta,
                    date=tx.dtposted.date(),
                    flag='!',
                    payee=getattr(tx, 'name', None),
                    narration=getattr(tx, 'memo', '') or '',
                    tags=set(),
                    links=set(),
                    postings=[
                        data.Posting(
                            account=self.account_name,
                            units=data.Amount(tx.trnamt, 'CAD'),
                            cost=None, price=None, flag=None, meta=None
                        )
                    ]
                )
                entries.append(txn)
        return entries
```

### Pattern 3: YAML Rule-Based Categorization

**What:** YAML file defines payee-regex to account mappings. Engine tries each rule in order.
**When to use:** Post-import categorization. Applied to transactions with `categorisation: non-classe` metadata.
**Example:**
```yaml
# rules/categorisation.yaml
regles:
  - nom: "Loyer bureau"
    condition:
      payee: ".*REGUS.*|.*IWGPLC.*"
    compte: "Depenses:Bureau:Loyer"
    confiance: 0.95

  - nom: "Internet"
    condition:
      payee: ".*BELL.*INTERNET.*|.*VIDEOTRON.*"
    compte: "Depenses:Bureau:Internet-Telecom"
    confiance: 0.90

  - nom: "Logiciels SaaS"
    condition:
      payee: ".*GITHUB.*|.*JETBRAINS.*|.*DIGITALOCEAN.*|.*AWS.*"
    compte: "Depenses:Bureau:Abonnements-Logiciels"
    confiance: 0.90

  - nom: "Restaurants"
    condition:
      payee: ".*RESTAURANT.*|.*CAFE.*|.*PIZZA.*"
    compte: "Depenses:Repas-Representation"
    confiance: 0.80
```

```python
# Rule engine implementation pattern
import yaml
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass
class Regle:
    nom: str
    condition_payee: Optional[re.Pattern]
    condition_narration: Optional[re.Pattern]
    condition_montant_min: Optional[Decimal]
    condition_montant_max: Optional[Decimal]
    compte: str
    confiance: float

class MoteurRegles:
    def __init__(self, chemin_regles: str):
        with open(chemin_regles) as f:
            config = yaml.safe_load(f)
        self.regles = self._charger_regles(config)

    def categoriser(self, payee: str, narration: str, montant: Decimal) -> tuple[str, float, str]:
        """Retourne (compte, confiance, nom_regle) ou None."""
        texte = f"{payee} {narration}".upper()
        for regle in self.regles:
            if regle.condition_payee and regle.condition_payee.search(texte):
                return (regle.compte, regle.confiance, regle.nom)
        return ("Depenses:Non-Classe", 0.0, "aucune-regle")
```

### Pattern 4: Beancount File Organization with Includes

**What:** A root `main.beancount` includes chart of accounts and monthly transaction files.
**When to use:** All ledger files. Enables clean separation and git diffs per month.
**Example:**
```beancount
; ledger/main.beancount
option "title" "CompteQC - Corporation Consultation IT"
option "operating_currency" "CAD"

include "comptes.beancount"
include "staging.beancount"
include "2026/01.beancount"
include "2026/02.beancount"
```

```beancount
; ledger/comptes.beancount
; Plan comptable -- Corporation de consultation IT (Quebec, CCPC)
; Mappage GIFI en metadata pour export CPA

; === ACTIFS (1000-1999) ===
2025-01-01 open Actifs:Banque:RBC:Cheques             CAD
  gifi: "1001"
2025-01-01 open Actifs:Banque:RBC:CarteCredit          CAD
  gifi: "1001"
2025-01-01 open Actifs:ComptesClients                   CAD
  gifi: "1060"

; === PASSIFS (2000-2999) ===
2025-01-01 open Passifs:CartesCredit:RBC                CAD
  gifi: "2700"
2025-01-01 open Passifs:TPS-Percue                      CAD
  gifi: "2620"
2025-01-01 open Passifs:TVQ-Percue                      CAD
  gifi: "2620"

; === CAPITAUX PROPRES (3000-3999) ===
2025-01-01 open Capital:Actions-Ordinaires               CAD
  gifi: "3500"
2025-01-01 open Capital:Benefices-Non-Repartis           CAD
  gifi: "3600"

; === REVENUS (4000-4999) ===
2025-01-01 open Revenus:Consultation                     CAD
  gifi: "8000"

; === DEPENSES (5000-8999) ===
2025-01-01 open Depenses:Bureau:Loyer                    CAD
  gifi: "8810"
2025-01-01 open Depenses:Bureau:Internet-Telecom         CAD
  gifi: "8811"
2025-01-01 open Depenses:Bureau:Abonnements-Logiciels    CAD
  gifi: "8811"
; ... etc.

; === COMPTE DE PASSAGE ===
2025-01-01 open Depenses:Non-Classe                      CAD
  gifi: "9990"
```

### Pattern 5: Git Auto-Commit After Import

**What:** After every successful import that passes bean-check, auto-commit the changed ledger files.
**When to use:** After every import operation that modifies ledger files.
**Example:**
```python
import subprocess
from pathlib import Path

def auto_commit(ledger_dir: Path, message: str) -> bool:
    """Git add + commit des fichiers .beancount modifies."""
    try:
        # Stage only .beancount files
        subprocess.run(
            ["git", "add", "*.beancount", "**/*.beancount"],
            cwd=ledger_dir, check=True, capture_output=True
        )
        # Check if there are staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=ledger_dir, capture_output=True
        )
        if result.returncode == 0:
            return False  # Nothing to commit

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=ledger_dir, check=True, capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
```

### Pattern 6: Two-Step Import Flow (Recommended)

**What:** Import extracts transactions to `staging.beancount`, user reviews, then merges to monthly files.
**When to use:** Daily import workflow.
**Flow:**
```
1. cqc importer fichier releve.csv
   -> Parse CSV/OFX
   -> Deduplicate against existing ledger
   -> Apply rule-based categorization
   -> Write new transactions to ledger/staging.beancount
   -> Run bean-check on full ledger
   -> If passes: git auto-commit
   -> Print summary (X nouvelles, Y doublons, Z non-classees)

2. cqc revue  (future phase, Phase 3)
   -> Show uncategorized transactions
   -> User categorizes manually
   -> Move from staging to monthly file

For Phase 1: single-step flow is sufficient.
Import writes directly to monthly file (e.g., 2026/02.beancount).
Uncategorized transactions use Depenses:Non-Classe with ! flag.
```

### Anti-Patterns to Avoid

- **Float arithmetic for money:** Beancount uses Decimal natively. Never convert amounts through float. `Decimal("19.99")` not `Decimal(19.99)`.
- **Single monolithic .beancount file:** Use includes and monthly files. A year of transactions in one file is hard to diff and review.
- **Silently dropping duplicate transactions:** Always log duplicates. Use beangulp's built-in deduplication with `--existing` flag. Mark duplicates as comments, never silently skip.
- **Inventing account names at import time:** The chart of accounts is defined in `comptes.beancount`. Import MUST only use accounts that exist. Uncategorized goes to `Depenses:Non-Classe`.
- **Skipping bean-check:** EVERY import must pass bean-check before git commit. If it fails, abort and report the error.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with encoding issues | Custom CSV parser | beangulp csvbase.Importer | Handles encoding, quoting, multi-line fields correctly |
| OFX/QFX parsing (SGML + XML) | Custom OFX parser | ofxtools 0.9.5 | OFXv1 is SGML (not XML), requires specialized parser. ofxtools handles both v1 and v2 |
| Transaction deduplication | Custom hash-based dedup | beangulp similar.heuristic_comparator | Date window + amount tolerance + narration comparison. Edge cases (same-day same-amount) handled |
| Double-entry validation | Custom balance checker | bean-check (beancount built-in) | Validates all invariants: balanced transactions, open accounts, correct currencies |
| SQL-like ledger queries | Custom aggregation code | beanquery | `SELECT account, sum(position) WHERE year = 2026` -- handles multi-currency, cost basis |
| CLI argument parsing | argparse | Typer (built on Click) | Type hints -> auto CLI, help text, tab completion, Rich formatting |

**Key insight:** Beancount's ecosystem has solved the hard accounting problems (balanced transactions, deduplication, multi-file includes, validation). The custom work is in the importers (RBC-specific format parsing), the categorization rules, and the French-language CLI wrapper.

## Common Pitfalls

### Pitfall 1: Beancount v3 vs v2 API Confusion
**What goes wrong:** Using `beancount.ingest` (v2) instead of `beangulp` (v3). Many online examples and tutorials still reference v2 APIs.
**Why it happens:** Beancount v3 was released mid-2024. Most blog posts and Stack Overflow answers reference v2.
**How to avoid:** Always import from `beangulp`, never from `beancount.ingest`. Use `beangulp.Importer` base class, not `beancount.ingest.importer.ImporterProtocol`.
**Warning signs:** Import errors mentioning `beancount.ingest`, `bean-extract`, or `bean-identify` (these commands no longer exist in v3).

### Pitfall 2: RBC CSV Format Inconsistency
**What goes wrong:** RBC CSV format may vary between account types (chequing vs credit card), over time, or between RBC Online Banking and RBC Express.
**Why it happens:** RBC does not publish a formal CSV specification. The format is reverse-engineered.
**How to avoid:** Build the importer's `identify()` method to check actual column headers, not just file extension. Support both known formats. Fail loudly on unrecognized headers.
**Warning signs:** Import produces transactions with wrong amounts, missing descriptions, or parse errors.

### Pitfall 3: Deduplication False Positives/Negatives
**What goes wrong:** Legitimate different transactions on the same day for the same amount get marked as duplicates (false positive), or the same transaction imported from CSV and OFX is not caught (false negative).
**Why it happens:** Heuristic deduplication compares date + amount + narration. Same-day same-amount purchases are common. CSV and OFX may have different narration text for the same transaction.
**How to avoid:** Use OFX when possible (provides FITID -- a unique bank-assigned transaction ID). For CSV, use narrow date window (1 day) with amount tolerance. For same-day same-amount, add check number or description similarity. Log all deduplication decisions.
**Warning signs:** Transaction count after import doesn't match expected count from bank statement.

### Pitfall 4: Encoding Issues in Canadian Bank Files
**What goes wrong:** French accented characters (e, a, c) in payee names get corrupted during import.
**Why it happens:** RBC CSV files may use Windows-1252 or Latin-1 encoding instead of UTF-8.
**How to avoid:** Detect encoding using file header or try UTF-8 first, fall back to Latin-1. Normalize payee names to NFD or NFC Unicode form.
**Warning signs:** Garbled characters in transaction descriptions (e.g., "CafÃ©" instead of "Cafe").

### Pitfall 5: bean-check Failures After Import
**What goes wrong:** Import produces transactions that don't pass bean-check (unbalanced, unknown accounts, wrong currencies).
**Why it happens:** Importer creates single-leg transactions (only the bank account posting, no expense leg). Or categorization assigns an account that doesn't exist in the chart of accounts.
**How to avoid:** Every transaction MUST have at least two postings. The second posting uses the categorized expense account (or `Depenses:Non-Classe` if no rule matches). Validate that the expense account exists in the chart of accounts before assigning it.
**Warning signs:** bean-check reports balance errors or unknown account errors after import.

### Pitfall 6: Git Auto-Commit on Failed Import
**What goes wrong:** A partially-written staging file gets committed to git, leaving the ledger in a broken state.
**Why it happens:** Auto-commit fires before bean-check validation.
**How to avoid:** ALWAYS run bean-check BEFORE git commit. Write to a temporary file first, validate, then move to final location and commit.
**Warning signs:** `bean-check ledger/main.beancount` fails after a git pull.

## Code Examples

### Complete RBC Chequing CSV Importer

```python
# Source: beangulp csvbase pattern (Context7 verified) + RBC format (web research)
from beangulp.importers import csvbase
from beangulp import mimetypes
from beancount.core import data
from decimal import Decimal, InvalidOperation
from os import path
import csv
import datetime

class RBCChequesImporter(csvbase.Importer):
    """Importateur CSV pour compte-cheques RBC.

    Format attendu: "Date","Description","Transaction","Debit","Credit","Total"
    Les dates sont en format YYYY-MM-DD.
    Les montants Debit sont des retraits, Credit sont des depots.
    """

    date = csvbase.Date("Date", "%Y-%m-%d")
    narration = csvbase.Columns("Description", sep="; ")

    def __init__(self):
        super().__init__(
            account="Actifs:Banque:RBC:Cheques",
            currency="CAD",
            flag="!"  # A revoir
        )

    def identify(self, filepath):
        mimetype, _ = mimetypes.guess_type(filepath)
        if mimetype != "text/csv":
            return False
        try:
            with open(filepath, encoding='utf-8') as fd:
                head = fd.read(512)
        except UnicodeDecodeError:
            with open(filepath, encoding='latin-1') as fd:
                head = fd.read(512)
        return '"Date"' in head and '"Debit"' in head and '"Credit"' in head

    def filename(self, filepath):
        return "rbc-cheques." + path.basename(filepath)

    def metadata(self, filepath, lineno, row):
        meta = super().metadata(filepath, lineno, row)
        meta['source'] = 'rbc-cheques-csv'
        return meta
```

### Beanquery Report via CLI

```python
# Source: beanquery API (Context7 verified) + Typer pattern
import typer
from rich.console import Console
from rich.table import Table
from beancount import loader
from beanquery import run_query

console = Console()

def soldes(chemin_ledger: str = "ledger/main.beancount"):
    """Affiche les soldes de tous les comptes."""
    entries, errors, options = loader.load_file(chemin_ledger)
    if errors:
        for error in errors:
            console.print(f"[red]Erreur: {error.message}[/red]")
        raise typer.Exit(code=1)

    query = "SELECT account, sum(position) WHERE account ~ 'Actifs' OR account ~ 'Passifs'"
    result_types, result_rows = run_query(entries, options, query)

    table = Table(title="Soldes des comptes")
    table.add_column("Compte", style="cyan")
    table.add_column("Solde", justify="right", style="green")

    for row in result_rows:
        table.add_row(str(row[0]), str(row[1]))

    console.print(table)
```

### GIFI Metadata on Beancount Accounts

```beancount
; Source: Beancount metadata syntax (Context7 verified) + CRA RC4088 GIFI codes
; Recommended approach: GIFI code as metadata on open directive

2025-01-01 open Actifs:Banque:RBC:Cheques              CAD
  gifi: "1001"
  description-gifi: "Encaisse et depots"

2025-01-01 open Depenses:Salaires:Brut                  CAD
  gifi: "8960"
  description-gifi: "Salaires, traitements et avantages"

2025-01-01 open Depenses:Bureau:Honoraires-Professionnels CAD
  gifi: "8860"
  description-gifi: "Honoraires professionnels"
```

This approach keeps GIFI mapping alongside the account definition, queryable via beanquery:
```sql
SELECT account, ANY_META('gifi') as gifi WHERE ANY_META('gifi') != NULL
```

## Discretion Recommendations

These are research-backed recommendations for areas marked as "Claude's Discretion":

### 1. GIFI Mapping: Use Beancount Metadata (not separate file)
**Recommendation:** Store GIFI codes as metadata on `open` directives.
**Rationale:** Keeps mapping co-located with account definition. Queryable via beanquery. No sync issues between two files. Beancount metadata is the idiomatic approach for account-level attributes.

### 2. Import Format: Support Both CSV and OFX
**Recommendation:** Build importers for both. Prefer OFX when available.
**Rationale:** OFX provides FITID (unique bank transaction ID) which makes deduplication reliable. CSV is always available as fallback. RBC supports both formats. Two importers is not much more work than one given the beangulp framework.

### 3. Deduplication Strategy: Layered Approach
**Recommendation:**
- OFX: Use FITID (bank transaction ID) stored as Beancount metadata. Exact match = definite duplicate.
- CSV: Use beangulp's `similar.heuristic_comparator` with 1-day date window and 0.01 CAD amount tolerance.
- Cross-format: When importing CSV after OFX (or vice versa), compare date + amount + first 20 chars of narration.
- Always log decisions: mark duplicates as comments in output, never silently skip.

### 4. Rule Format: YAML
**Recommendation:** YAML file with list of rules, each having condition (payee regex) and target account.
**Rationale:** Human-readable, easy to edit, supports comments. Pydantic validates on load. YAML is widely used in the Beancount ecosystem (beanhub-import uses a similar pattern).

### 5. Auto-Suggest Rules After Manual Correction: Deferred to Phase 3
**Recommendation:** Do not implement auto-suggestion in Phase 1. When user manually categorizes a transaction, just record it. Phase 3's review workflow will add rule suggestion (after N identical corrections, prompt to create a rule).
**Rationale:** Phase 1 focuses on getting the pipeline working. Rule suggestions require tracking correction patterns, which is a Phase 3 concern.

### 6. CLI Report Format: Rich Tables
**Recommendation:** Use Rich tables for CLI output. Structured, colored, aligned columns.
**Rationale:** Rich is already a Typer dependency. Tables are clean for account balances and transaction lists. Supports export to plain text if piped.

### 7. Import Flow: Single-Step with Review Tags
**Recommendation:** For Phase 1, import directly to monthly ledger files (no staging file).
- All imported transactions get `!` flag (needs review).
- Categorized transactions get `categorisation: "regle"` metadata.
- Uncategorized get `categorisation: "non-classe"` and post to `Depenses:Non-Classe`.
- Run bean-check, then git commit.
- User can later change `!` to `*` after review.

**Rationale:** A staging file adds complexity without value in Phase 1 (no approval workflow yet). The `!` flag in Beancount is designed exactly for "needs review" transactions. Phase 3 adds the full staging/approval workflow.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| beancount.ingest | beangulp (separate package) | Beancount 3.0.0 (mid-2024) | All importers must use beangulp.Importer base class. bean-extract/bean-identify removed. |
| beancount.query | beanquery (separate package) | Beancount 3.0.0 (mid-2024) | Import from beanquery, not beancount.query. |
| Beancount v2 on PyPI | Beancount 3.2.0 | 2025 | v3 is the current recommended version. v2 still installable but no longer maintained. |
| ofxparse | ofxtools | Ongoing | ofxtools is actively maintained (0.9.5). ofxparse is stale. |
| Poetry / pip-tools | uv | 2024-2025 | uv is 10-100x faster, handles Python versions. De facto standard for new projects. |

**Deprecated/outdated:**
- `beancount.ingest`: Removed in v3. Use `beangulp`.
- `bean-extract`, `bean-identify`, `bean-file`: Removed in v3. Use beangulp CLI or custom Python scripts.
- `beancount.query.query`: Removed from core. Use `beanquery` package.
- `ofxparse`: Stale maintenance since ~2022. Use `ofxtools`.

## Open Questions

1. **RBC CSV exact format for business accounts**
   - What we know: Personal banking CSV uses "Date","Description","Transaction","Debit","Credit","Total" with YYYY-MM-DD dates. Credit card may differ.
   - What's unclear: Business account CSV may have different column headers. Credit card CSV format may use "Transaction Date","Posting Date" or different columns.
   - Recommendation: Build importers with flexible header detection. Test with actual downloaded files. The identify() method should check actual headers, not assume. Plan to update when real sample files are available.

2. **RBC OFX account IDs**
   - What we know: OFX files contain account IDs (acctid). The importer needs to match against the correct account.
   - What's unclear: What format RBC uses for account IDs in OFX (full account number? masked? branch+account?).
   - Recommendation: Parse a sample OFX file to determine the format. Make account ID configurable in the importer.

3. **Fava compatibility with French account names**
   - What we know: Fava 1.30.12 is compatible with Beancount v3. Account names can use any Unicode characters.
   - What's unclear: Whether Fava's navigation, search, and reports handle accented characters and colon-separated French names without issues.
   - Recommendation: LOW risk. Test early with the chart of accounts. Accented characters in Beancount account names are well-supported per the spec (alphanumeric + dash + colon).
   - **Update:** Beancount account names must start with a capital letter and use only letters, numbers, and dashes between colons. Accented uppercase letters (e.g., E, A) should work but test to confirm. Safe alternative: use unaccented names (Depenses, not Depenses).

4. **beangulp csvbase handling of separate Debit/Credit columns**
   - What we know: csvbase.Importer has an `amount` class attribute for a single amount column. RBC uses separate Debit and Credit columns.
   - What's unclear: Whether csvbase supports mapping two columns to a single amount, or if custom extract() override is needed.
   - Recommendation: May need to override `extract()` to manually handle Debit/Credit merge. Alternative: pre-process CSV to merge columns before passing to csvbase. Test with actual beangulp 0.2.0.

## Sources

### Primary (HIGH confidence)
- [Beancount 3.2.0 on PyPI](https://pypi.org/project/beancount/) -- version verified 2026-02-19
- [beangulp 0.2.0 on PyPI](https://pypi.org/project/beangulp/) -- version verified 2026-02-19
- [beanquery 0.2.0 on PyPI](https://pypi.org/project/beanquery/) -- version verified 2026-02-19
- [fava 1.30.12 on PyPI](https://pypi.org/project/fava/) -- version verified 2026-02-19
- [ofxtools 0.9.5 on PyPI](https://pypi.org/project/ofxtools/) -- version verified 2026-02-19
- [Typer 0.24.0 on PyPI](https://pypi.org/project/typer/) -- version verified 2026-02-19
- Context7 `/websites/beancount_github_io_index` -- Beancount syntax, metadata, file organization, plugins
- Context7 `/beancount/beangulp` -- csvbase.Importer, deduplication, testing, CLI commands
- Context7 `/fastapi/typer` -- subcommands, callbacks, app structure
- [CRA RC4088 GIFI codes](https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/rc4088/general-index-financial-information-gifi.html) -- GIFI code ranges and categories
- [ofxtools parser documentation](https://ofxtools.readthedocs.io/en/latest/parser.html) -- OFX parsing API

### Secondary (MEDIUM confidence)
- [Beancount v3 migration guide](https://beancount.io/blog/2025/06/06/whats-new-in-beancount-v3) -- v3 breaking changes and new architecture
- [beancount-reds-importers](https://github.com/redstreet/beancount_reds_importers) -- alternative importer framework with OFX support
- [Fava v3 compatibility issue #1831](https://github.com/beancount/fava/issues/1831) -- Fava/Beancount v3 compatibility tracking
- [RBC transaction extraction gist](https://gist.github.com/renoirb/f865666be869f836ec567f22b3719827) -- RBC CSV format reverse-engineering

### Tertiary (LOW confidence)
- RBC CSV column format for business accounts -- based on personal banking format extrapolation and third-party tool documentation. Needs validation with real sample files.
- RBC credit card CSV format -- inferred from third-party converter tools. May differ from actual RBC export.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all library versions verified on PyPI, APIs verified via Context7
- Architecture: HIGH -- patterns verified against beangulp and Beancount official docs
- RBC import formats: MEDIUM -- personal banking CSV format documented, business format inferred
- Pitfalls: HIGH -- based on documented community experience and Beancount v2->v3 migration issues
- GIFI mapping: HIGH -- CRA RC4088 is the official source

**Research date:** 2026-02-19
**Valid until:** 2026-04-19 (stable domain, libraries change slowly)
