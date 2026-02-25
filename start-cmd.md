# Start Fava UI
uv run fava ledger/main.beancount --port 5001

# Run payroll calculation (dry-run to preview)
uv run compteqc paie lancer 5000 --dry-run

# Run payroll calculation (write to ledger)
uv run compteqc paie lancer 5000

# Run payroll with shareholder loan offset
uv run compteqc paie lancer 5000 --salary-offset 500

# Run payroll for specific period
uv run compteqc paie lancer 5000 --periode 1