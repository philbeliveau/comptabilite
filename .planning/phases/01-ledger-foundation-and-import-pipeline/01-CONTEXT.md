# Phase 1: Ledger Foundation and Import Pipeline - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Working double-entry Beancount ledger with a Quebec-appropriate chart of accounts (GIFI-mapped), RBC transaction import (chequing + credit card), rule-based categorization for the majority of transactions, and basic CLI for import and reporting. AI categorization, payroll, GST/QST tracking, and web UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Plan comptable (Chart of Accounts)
- Granularité modérée (~50-60 comptes) : assez détaillé pour être utile sans devenir du bruit
- Revenu unique pour l'instant (pas de split consulting vs Enact) ; on séparera quand Enact génère des revenus
- Noms de comptes en français (ex: "Dépenses:Bureau:Abonnements-Logiciels", "Revenus:Consultation")
- Mappage GIFI : à la discrétion de Claude (metadata Beancount ou fichier séparé)

### Import et normalisation
- Deux comptes à importer : compte-chèques RBC + carte de crédit RBC
- Les deux formats disponibles (CSV et OFX/QFX) — Claude choisit le meilleur ou supporte les deux
- Devise CAD uniquement pour la Phase 1 (pas de multi-devises)
- Déduplication : à la discrétion de Claude (approche la plus sûre pour l'exactitude comptable)

### Catégorisation par règles
- Format des règles : à la discrétion de Claude (YAML, Python, ou autre selon les conventions Beancount)
- Transactions sans correspondance : postées dans un compte "Non-classé" (holding account) pour revue ultérieure
- Pas de pré-chargement de règles — on commence vide et on bâtit au fur et à mesure des imports
- Suggestion automatique de règles après catégorisation manuelle : à la discrétion de Claude

### CLI
- Nom de commande : `cqc` (CompteQC)
- Langue de l'interface CLI : français (messages, aide, erreurs, prompts)
- Format de sortie par défaut des rapports : à la discrétion de Claude
- Flux d'import quotidien : à la discrétion de Claude (balance entre vitesse et sécurité)

### Claude's Discretion
- Stockage du mappage GIFI (metadata vs fichier séparé)
- Choix de format d'import préféré (CSV vs OFX) ou support des deux
- Stratégie de déduplication des transactions
- Format de définition des règles de catégorisation
- Suggestion automatique de règles après correction manuelle
- Format de sortie par défaut (table, plain text, etc.)
- Design du flux import → revue → post (une étape ou plusieurs)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraints from CLAUDE.md:
- All monetary amounts must use Decimal (never float)
- Ledger data as plain-text .beancount files under git version control with auto-commit on changes
- bean-check must pass after every import
- System must not silently invent categories or numbers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-ledger-foundation-and-import-pipeline*
*Context gathered: 2026-02-18*
