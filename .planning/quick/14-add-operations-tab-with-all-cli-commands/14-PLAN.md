---
phase: quick-14
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/operations/__init__.py
  - src/compteqc/fava_ext/operations/templates/OperationsExtension.html
  - ledger/main.beancount
autonomous: true
requirements: [QUICK-14]

must_haves:
  truths:
    - "Operations tab appears in Fava sidebar"
    - "All CLI operations are organized into categorized cards"
    - "Each card/button has a tooltip description on hover"
    - "Import card has a file upload form with account type and source type selectors"
    - "Links to existing tabs navigate correctly"
    - "Retrain ML button triggers a POST and shows result"
    - "Review Journal shows auto-approved transactions (>95% confidence)"
  artifacts:
    - path: "src/compteqc/fava_ext/operations/__init__.py"
      provides: "Fava extension class with import and retrain endpoints"
      exports: ["OperationsExtension"]
    - path: "src/compteqc/fava_ext/operations/templates/OperationsExtension.html"
      provides: "Command center UI with categorized operation cards"
      min_lines: 100
  key_links:
    - from: "src/compteqc/fava_ext/operations/__init__.py"
      to: "compteqc.cli.importer"
      via: "import logic reuse for file import endpoint"
      pattern: "_detecter_importateurs|_importer_avec"
    - from: "src/compteqc/fava_ext/operations/__init__.py"
      to: "compteqc.categorisation.ml"
      via: "retrain endpoint"
      pattern: "PredicteurML"
    - from: "ledger/main.beancount"
      to: "src/compteqc/fava_ext/operations/__init__.py"
      via: "fava-extension registration"
      pattern: "compteqc.fava_ext.operations"
---

<objective>
Create a new "Operations" Fava extension tab that serves as a command center, exposing all CompteQC CLI operations through the web UI. Each operation is organized into categorized cards with tooltip descriptions. The two active operations (file import and ML retrain) have working POST endpoints; all other operations link to their existing tabs or Fava built-in pages.

Purpose: Give users a single launchpad to discover and access all CompteQC capabilities without needing the CLI.
Output: Working Operations tab registered in Fava with import form, retrain button, and navigation links.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/compteqc/fava_ext/approbation/__init__.py (extension_endpoint pattern, POST handling)
@src/compteqc/fava_ext/recus/__init__.py (file upload endpoint pattern)
@src/compteqc/fava_ext/tableau_bord/__init__.py (data-driven page pattern)
@src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html (template structure, cqc-* CSS classes)
@src/compteqc/fava_ext/recus/templates/RecusExtension.html (upload form pattern)
@src/compteqc/cli/importer.py (import logic to reuse)
@src/compteqc/cli/app.py (retrain command logic, all CLI commands)
@ledger/main.beancount (extension registration pattern)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Operations extension Python class with import and retrain endpoints</name>
  <files>src/compteqc/fava_ext/operations/__init__.py</files>
  <action>
Create `OperationsExtension(FavaExtensionBase)` with `report_title = "Operations"`.

Three endpoints:

1. `@extension_endpoint("import", ["POST"])` -- File import endpoint:
   - Accepts multipart form with `fichier` (file), `compte` (AUTO/CHEQUES/CARTE), `source_type` (corporate/personal)
   - Saves uploaded file to a temp location
   - Reuses import logic from `compteqc.cli.importer`: call `_detecter_importateurs`, then `_importer_avec` for each importateur
   - Uses `self.ledger.beancount_file_path` to get `chemin_main`, derives `chemin_regles` from sibling `../rules/categorisation.yaml`
   - Loads entries via `beancount.loader.load_file` for deduplication
   - Returns JSON: `{"status": "ok", "importees": N, "regles": N, "ia_auto": N, "pending": N}` on success
   - Returns JSON: `{"status": "error", "message": "..."}` on failure
   - After import, calls `self.ledger.load_file()` to refresh

2. `@extension_endpoint("retrain", ["POST"])` -- ML retrain endpoint:
   - Reuse logic from `compteqc.cli.app.retrain`: load entries, extract training data, train PredicteurML, save model
   - Returns JSON: `{"status": "ok", "transactions": N, "comptes": N}` on success
   - Returns JSON: `{"status": "error", "message": "..."}` or `{"status": "warning", "message": "insufficient data"}` as appropriate

