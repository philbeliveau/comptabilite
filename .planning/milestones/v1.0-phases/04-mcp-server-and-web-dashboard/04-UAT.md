---
status: diagnosed
phase: 04-mcp-server-and-web-dashboard
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md, 04-05-SUMMARY.md]
started: 2026-02-19T15:00:00Z
updated: 2026-02-19T16:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. All Phase 4 tests pass
expected: Running `uv run pytest` completes with all Phase 4 tests passing (0 failures).
result: pass
notes: 98 Phase 4 tests pass (test_mcp_server, test_mcp_mutations, test_fava_ext, test_fava_quebec, test_fava_gap_closure). 8 pre-existing failures in Phase 1/3 CLI tests (test_cli.py, test_categorisation.py) unrelated to Phase 4.

### 2. MCP server starts via stdio
expected: Running `uv run python -m compteqc.mcp` starts without errors.
result: pass
notes: Server starts, creates CompteQC MCP instance. Blocks on stdio as expected.

### 3. Fava starts and shows 8 extensions
expected: Running `uv run fava ledger/main.beancount` starts the web server with 8 extension links in the sidebar.
result: pass
notes: Fava starts on configured port. Redirects to income_statement. All 8 extensions registered. 5 return HTTP 200, 3 return HTTP 500 (tested individually below).

### 4. Approval queue page loads
expected: Clicking "Approbation" shows the pending transaction approval page with confidence badges and batch selection.
result: issue
reported: "HTTP 500 - TypeError: url_for() got multiple values for argument 'endpoint'. The template passes endpoint='approuver' to Flask url_for which conflicts with Flask's own 'endpoint' keyword argument."
severity: blocker

### 5. Payroll dashboard loads
expected: Clicking "Paie QC" shows a payroll dashboard with 7 Quebec deductions plus income tax, YTD amounts and max-reached indicators.
result: pass
notes: HTTP 200. Page renders successfully.

### 6. GST/QST tracker loads
expected: Clicking "Taxes QC" shows GST/QST by filing period with TPS, TVQ, CTI, RTI, and net remittance.
result: pass
notes: HTTP 200. Page renders successfully.

### 7. CCA schedule loads
expected: Clicking "DPA QC" shows a CCA table with asset classes and FNACC columns.
result: pass
notes: HTTP 200. Page renders successfully.

### 8. Shareholder loan with alerts loads
expected: Clicking "Pret Actionnaire" shows shareholder loan balance with s.15(2) countdown and color-coded alerts.
result: pass
notes: HTTP 200. Page renders with 5 alert-related elements.

### 9. Deadlines extension loads
expected: Clicking "Echeances" shows a placeholder message or deadline alert banners.
result: issue
reported: "HTTP 500 - jinja2.exceptions.TemplateNotFound: compteqc.fava_ext.echeances. Template uses {% from 'compteqc.fava_ext.echeances' import couleur_urgence %} but Jinja2 cannot import from Python modules — this is not a valid Jinja2 import."
severity: blocker

### 10. Receipt upload page loads
expected: Clicking "Recus" shows a drag-and-drop upload zone.
result: issue
reported: "HTTP 500 - TypeError: url_for() got multiple values for argument 'endpoint'. Same bug as Approbation — template passes endpoint='upload' to Flask url_for which conflicts with Flask's own 'endpoint' kwarg."
severity: blocker

## Summary

total: 10
passed: 7
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "Approbation extension page loads with approval queue"
  status: failed
  reason: "HTTP 500 - TypeError: url_for() got multiple values for argument 'endpoint'. Template passes endpoint='approuver' to url_for('extension_endpoint', ..., endpoint='approuver') but Flask url_for uses 'endpoint' as its first positional arg."
  severity: blocker
  test: 4
  root_cause: "Fava's Flask route uses <endpoint> as URL variable which conflicts with flask.url_for()'s first positional parameter name. Template originally used url_for() which triggered the TypeError."
  artifacts:
    - path: "src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html"
      issue: "url_for('extension_endpoint', endpoint='approuver') conflicts with Flask's url_for signature"
  missing:
    - "Replace url_for() calls with hardcoded URL string interpolation using g.beancount_file_slug and extension.name"
  debug_session: ""
  fix_status: "Already fixed in working tree — template now uses hardcoded URL strings instead of url_for()"

- truth: "Echeances extension page loads with deadline alerts or placeholder"
  status: failed
  reason: "HTTP 500 - jinja2.exceptions.TemplateNotFound: compteqc.fava_ext.echeances. Template uses {% from 'compteqc.fava_ext.echeances' import couleur_urgence %} which is not valid Jinja2 syntax for importing Python functions."
  severity: blocker
  test: 9
  root_cause: "Jinja2 {% from %} imports macros from template files, not Python modules. couleur_urgence is a Python function that cannot be imported this way."
  artifacts:
    - path: "src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html"
      issue: "{% from 'compteqc.fava_ext.echeances' import couleur_urgence %} is invalid Jinja2"
    - path: "src/compteqc/fava_ext/echeances/__init__.py"
      issue: "couleur_urgence() not pre-applied to alert data before passing to template"
  missing:
    - "Remove invalid {% from %} import"
    - "Pre-compute classe_css in Python via couleur_urgence() before passing to template"
    - "Replace extension.module.couleur_urgence() call with alerte.classe_css in template"
  debug_session: ""
  fix_status: "Already fixed in working tree — couleur_urgence pre-computed in __init__.py, template uses alerte.classe_css"

- truth: "Recus extension page loads with drag-and-drop upload zone"
  status: failed
  reason: "HTTP 500 - TypeError: url_for() got multiple values for argument 'endpoint'. Same url_for endpoint conflict as Approbation extension."
  severity: blocker
  test: 10
  root_cause: "Same Fava url_for/endpoint naming conflict as Approbation. Template originally used url_for() with endpoint='upload'."
  artifacts:
    - path: "src/compteqc/fava_ext/recus/templates/RecusExtension.html"
      issue: "url_for('extension_endpoint', endpoint='upload') conflicts with Flask's url_for signature"
  missing:
    - "Replace url_for() calls with hardcoded URL string interpolation"
  debug_session: ""
  fix_status: "Already fixed in working tree — template now uses hardcoded URL strings"
