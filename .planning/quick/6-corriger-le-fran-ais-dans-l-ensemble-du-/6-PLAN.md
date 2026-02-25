---
phase: quick-6
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html
  - src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html
  - src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
  - src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html
  - src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html
  - src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html
  - src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html
  - src/compteqc/fava_ext/recus/templates/RecusExtension.html
  - src/compteqc/rapports/templates/balance_verification.html
  - src/compteqc/rapports/templates/bilan.html
  - src/compteqc/rapports/templates/etat_resultats.html
  - src/compteqc/rapports/templates/sommaire_paie.html
  - src/compteqc/rapports/templates/sommaire_pret.html
  - src/compteqc/rapports/templates/sommaire_dpa.html
  - src/compteqc/rapports/templates/sommaire_taxes.html
  - src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
autonomous: true
requirements: [QUICK-6]
must_haves:
  truths:
    - "All user-visible French text in Fava extension templates uses correct accents"
    - "All user-visible French text in report templates uses correct accents"
    - "All REPORT_INTROS and TOOLTIPS dictionary values in ThemeQCExtension.js use correct accents"
    - "No Jinja2 syntax, HTML entities, or JavaScript string escaping is broken"
  artifacts:
    - path: "src/compteqc/fava_ext/*/templates/*.html"
      provides: "8 Fava extension templates with corrected French"
    - path: "src/compteqc/rapports/templates/*.html"
      provides: "7 report templates with corrected French"
    - path: "src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js"
      provides: "REPORT_INTROS and TOOLTIPS with corrected French"
  key_links: []
---

<objective>
Fix all French accent and orthography errors across the entire UI: Fava extension templates, report templates, and JavaScript dictionaries.