3. `@extension_endpoint("journal", ["GET"])` -- Review journal endpoint:
   - Returns JSON list of auto-approved transactions (confidence >= 0.95, not #pending)
   - Each entry: `{"date", "payee", "narration", "montant", "compte", "confiance", "source"}`
   - Scans `self.ledger.all_entries` for Transaction entries with `meta.get("confiance")` >= "0.95" and `meta.get("categorisation")` in ("ml", "llm")
   - Limit to 50 most recent

Also add a helper method `_tab_urls()` that returns a dict mapping tab names to their Fava extension URLs:
- Uses `flask.g.beancount_file_slug` to build URLs like `/{slug}/extension/ApprobationExtension/`
- Maps: approbation, paie_qc, recus, export_cpa, echeances, taxes_qc, dpa_qc, pret_actionnaire
- Also includes Fava built-in report URLs: trial_balance, income_statement, balance_sheet

This method is called from the template to generate correct links.
  </action>
  <verify>
`python -c "from compteqc.fava_ext.operations import OperationsExtension; print('OK')"` succeeds.
  </verify>
  <done>OperationsExtension class exists with import, retrain, and journal endpoints, all returning JSON.</done>
</task>

<task type="auto">
  <name>Task 2: Create Operations template with categorized command cards and register extension</name>
  <files>
    src/compteqc/fava_ext/operations/templates/OperationsExtension.html
    ledger/main.beancount
  </files>
  <action>
**Template** (`OperationsExtension.html`):

Use `{% set page_title = "Operations" %}` and `{% block content %}`.

Page header: `cqc-page-header` with title "Centre d'operations" and subtitle "Toutes les commandes CompteQC".

Layout: CSS grid of `cqc-card` elements organized by category. Use a 3-column grid on desktop, 1-column on mobile (same pattern as dashboard charts but 3 cols).

**Category cards (each is a `cqc-card`):**

1. **Import** (icon: upload arrow or document icon via HTML entity)
   - Tooltip: "Importer un fichier bancaire CSV/OFX dans le grand livre"
   - Contains a form (`method="POST"`, `enctype="multipart/form-data"`, action pointing to the import endpoint)
   - File input (`accept=".csv,.ofx,.qfx"`)
   - Select for `compte`: AUTO (default), CHEQUES, CARTE
   - Select for `source_type`: Corporatif (corporate), Personnel (personal)
   - Submit button with `cqc-btn cqc-btn-primary`
   - Show result div (hidden by default) for import feedback
   - Use XHR submission (like recus pattern) to show progress/result without page reload

2. **Revision** (icon: clipboard/checkmark)
   - Tooltip: "Reviser, approuver ou rejeter les transactions en attente"
   - Link button to Approbation tab: "File d'approbation" with tooltip "Voir les transactions #pending a approuver/rejeter"
   - "Journal auto-approuve" button that fetches the `/journal` endpoint and displays results in a collapsible table below (date, payee, montant, confiance, compte)

3. **Rapports** (icon: chart/report)
   - Tooltip: "Rapports financiers et soldes comptables"
   - Link buttons (each `cqc-btn cqc-btn-outline`):
     - "Soldes" -> Fava trial_balance, title="Soldes de tous les comptes"
     - "Balance de verification" -> Fava trial_balance, title="Balance de verification (debits = credits)"
     - "Etat des resultats" -> Fava income_statement, title="Revenus et depenses de l'exercice"
     - "Bilan" -> Fava balance_sheet, title="Actifs, passifs et capitaux propres"

4. **Paie** (icon: money/salary)
   - Tooltip: "Calculer et comptabiliser la paie"
   - Link button to PaieQC tab: "Calculateur de paie", title="Lancer le calcul de paie avec deductions Quebec"

5. **Factures** (icon: receipt/invoice)
   - Tooltip: "Creer, lister et gerer les factures clients"
   - Note: "Disponible via CLI: cqc facture creer/lister/voir/pdf/envoyer/payer/relances"
   - Styled as `cqc-text-muted` informational text (these are interactive prompts, not suitable for web yet)

6. **Recus** (icon: camera/document)
   - Tooltip: "Telecharger et lier des recus aux transactions"
   - Link button to Recus tab: "Telecharger des recus", title="Glisser-deposer des recus PDF/JPEG pour extraction IA"

7. **Export CPA** (icon: briefcase/export)
   - Tooltip: "Generer le package de fin d'annee pour le comptable"
   - Link button to ExportCPA tab: "Exporter pour CPA", title="Generer les rapports et schedules pour le comptable"

8. **Echeances** (icon: calendar)
   - Tooltip: "Calendrier des echeances fiscales et rappels"
   - Link button to Echeances tab: "Calendrier fiscal", title="Voir les echeances fiscales et alertes de production"

9. **ML / IA** (icon: brain/gear)
   - Tooltip: "Re-entrainer le modele de categorisation automatique"
   - Button (POST to retrain endpoint): "Re-entrainer le modele ML", title="Entrainer le modele ML depuis les transactions approuvees du ledger"
   - Show result div for retrain feedback (hidden by default)
   - Use XHR for the POST call, show result in a `cqc-alert` below the button

**JavaScript** (inline `<script>` at bottom of template):
- Import form: XHR with FormData to import endpoint URL (build from `{{ url_for_current('import') }}` or construct from extension name). On success, show result summary in a cqc-alert-success div. On error, show cqc-alert-danger.
- Retrain button: XHR POST to retrain endpoint. On success, show count in cqc-alert-success. On error/warning, show appropriate alert.
- Journal button: fetch GET to journal endpoint. On success, render a simple cqc-table in the collapsible area.
- Use the `g.beancount_file_slug` based URL pattern: `/{slug}/extension/OperationsExtension/{endpoint}`

**CSS** (inline `<style>` block):
- `.cqc-ops-grid`: 3-column grid, gap 24px, responsive to 1-col on mobile
- `.cqc-ops-card`: use existing `cqc-card` class
- `.cqc-ops-card h3`: category title with icon
- `.cqc-ops-links`: flex-wrap container for link buttons within a card
- Keep all sizing using design system tokens (--cqc-font-*, --cqc-space-*)

**Registration**: Add to `ledger/main.beancount`:
```
2010-01-01 custom "fava-extension" "compteqc.fava_ext.operations"
```
Place it after the last existing extension registration line (after recus).

For Fava built-in report links, use the pattern:
- `/{slug}/trial_balance/` for trial balance / soldes
- `/{slug}/income_statement/` for income statement
- `/{slug}/balance_sheet/` for balance sheet
Where `{slug}` comes from the template variable. In Fava templates, use `url_for('report', report_name='trial_balance')` etc.
  </action>
  <verify>
1. Run `fava ledger/main.beancount` and navigate to the Operations tab in the sidebar.
2. Verify all 9 category cards render with tooltips on hover.
3. Verify link buttons navigate to correct tabs (Approbation, PaieQC, Recus, ExportCPA, Echeances).
4. Verify Fava built-in links (trial balance, income statement, balance sheet) navigate correctly.
5. Test import form: upload a CSV file, verify JSON response and feedback message.
6. Test retrain button: click and verify JSON response and feedback message.
  </verify>
  <done>
Operations tab visible in sidebar. All 9 category cards rendered with tooltip descriptions. Import form accepts file upload with account/source selectors and returns import results. Retrain button triggers ML retraining. Journal button loads auto-approved transactions. All link buttons navigate to correct existing tabs/pages.
  </done>
</task>

</tasks>

<verification>
1. Fava starts without errors with the new extension registered
2. Operations tab appears in the sidebar navigation
3. All category cards are present with hover tooltips
4. Import form submits via XHR and shows results
5. Retrain button works via XHR and shows results
6. All navigation links resolve to correct pages
7. Page is responsive (3-col to 1-col)
</verification>

<success_criteria>
- Operations tab is a working command center with all 9 operation categories
- Import and retrain are functional POST endpoints
- Journal review displays auto-approved transactions
- Every button/link has a descriptive title attribute (tooltip)
- Design uses cqc-* design system consistently
- Extension registered in main.beancount
</success_criteria>

<output>
After completion, create `.planning/quick/14-add-operations-tab-with-all-cli-commands/14-SUMMARY.md`
</output>
