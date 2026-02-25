# CompteQC CLI Reference

## Import

```bash
# Import any RBC file (auto-detects cheques vs carte)
uv run cqc importer fichier <path-to-csv>

# Force account type
uv run cqc importer fichier <path-to-csv> --compte CHEQUES
uv run cqc importer fichier <path-to-csv> --compte CARTE

# Import a PERSONAL bank CSV (everything → Passifs:Pret-Actionnaire)
# Skips categorization pipeline entirely (no rules, ML, or LLM)
uv run cqc importer fichier <path-to-csv> --source-type personal
uv run cqc importer fichier <path-to-csv> -s personal

# Explicitly mark as corporate (this is the default)
uv run cqc importer fichier <path-to-csv> --source-type corporate
```

### Source type explained

| Flag | Behavior |
|------|----------|
| `--source-type corporate` (default) | Normal pipeline: rules → ML → LLM → CAPEX detection → pending/auto-approve |
| `--source-type personal` | Everything → `Passifs:Pret-Actionnaire`, flag `*` (auto-approved), no pipeline |

Use `--source-type personal` when importing a CSV from your **personal bank account**. Every transaction from a personal account is a shareholder loan movement by definition — the categorization pipeline has no business running on it.

## Review pending transactions

```bash
# List all pending transactions
uv run cqc reviser liste

# Approve one transaction by index
uv run cqc reviser approuver <index>

# Approve multiple
uv run cqc reviser approuver 0 1 2 3

# Reject (delete) a pending transaction
uv run cqc reviser rejeter <index>

# Recategorize to a different account
uv run cqc reviser recategoriser <index> <account>
# Example: uv run cqc reviser recategoriser 3 Depenses:Bureau:Loyer

# View recently auto-approved transactions (>95% confidence)
uv run cqc reviser journal
```

## Reports

```bash
# Account balances (all or filtered)
uv run cqc soldes
uv run cqc soldes --compte Depenses

# Trial balance
uv run cqc rapport balance

# Income statement (P&L)
uv run cqc rapport resultats

# Balance sheet
uv run cqc rapport bilan
```

## Payroll

```bash
uv run cqc paie --help
```

## Invoicing

```bash
uv run cqc facture --help
```

## Receipts

```bash
uv run cqc recu --help
```

## CPA Export

```bash
uv run cqc cpa --help
```

## Filing deadlines

```bash
uv run cqc echeances --help
```

## Global options

```bash
# Custom ledger path
uv run cqc --ledger path/to/main.beancount <command>

# Custom rules file
uv run cqc --regles path/to/rules.yaml <command>

# Version
uv run cqc --version
```
