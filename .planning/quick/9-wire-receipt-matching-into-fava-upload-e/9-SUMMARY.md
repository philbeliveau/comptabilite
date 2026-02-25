# Quick Task 9: Wire receipt matching into Fava upload endpoint

## Summary

Wired the existing CLI receipt-matching pipeline (rename, match, link) into the Fava RecusExtension upload endpoint using Option A (form POST pattern).

## Changes

### `src/compteqc/fava_ext/recus/__init__.py`

**Upload handler modifications:**
- After Claude Vision extraction (`extraire_recu`), now calls `renommer_recu()` to rename with vendor slug
- Calls `proposer_correspondances()` to match receipt against existing ledger transactions by amount+date
- Returns HTML page showing extracted data (vendor, date, total) and match table with scores
- Each match row has a "Lier" button that POSTs to the new `/link` endpoint

**New `/link` endpoint:**
- `@extension_endpoint("link", ["POST"])` handler
- Receives `chemin_recu`, `date_txn`, `compte` from form hidden fields
- Calls `generer_directive_document()` + `ecrire_directive()` to write a Beancount `document` directive
- Redirects back to RecusExtension page with 303 See Other (ensures GET after POST)

**Bug fixes during testing:**
- Fixed URL construction: uses `g.beancount_file_slug` f-string instead of `request.url` splitting (which produced wrong paths)
- Fixed redirect: uses 303 instead of 302 (302 preserves POST method, causing 405 on the GET-only report page)
- Fixed `url_for()` conflict: Flask's `url_for` clashes when route has a parameter also named `endpoint`

## Commits

- `85ed3b1` — Initial wiring of rename+match+link into upload handler
- `ef49032` — Fix /link endpoint URL routing and redirect
