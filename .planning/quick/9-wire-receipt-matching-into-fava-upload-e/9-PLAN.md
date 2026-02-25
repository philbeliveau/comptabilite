---
phase: quick-9
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/compteqc/fava_ext/recus/__init__.py
autonomous: false
requirements: [QUICK-9]

must_haves:
  truths:
    - "After upload+extraction, user sees a table of matching transactions sorted by score"
    - "User can click a link button on a match row to write a document directive and redirect back"
    - "If no matches found, user sees a message saying no matches and a back link"
  artifacts:
    - path: "src/compteqc/fava_ext/recus/__init__.py"
      provides: "Upload handler calls renommer_recu + proposer_correspondances; new /link POST endpoint calls generer_directive_document + ecrire_directive"
      contains: "extension_endpoint.*link"
  key_links:
    - from: "src/compteqc/fava_ext/recus/__init__.py"
      to: "compteqc.documents.upload.renommer_recu"
      via: "import and call after extraction"
      pattern: "renommer_recu"
    - from: "src/compteqc/fava_ext/recus/__init__.py"
      to: "compteqc.documents.matching.proposer_correspondances"
      via: "import and call with self.ledger.all_entries"
      pattern: "proposer_correspondances"
    - from: "src/compteqc/fava_ext/recus/__init__.py"
      to: "compteqc.documents.beancount_link"
      via: "import and call in /link endpoint"
      pattern: "generer_directive_document|ecrire_directive"
---

<objective>
Wire the existing receipt-matching pipeline (rename, match, link) into the Fava RecusExtension upload endpoint.

Purpose: After a receipt is uploaded and extracted, the user should see candidate transaction matches and be able to link a receipt to a transaction with one click, writing a Beancount document directive.

Output: Updated RecusExtension with full upload-rename-match-link flow via form POSTs (same pattern as ApprobationExtension).
</objective>

<execution_context>
@/Users/philippebeliveau/.claude/get-shit-done/workflows/execute-plan.md
@/Users/philippebeliveau/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/compteqc/fava_ext/recus/__init__.py
@src/compteqc/fava_ext/recus/templates/RecusExtension.html
@src/compteqc/fava_ext/approbation/__init__.py (reference pattern for form POST + redirect)
@src/compteqc/documents/__init__.py (public API: renommer_recu, proposer_correspondances, generer_directive_document, ecrire_directive)
@src/compteqc/documents/upload.py (renommer_recu signature)
@src/compteqc/documents/matching.py (proposer_correspondances signature, Correspondance model)
@src/compteqc/documents/beancount_link.py (generer_directive_document, ecrire_directive signatures)
@src/compteqc/documents/extraction.py (DonneesRecu model)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire rename + matching into upload handler, add /link endpoint</name>
  <files>src/compteqc/fava_ext/recus/__init__.py</files>
  <action>
Modify the `upload()` method in `RecusExtension` to call `renommer_recu()` and `proposer_correspondances()` after extraction, then render an HTML match results page instead of the current raw HTML.

Specific changes:

1. Add imports at the top:
   - `from werkzeug.utils import redirect` (same as approbation)
   - Inside the upload handler (lazy): `from compteqc.documents.upload import renommer_recu`
   - Inside the upload handler (lazy): `from compteqc.documents.matching import proposer_correspondances`
   - Inside the link handler (lazy): `from compteqc.documents.beancount_link import generer_directive_document, ecrire_directive`

2. In `upload()`, after `donnees = extraire_recu(stored)` succeeds:
   - Call `renamed = renommer_recu(stored, donnees)` to rename with vendor slug
   - Call `correspondances = proposer_correspondances(donnees, self.ledger.all_entries)` to find matches
   - Compute `chemin_relatif = renamed.relative_to(ledger_path.parent)` for display
   - Reload ledger: `self.ledger.load_file()`
   - Instead of returning raw HTML string, build an HTML response that shows:
     - Success message with filename and extracted data summary (fournisseur, date, total)
     - If correspondances is non-empty: a table with columns Date, Narration, Montant, Score, and a "Lier" form button per row. Each row's form POSTs to the /link endpoint with hidden fields: `chemin_recu` (str(chemin_relatif)), `date_txn` (correspondance.date.isoformat()), `compte` (first posting account from the matched transaction -- need to look it up from self.ledger.all_entries[correspondance.transaction_index]), `narration` (for display).
     - If correspondances is empty: "Aucune correspondance trouvee" message
     - A "Retour" link back to the extension page

   IMPORTANT: To get the account for the document directive, look up the matched transaction from `self.ledger.all_entries[correspondance.transaction_index]` and use the first posting's account. Store this in a hidden field `compte` in the link form.

   Build the link URL as: `/{{ beancount_file_slug }}/extension/RecusExtension/link` -- use `request.url_root` or construct relative to current URL. Safest approach: use `request.url.rsplit('/', 1)[0] + '/link'` to build the link endpoint URL from the upload endpoint URL.

   Use inline HTML (like the existing upload handler does) rather than a separate template file. This keeps the change minimal. Use the same CSS classes as the main template (cqc-table, cqc-card, etc.) for visual consistency.