Purpose: Correct, professional French throughout the accounting dashboard.
Output: 16 files with proper French diacritics (e, a, e, e, o, c, etc.)
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix French accents in 8 Fava extension templates</name>
  <files>
    src/compteqc/fava_ext/echeances/templates/EcheancesExtension.html
    src/compteqc/fava_ext/paie_qc/templates/PaieQCExtension.html
    src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
    src/compteqc/fava_ext/dpa_qc/templates/DpaQCExtension.html
    src/compteqc/fava_ext/taxes_qc/templates/TaxesQCExtension.html
    src/compteqc/fava_ext/pret_actionnaire/templates/PretActionnaireExtension.html
    src/compteqc/fava_ext/export_cpa/templates/ExportCPAExtension.html
    src/compteqc/fava_ext/recus/templates/RecusExtension.html
  </files>
  <action>
    Read each file and fix ALL user-visible French text missing accents. Key fixes per file:

    - EcheancesExtension.html: Echeances->Echeances, echeance->echeance, pret->pret (in visible text and title attributes only)
    - PaieQCExtension.html: impot->impot (in visible text only)
    - ApprobationExtension.html: Beneficiaire->Beneficiaire, Categorie->Categorie, Elevee->Elevee, Moderee->Moderee, Revision->Revision, Depenses->Depenses
    - DpaQCExtension.html: Deduction->Deduction, debut->debut, ecritures->ecritures
    - TaxesQCExtension.html: periode->periode
    - PretActionnaireExtension.html: Pret->Pret, enregistre->enregistre
    - ExportCPAExtension.html: fonctionnalite->fonctionnalite, implementee->implementee, prevus->prevus
    - RecusExtension.html: Televersement->Televersement, recus->recus, deposez->deposez, recent->recent

    IMPORTANT RULES:
    - Only fix text inside HTML tags, title attributes, and user-visible strings
    - Do NOT change Jinja2 variable names, block names, or macro names
    - Do NOT change HTML id/class attributes or data- attributes
    - Do NOT change CSS class names or JavaScript identifiers
    - Preserve all Jinja2 {{ }}, {% %}, {# #} syntax exactly
    - Scan each file thoroughly -- the list above is a guide, not exhaustive
  </action>
  <verify>
    For each file: python3 -c "open('FILE', encoding='utf-8').read()" confirms valid UTF-8.
    Grep for common missing-accent patterns: grep -rn "Echeance[^s]\\|Beneficiaire\\|Categorie\\|Deduction" in the 8 files should return zero hits on unaccented versions in visible text.
  </verify>
  <done>All 8 Fava extension templates display correct French with proper accents in all user-visible text. No Jinja2 syntax broken.</done>
</task>

<task type="auto">
  <name>Task 2: Fix French accents in 7 report templates</name>
  <files>
    src/compteqc/rapports/templates/balance_verification.html
    src/compteqc/rapports/templates/bilan.html
    src/compteqc/rapports/templates/etat_resultats.html
    src/compteqc/rapports/templates/sommaire_paie.html
    src/compteqc/rapports/templates/sommaire_pret.html
    src/compteqc/rapports/templates/sommaire_dpa.html
    src/compteqc/rapports/templates/sommaire_taxes.html
  </files>
  <action>
    Read each file and fix ALL user-visible French text missing accents. Key fixes per file:

    - balance_verification.html: verification->verification, equilibree->equilibree
    - bilan.html: Resultat->Resultat, Equation->Equation, verifiee->verifiee
    - etat_resultats.html: Etat->Etat, resultats->resultats, depenses->depenses, RESULTAT->RESULTAT
    - sommaire_paie.html: Impot->Impot
    - sommaire_pret.html: pret->pret, continuite->continuite, Detail->Detail, Echeances->Echeances
    - sommaire_dpa.html: Deduction->Deduction, Reclamee->Reclamee, Detail->Detail
    - sommaire_taxes.html: Percue->Percue, Payee->Payee

    SAME RULES as Task 1:
    - Only fix user-visible text (headings, labels, paragraphs, title attributes)
    - Preserve all Jinja2 syntax, HTML structure, CSS classes
    - Scan thoroughly -- the list above is a guide, not exhaustive
  </action>
  <verify>
    For each file: python3 -c "open('FILE', encoding='utf-8').read()" confirms valid UTF-8.
    Grep for common patterns: grep -rn "Resultat\\|verification\\|Deduction\\|Echeance" in the 7 files should return zero unaccented hits in visible text positions.
  </verify>
  <done>All 7 report templates display correct French with proper accents in all user-visible text. No Jinja2 syntax broken.</done>
</task>

<task type="auto">
  <name>Task 3: Fix French accents in ThemeQCExtension.js dictionaries</name>
  <files>
    src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
  </files>
  <action>
    Read ThemeQCExtension.js and fix ALL French accent errors in:

    1. REPORT_INTROS dictionary: Fix all string values (Etat->Etat, resultats->resultats, etc.)
    2. TOOLTIPS dictionary: Fix all 64+ tooltip string values for proper French accents
    3. SIDEBAR_GROUPS array: Fix any French labels missing accents
    4. Any other user-visible French string literals in the file

    IMPORTANT RULES:
    - Only fix string VALUES (inside quotes), never object keys used for lookups unless the key is matched against user-visible text
    - CRITICAL: If object keys in REPORT_INTROS or TOOLTIPS are matched against DOM text content, and the DOM text is being fixed in Tasks 1-2, then the keys MUST be updated to match the corrected DOM text
    - Preserve all JavaScript syntax: template literals, string concatenation, regex patterns
    - Do NOT change function names, variable names, or code logic
    - Ensure string escaping is preserved (no unescaped quotes inside strings)
    - The file uses backtick template literals -- preserve these exactly
  </action>
  <verify>
    node -c src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js confirms valid JavaScript syntax.
    Manual review: spot-check 5+ TOOLTIPS entries and 3+ REPORT_INTROS entries for correct accents.
  </verify>
  <done>All REPORT_INTROS entries, all 64+ TOOLTIPS entries, and all other user-visible French strings in ThemeQCExtension.js use correct French accents. JavaScript syntax remains valid.</done>
</task>

</tasks>

<verification>
1. All 16 files are valid UTF-8: python3 -c "import glob; [open(f, encoding='utf-8').read() for f in glob.glob('src/compteqc/**/templates/*.html', recursive=True)]"
2. ThemeQCExtension.js passes syntax check: node -c src/compteqc/fava_ext/theme_qc/ThemeQCExtension.js
3. Run existing tests to confirm no breakage: cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5
</verification>

<success_criteria>
- All 16 files have correct French diacritics in user-visible text
- Zero Jinja2 template syntax errors
- Zero JavaScript syntax errors
- Existing tests still pass
</success_criteria>

<output>
After completion, create `.planning/quick/6-corriger-le-fran-ais-dans-l-ensemble-du-/6-SUMMARY.md`
</output>
