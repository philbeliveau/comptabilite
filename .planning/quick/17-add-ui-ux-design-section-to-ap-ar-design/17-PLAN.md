---
phase: quick-17
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/design/accounts-payable-receivable.md
autonomous: true
requirements: [QUICK-17]

must_haves:
  truths:
    - "Design doc has a Section 8 covering complete UI/UX for AP/AR Fava tab"
    - "All wireframes use existing CQC CSS classes and Fava extension patterns"
    - "Receipt-to-AP pipeline UX is documented"
    - "Auto-matching approval UX is documented"
    - "Implementation roadmap is updated to include UI work"
  artifacts:
    - path: "docs/design/accounts-payable-receivable.md"
      provides: "Complete AP/AR design with UI/UX section"
      contains: "## 8. UI/UX Design"
  key_links:
    - from: "docs/design/accounts-payable-receivable.md"
      to: "src/compteqc/fava_ext/"
      via: "references to extension patterns"
      pattern: "FavaExtensionBase|extension_endpoint"
---

<objective>
Add a comprehensive UI/UX design section (Section 8) to the existing AP/AR design document at `docs/design/accounts-payable-receivable.md`.

Purpose: The backend design is thorough (851 lines covering data models, journal entries, aging, integration) but has no UI/UX layer. This section bridges backend design to the Fava extension implementation, providing wireframes, form specifications, and interaction flows for the new "Comptes a payer / a recevoir" tab.

Output: Updated design document with ~300-400 lines of new UI/UX content inserted as Section 8 before the appendices.
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@docs/design/accounts-payable-receivable.md
@src/compteqc/fava_ext/tableau_bord/templates/TableauBordExtension.html
@src/compteqc/fava_ext/recus/templates/RecusExtension.html
@src/compteqc/fava_ext/approbation/templates/ApprobationExtension.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Section 8 UI/UX Design to AP/AR document</name>
  <files>docs/design/accounts-payable-receivable.md</files>
  <action>
Insert a new "## 8. UI/UX Design -- Fava Extension" section before the existing appendices (currently starting at line 818 with "## Appendix: GIFI Code Reference"). Renumber the appendices if needed. The new section must cover all subsections below.

**8.1 Tab Overview: "Comptes a payer / a recevoir"**
- New Fava extension: `ComptesFournisseursExtension` (or similar), subclass of `FavaExtensionBase`
- Extension endpoint decorator pattern, like existing tabs
- Page structure: `cqc-page-header` with title, then KPI row, then sub-tab toggle, then content area
- ASCII wireframe showing full page layout

**8.2 KPI Row**
- 4 KPIs using `.cqc-kpi-row > .cqc-kpi` pattern (same as TableauBordExtension):
  - "Comptes clients (AR)" -- total outstanding AR, with `cqc-error` class if any overdue
  - "En retard (AR)" -- overdue AR amount with count badge
  - "Comptes fournisseurs (AP)" -- total outstanding AP
  - "Position nette" -- AR minus AP, green if positive, red if negative
- Use `data-value` and `data-decimals="2"` attributes for animated number rendering (same pattern as dashboard)

**8.3 Sub-tab Toggle**
- Two-button toggle: "Factures clients" (AR) and "Factures fournisseurs" (AP)
- Use `.cqc-tab-toggle` CSS class (define it inline in `<style>` block, same pattern as other extensions)
- JavaScript toggle showing/hiding corresponding `<div>` sections
- Default: show AR tab (most frequently checked)

**8.4 Invoice/Bill List Table**
- Use `.cqc-table` for both AR and AP lists
- AR columns: Numero, Client, Date, Echeance, Total, Paye, Solde, Statut, Actions
- AP columns: Numero interne, Fournisseur, Ref fournisseur, Date facture, Echeance, Total, Paye, Solde, Statut, Actions
- Status badges using `.cqc-badge` with variants:
  - `cqc-badge-draft` (gray) for DRAFT/RECEIVED
  - `cqc-badge-sent` (blue) for SENT/APPROVED
  - `cqc-badge-partial` (orange) for PARTIAL
  - `cqc-badge-paid` (green) for PAID
  - `cqc-badge-overdue` (red) for OVERDUE/DISPUTED
- Aging color indicator: subtle left border color on rows (green=current, yellow=30-60, orange=60-90, red=90+)
- Action buttons: "Payer" (`.cqc-btn cqc-btn-sm`), "Voir" link to entry context in Fava
- ASCII wireframe of the table

**8.5 Aging Stacked Bar Chart**
- Chart.js stacked horizontal bar chart below the table
- Two bars: AR and AP, each segmented by aging bucket (Current, 30-60, 60-90, 90+)
- Color scheme: Quebec blue palette (--cqc-blue-100 through --cqc-blue-700) for AR, muted gray-blue for AP
- Use same Chart.js patterns as dashboard: `data-chart` JSON attribute on canvas container, registry Map with destroy-on-navigate lifecycle
- Include the Chart.js configuration JSON structure

**8.6 "+Nouvelle facture" Form (AR Creation)**
- Button at top of AR sub-tab: `.cqc-btn cqc-btn-primary` with "+Nouvelle facture"
- Slides open a `.cqc-card` form section (or modal -- recommend inline expansion for simplicity)
- Fields: Client (text input with autocomplete from existing clients in registry), Date, Echeance (auto-fill Net 30), Lignes (dynamic add/remove rows), each line: Description, Quantite, Prix unitaire, TPS applicable (checkbox, default on), TVQ applicable (checkbox, default on), Notes
- Pre-calculated totals shown live: Sous-total, TPS, TVQ, Total
- Submit button: POST to extension_endpoint, creates Facture + journal entry
- This brings `cqc facture creer` CLI functionality to web