3. Add a new endpoint method:

   ```python
   @extension_endpoint("link", ["POST"])
   def link(self) -> str:
       """POST /link -- lie un recu a une transaction via directive document."""
       from compteqc.documents.beancount_link import generer_directive_document, ecrire_directive
       import datetime

       chemin_recu = request.form.get("chemin_recu", "")
       date_str = request.form.get("date_txn", "")
       compte = request.form.get("compte", "")

       if not chemin_recu or not date_str or not compte:
           return ('<html><body><h2>Erreur</h2>'
                   '<p>Parametres manquants.</p>'
                   '<a href="javascript:history.back()">Retour</a>'
                   '</body></html>')

       date_txn = datetime.date.fromisoformat(date_str)
       ledger_path = Path(self.ledger.beancount_file_path)
       ledger_dir = ledger_path.parent

       directive = generer_directive_document(date_txn, compte, chemin_recu)
       ecrire_directive(directive, ledger_dir, date_txn.year, date_txn.month)

       self.ledger.load_file()

       return redirect(request.referrer or request.url)
   ```

   This follows the exact same pattern as ApprobationExtension.approuver() and ApprobationExtension.rejeter(): form POST, do work, reload ledger, redirect.

4. Keep the existing fallback paths (extraction failure, phase 5 not available) unchanged.
  </action>
  <verify>
Run: `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -c "from compteqc.fava_ext.recus import RecusExtension; print('OK')"`

Verify the link endpoint method exists: `python -c "from compteqc.fava_ext.recus import RecusExtension; assert hasattr(RecusExtension, 'link'); print('link endpoint OK')"`

Run existing tests: `cd /Users/philippebeliveau/Desktop/Notebook/comptabilite && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
  </verify>
  <done>
Upload handler calls renommer_recu + proposer_correspondances after extraction and returns HTML with match table. New /link POST endpoint calls generer_directive_document + ecrire_directive then redirects. All existing tests pass.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Verify receipt upload-match-link flow in Fava</name>
  <files>src/compteqc/fava_ext/recus/__init__.py</files>
  <action>Human verifies the full receipt flow works end-to-end in Fava.</action>
  <verify>
    1. Start Fava: `fava ledger/main.beancount`
    2. Navigate to the "Recus" extension page
    3. Upload a receipt image (PDF, JPG, or PNG)
    4. After upload, verify: success message shows extracted vendor/date/total, match table appears with candidate transactions, each row has a "Lier" button
    5. Click "Lier" on a match row
    6. Verify redirect back to the Recus page
    7. Check the monthly beancount file for the new document directive
  </verify>
  <done>User confirms upload-rename-match-link flow works correctly in the browser.</done>
</task>

</tasks>

<verification>
- `python -c "from compteqc.fava_ext.recus import RecusExtension"` imports without error
- `RecusExtension` has both `upload` and `link` methods decorated with `@extension_endpoint`
- Existing test suite passes
</verification>

<success_criteria>
- Upload flow calls renommer_recu (file renamed with vendor slug) and proposer_correspondances (match table shown)
- /link endpoint writes document directive to monthly beancount file via generer_directive_document + ecrire_directive
- Pattern matches existing ApprobationExtension (form POST + redirect)
- Only 1 file modified: __init__.py (match results rendered as inline HTML in upload response)
</success_criteria>

<output>
After completion, create `.planning/quick/9-wire-receipt-matching-into-fava-upload-e/9-SUMMARY.md`
</output>
