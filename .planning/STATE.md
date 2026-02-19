# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** Every dollar that flows through the corporation is correctly categorized, traceable to source documents, and ready for CPA review -- without manual data entry.
**Current focus:** Phase 5: Reporting, CPA Export and Document Management

## Current Position

Phase: 5 of 5 (Reporting, CPA Export and Document Management)
Plan: 5 of 5 in current phase (ALL COMPLETE)
Status: Phase 05 Complete
Last activity: 2026-02-19 -- Completed 05-03 (CPA Package Orchestrator)

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 22
- Average duration: 4.9 min
- Total execution time: 1.75 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | 19 min | 6.3 min |
| 02 | 5 | 23 min | 4.6 min |
| 03 | 3 | 17 min | 5.7 min |
| 04 | 5 | 26 min | 5.2 min |

**Recent Trend:**
- Last 5 plans: 05-05 (4 min), 05-04 (5 min), 05-02 (5 min), 05-01 (7 min), 05-03 (6 min)
- Trend: stable

*Updated after each plan completion*
| Phase 05 P03 | 6 | 2 tasks | 17 files |
| Phase 05 P02 | 5 | 2 tasks | 10 files |
| Phase 05 P01 | 7 | 2 tasks | 12 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Research]: Beancount v3 selected as ledger engine (Python-native plugins, Decimal math, 10-year track record)
- [Research]: Tiered categorization pipeline: rules first (60-70%), ML second (20-25%), LLM last (5-10%)
- [Research]: FastAPI + HTMX + Fava for web layer; no JS build toolchain
- [01-01]: Beancount v3 name_* options must be in every included file, not just main.beancount
- [01-01]: Float rejection via Pydantic BeforeValidator (strict mode blocks string date coercion)
- [01-02]: Credit card sign convention: CSV positive = purchase, maps to negative on carte account posting
- [01-02]: Dedup strategy: FITID for OFX, date+montant+narration[:20] for CSV
- [01-02]: Empty categorisation rules file -- build rules incrementally from real imports
- [01-02]: appliquer_categorisation creates new Transaction instances (immutable transformation)
- [01-03]: Monthly beancount files require name_* options (same Beancount v3 requirement as comptes.beancount)
- [01-03]: Reports compute balances directly from Transaction postings instead of beanquery
- [01-03]: Bilan includes resultat net under capitaux propres for accounting equation verification
- [02-01]: Tuple instead of list for tax brackets in TauxAnnuels (immutability)
- [02-01]: Per-deduction-type liability sub-accounts for trivial YTD queries
- [02-01]: QPP supp1 has NO exemption deduction (differs from QPP base)
- [02-03]: Plug value rounding: avant_taxes = total - tps - tvq ensures exact sum
- [02-03]: Pydantic BaseModel for YAML tax rule validation (not raw dicts)
- [02-03]: Reconciliation flags TPS-only transactions for human review rather than auto-correcting
- [02-04]: CCA transactions use '!' flag for discretionary CPA review (not auto-posted)
- [02-04]: s.15(2) inclusion date from fiscal year-end + 1 year (not loan date + 1 year)
- [02-04]: FIFO repayment allocation for per-advance s.15(2) deadline tracking
- [02-04]: Circularity detection: 20% tolerance, 30-day window per s.15(2.6)
- [02-02]: Salary offset Pret-Actionnaire uses credit posting (not debit) for correct transaction balancing
- [02-02]: FSS estimated by annualizing from (YTD + current) mass salariale
- [03-01]: Direct sklearn pipeline instead of smart_importer.EntryPredictor (too coupled to beangulp)
- [03-01]: SVC(probability=True) for Platt scaling confidence scores
- [03-01]: ClassificateurLLM as runtime_checkable Protocol for loose coupling with 03-02
- [03-01]: CAPEX keyword-based CCA class suggestion (class 50 computers, 8 furniture, 10 vehicles, 12 software)
- [03-02]: Anthropic messages.parse() with Pydantic output_format for constrained structured output
- [03-02]: beancount.parser.parse_string instead of loader.load_file for pending (avoids Open directive validation)
- [03-02]: Lazy Anthropic client initialization to avoid import-time API key requirement
- [03-02]: SHA-256 prompt hash (16 chars) in JSONL log for drift detection without storing full prompts
- [02-05]: Reuse paie/ytd.py entry-reading pattern for shareholder loan bridge (isinstance + year + account match)
- [02-05]: No tag filtering for pret actionnaire (all transactions touching the account are relevant)
- [03-03]: CLI tests must pass --ledger/--regles args (Typer callback always resets globals from defaults)
- [03-03]: Beancount parser sorts entries by date when re-parsing pending.beancount
- [04-01]: Beancount v3 parse_string is at beancount.parser.parser.parse_string (not beancount.parser)
- [04-01]: Tool response cap at 50 items with tronque flag for pagination
- [04-01]: French field names in all MCP tool responses
- [04-01]: AppContext dataclass with reload() for in-memory ledger refresh after mutations
- [04-02]: charger_regles() function instead of ConfigRegles.charger() (Pydantic model has no classmethod)
- [04-02]: Composite key date|payee|narration[:20] for pending transaction identification
- [04-02]: Auto-approve threshold: confiance >= 0.95, revue_obligatoire=False, abs(montant) <= 2000
- [04-02]: Unified payroll confirmation with raison field: nouveau_montant, gros_montant, nouveau_et_gros_montant
- [04-03]: lister_pending supports both meta key conventions (confiance/source_ia and confidence/ai-source)
- [04-03]: niveau_confiance and est_gros_montant as module-level helpers for testability
- [04-03]: Standard HTML form POST + redirect for Fava extension (no HTMX)
- [04-04]: niveau_alerte_s152 as module-level helper for testability (same pattern as 04-03)
- [04-04]: CCA extension loads actifs.yaml from ledger directory by default, falls back to empty registre
- [04-04]: TaxesQCExtension supports config string for frequence (annuel/trimestriel)
- [04-05]: Try-import pattern for Phase 5 modules (compteqc.echeances.calendrier, compteqc.documents.upload)
- [04-05]: RecusExtension saves files to documents/ dir even without Phase 5 extraction
- [04-05]: 4 urgency CSS classes: alerte-critique (red), alerte-urgent (orange), alerte-normal (yellow), alerte-info (blue)
- [05-05]: Weekend adjustment: Saturday/Sunday deadlines pushed to Monday (standard CRA rule)
- [05-05]: Urgency thresholds: critique <= 7d, urgent <= 14d, normal <= 30d, info <= 90d
- [05-05]: CLI footer shows only alerts within 30 days (per discretion recommendation)
- [05-05]: Payroll remittance assumes regular remitter (15th of following month)
- [05-04]: Claude Vision tool_use for structured extraction (not messages.parse -- tool_use gives cleaner JSON)
- [05-04]: Amount (60%) + date (40%) weighted scoring for receipt matching
- [05-04]: Image resize to 1568px max via Pillow before sending to Claude Vision
- [05-04]: Pillow added as project dependency for image processing
- [05-02]: WeasyPrint for HTML-to-PDF invoice generation (Jinja2 template + CSS)
- [05-02]: YAML-based invoice registry (low volume, no database needed)
- [05-02]: FAC-YYYY-NNN sequential numbering (Quebec legal requirement for gapless invoices)
- [05-02]: Lazy WeasyPrint import to avoid system dependency crash at module load
- [05-02]: PDF test skipped when pango/gobject system deps unavailable
- [05-01]: Used calculer_soldes from mcp/services.py (plan referenced nonexistent ledger/rapports.py)
- [05-01]: GIFI validation checks beancount equation sum (all accounts = 0) rather than transformed form
- [05-01]: BaseReport ABC pattern: subclasses implement extract_data/csv_headers/csv_rows
- [05-01]: PDF tests use weasyprint_available fixture for graceful skip when system libs unavailable
- [05-03]: sum() with Decimal('0') start value to avoid int return on empty dicts in bilan/etat_resultats
- [05-03]: Year-end checklist uses warn-but-allow: only equation imbalance (ERROR) blocks CPA package
- [05-03]: CPA package ZIP organizes into rapports/ (statements), annexes/ (schedules), gifi/ (export CSVs)

### Pending Todos

None yet.

### Blockers/Concerns

- smart_importer + Beancount v3 compatibility: resolved by bypassing EntryPredictor, using direct sklearn
- CPA export format preference unknown (consult CPA before Phase 5)
- Quebec Law 25 compliance for sending financial data to cloud LLM (affects Phase 3)

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 05-03-PLAN.md
Resume file: .planning/phases/05-reporting-cpa-export-and-document-management/05-03-SUMMARY.md
