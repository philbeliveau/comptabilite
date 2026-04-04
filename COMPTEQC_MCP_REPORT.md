# `compteqc` MCP Verification Report

Date: 2026-04-04
Workspace: `/Users/philippebeliveau/Desktop/Notebook/comptabilite`

## Summary

- MCP status: reachable from Codex
- Ledger status: loaded successfully through live read-only queries
- Mutations performed: none

## Startup Check

Command used:

```bash
uv run python -m compteqc.mcp --help
```

Result:

- First attempt in sandbox failed with:

```text
error: failed to open file `/Users/philippebeliveau/.cache/uv/sdists-v9/.git`: Operation not permitted (os error 1)
```

- Rerun with escalation succeeded with exit code `0`

Conclusion:

- The startup issue was a sandbox access restriction in the `uv` cache, not an application failure.

## Available MCP Tools

The following `compteqc` MCP tools were available to Codex in this project:

- `ap_add`
- `ap_aging`
- `ap_list`
- `ap_pay`
- `apar_summary`
- `approuver_lot`
- `ar_aging`
- `balance_verification`
- `bilan`
- `calculer_paie_tool`
- `etat_dpa`
- `etat_pret_actionnaire`
- `etat_resultats`
- `lancer_paie`
- `lister_pending_tool`
- `proposer_categorie`
- `rejeter`
- `soldes_comptes`
- `sommaire_tps_tvq`

Note:

- `list_mcp_resources(server="compteqc")` returned no resources. The server is tool-based rather than resource-based.

## Read-Only Checks Run

### 1. Account Balances

Tool:

- `soldes_comptes`

Status:

- Worked

Highlights:

- `nb_comptes = 19`
- `tronque = false`
- `Actifs:Banque:RBC:Cheques = 116.92`
- `Passifs:CartesCredit:RBC = 4,335.49`
- `Passifs:Pret-Actionnaire = -7,628.40`
- `Passifs:Salaires-A-Payer = -3,191.02`
- `Revenus:Autres = -1,657.70`

### 2. Trial Balance

Tool:

- `balance_verification`

Status:

- Worked

Result:

- `total_debits = 12,566.68`
- `total_credits = 12,566.68`
- `equilibre = true`

### 3. Income Statement

Tool:

- `etat_resultats`

Status:

- Worked

Result:

- `total_revenus = 1,657.70`
- `total_depenses = 8,024.71`
- `resultat_net = -6,367.01`
- `tronque = false`

### 4. GST/QST Summary

Tool:

- `sommaire_tps_tvq`

Status:

- Worked

Result:

- `periode = 2026-01-01 a 2026-12-31`
- `tps_percue = 0.00`
- `tvq_percue = 0.00`
- `tps_payee = 0.00`
- `tvq_payee = 0.00`
- `remise_nette_tps = 0.00`
- `remise_nette_tvq = 0.00`
- `nb_transactions = 0`

## Errors And Likely Cause

Observed error:

```text
error: failed to open file `/Users/philippebeliveau/.cache/uv/sdists-v9/.git`: Operation not permitted (os error 1)
```

Likely cause:

- Codex sandbox blocked `uv` from accessing its cache under the user home directory.

Impact:

- Prevented a direct non-escalated startup check only.
- Did not prevent MCP usage once the check was rerun with escalation.

## Repo-Control MCP Access Parity

Assessment:

- Codex now has the same practical `compteqc` repo-control MCP access as Claude for this project.

Basis:

- The repo documentation specifies the same server entrypoint:

```bash
uv run python -m compteqc.mcp
```

- Codex was able to call the live `compteqc` MCP tools successfully against this repository.

## Final Conclusion

- `compteqc` MCP started successfully when run outside the sandbox restriction.
- The ledger loaded successfully through live read-only queries.
- The requested read-only checks all worked.
- No ledger files were modified.