**8.7 "+Nouvelle facture fournisseur" Form (AP Creation)**
- Button at top of AP sub-tab: `.cqc-btn cqc-btn-primary` with "+Nouvelle facture fournisseur"
- Fields: Fournisseur (autocomplete from existing vendors in RegistreFournisseurs), Reference fournisseur (text), Date facture, Date echeance, Lignes (dynamic rows), each line: Description, Montant, Categorie depense (dropdown populated from chart of accounts expense categories), TPS applicable, TVQ applicable, taux_itc (default 1.0, set to 0.5 for meals), taux_itr (default 1.0), Notes
- Same live total calculation
- Submit: POST to extension_endpoint, creates FactureFournisseur + journal entry

**8.8 Receipt-to-AP Pipeline UX**
- Document the flow from existing Recus tab to AP creation:
  1. User uploads receipt in Recus tab (existing)
  2. AI extraction produces: vendor, date, amount, tax breakdown (existing)
  3. NEW: After extraction, show "Creer entree AP?" prompt button
  4. Clicking it navigates to AP tab with form pre-filled from extracted data
  5. User reviews, adjusts category, confirms
- Wireframe showing the prompt on the Recus extraction result
- Note: This is the primary AP entry path for a solo consultant (receipt-driven, not manual form)

**8.9 Auto-matching UX in Approval Queue**
- Enhancement to existing ApprobationExtension (approval/transaction review tab)
- When a bank deposit matches an AR invoice (per Section 6.1 matching logic):
  - Show match suggestion: "Correspond a FAC-2026-003 - Acme Corp ($5,750.00)" with confidence percentage
  - "Lier" button (same POST redirect pattern as existing Lier in Recus) to confirm match and generate payment entry
- When a bank withdrawal matches an AP bill:
  - Show: "Correspond a FOUR-2026-001 - Cabinet Comptable ($1,149.75)"
  - "Lier" button to confirm and record AP payment
- ASCII wireframe of a matched transaction row in approval queue

**8.10 Dashboard Homepage Integration**
- New KPI card on TableauBordExtension for AP/AR position
- Add after existing KPIs: "Position AR/AP" showing net position value
- Color: green if net positive (AR > AP), red if negative
- Clicking navigates to the AP/AR tab
- Requires: new method on TableauBordExtension Python class to query both registries

**8.11 Solo Consultant Workflow Summary**
- Document the realistic day-to-day workflow:
  - AP: Upload receipt -> AI extracts -> "Creer AP?" -> pre-filled form -> confirm. Rarely manual form entry.
  - AR: Use recurring template for monthly retainer -> auto-generated invoice -> send to client. Occasional manual invoice for one-off projects.
  - Matching: Review approval queue -> system suggests AR/AP matches -> confirm with "Lier"
  - Review: Weekly glance at KPI row for overdue amounts
- Emphasize that most AP entries come from receipt upload, not manual forms
- Emphasize that most AR entries come from recurring templates (Phase C in roadmap)

**8.12 Updated Implementation Roadmap**
- Update existing Phase D (Dashboard and MCP Integration) to include:
  - Fava extension tab creation (Python + Jinja2 template)
  - KPI row, sub-tab toggle, list tables
  - Chart.js aging visualization
  - Form endpoints for AR/AP creation
- Add Phase E: "Receipt-to-AP Pipeline and Auto-matching UX"
  - Receipt extraction -> AP creation prompt
  - Approval queue matching suggestions
  - Dashboard KPI integration
- Update the dependency diagram to include Phase E

Use ASCII art wireframes throughout (same style as Section 6.3 already uses). Reference existing CSS classes by name. Reference existing extension Python patterns (FavaExtensionBase, extension_endpoint, kpis() method pattern). Keep all text in French for UI labels, English for technical descriptions (matching the existing document style).
  </action>
  <verify>
    <automated>grep -c "## 8\. UI/UX Design" docs/design/accounts-payable-receivable.md | grep -q "1" && grep -c "cqc-kpi-row" docs/design/accounts-payable-receivable.md | grep -qv "^0" && grep -c "Phase E" docs/design/accounts-payable-receivable.md | grep -qv "^0" && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>
    - Section 8 exists with all 12 subsections (8.1 through 8.12)
    - ASCII wireframes for: full page layout, table, form, receipt-to-AP prompt, matching row
    - All UI elements reference existing CQC CSS classes
    - Implementation roadmap updated with Phase E
    - Document line count increased by ~300-400 lines
    - Appendices still present after the new section
  </done>
</task>

</tasks>

<verification>
- `grep "## 8" docs/design/accounts-payable-receivable.md` shows "## 8. UI/UX Design"
- `grep "## Appendix" docs/design/accounts-payable-receivable.md` still shows both appendices
- `grep "Phase E" docs/design/accounts-payable-receivable.md` shows updated roadmap
- `wc -l docs/design/accounts-payable-receivable.md` shows ~1150-1250 lines (was 851)
</verification>

<success_criteria>
The AP/AR design document is a complete implementation reference covering both backend (existing) and frontend (new Section 8), ready for a developer to implement the Fava extension tab without ambiguity about layout, forms, interactions, or CSS patterns.
</success_criteria>

<output>
After completion, create `.planning/quick/17-add-ui-ux-design-section-to-ap-ar-design/17-SUMMARY.md`
</output>
