# Phase 7: Dashboard Homepage - Research

**Researched:** 2026-02-25
**Domain:** Fava extension backend (Python/Beancount) + Chart.js frontend dashboard
**Confidence:** HIGH

## Summary

Phase 7 builds a dashboard homepage as a new Fava extension (`TableauBordExtension`) that computes five KPI values, monthly revenue series, expense category breakdown, and recent transactions from the Beancount ledger. The Python backend follows the exact same pattern as the 9 existing extensions (inherit `FavaExtensionBase`, implement `after_load_file()`, expose data methods callable from Jinja2 templates). The HTML template uses `[data-chart]` containers and `[data-value]` attributes that Phase 6's `renderCharts()` and `animateKPIs()` discover and animate automatically.

The architecture is straightforward: all five KPIs and both chart datasets are computable from the Beancount entries already accessible via `self.ledger.all_entries`. The existing `compteqc.mcp.services.calculer_soldes()` and the pattern in `etat_resultats()` (MCP tool) provide proven code for summing revenue/expense accounts. The dashboard extension just needs to pre-compute these aggregates in `after_load_file()` and expose them as template-friendly dicts and JSON strings.

**Primary recommendation:** Create a single new Fava extension `TableauBordExtension` with Python backend computing all data in `after_load_file()`, and a Jinja2 template that renders KPI cards with `data-value` attributes, two `[data-chart]` containers (line + doughnut), and a recent transactions table. No new JavaScript is needed -- Phase 6's infrastructure handles rendering.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | KPI cards (Revenue YTD, Expenses YTD, Net Income, Tax Owing, Pending Approvals) with count-up animation | Backend computes 5 KPIs from Beancount entries. Template renders `[data-value]` attributes. Phase 6's `animateKPIs()` handles animation. |
| DASH-02 | Monthly revenue trend as Chart.js line chart | Backend aggregates revenue by month (Jan-Dec current year). Template emits `[data-chart]` container with JSON data. Phase 6's `renderCharts()` creates Chart.js line instance. |
| DASH-03 | Expense category breakdown as Chart.js doughnut chart | Backend groups expenses by top-level category, caps at top 6 + "Autres". Template emits `[data-chart]` container. Phase 6's `renderCharts()` creates doughnut instance. |
| DASH-04 | Last 10 transactions with status badges | Backend extracts last 10 transactions sorted by date descending. Template renders table rows with date, payee, narration, amount, status badge. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Fava extension (FavaExtensionBase) | Fava 1.29+ | Extension framework for custom pages | Already used by all 9 existing extensions in the project |
| Beancount | 2.3+ | Ledger data access via `self.ledger.all_entries` | Core accounting engine, already installed |
| Chart.js | 4.4.8 UMD | Line and doughnut chart rendering | Phase 6 decision -- CDN loaded, registry managed |
| Jinja2 | (bundled with Fava) | HTML template rendering | Standard Fava template engine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` (stdlib) | Python 3.12 | Serialize chart data to JSON for `data-chart` attributes | Every chart container needs JSON-encoded data |
| `Intl.NumberFormat` | Browser native | Format animated KPI numbers in fr-CA locale | Phase 6's `animateKPIs()` already uses this |
| `compteqc.mcp.services` | Internal | `calculer_soldes()`, `lister_pending()`, `formater_montant()` | Reuse for KPI computation, avoid duplicating logic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Computing in `after_load_file()` | JSON API endpoint | Adds complexity; server-rendered data is simpler and faster for a single-user tool. No benefit from async loading here. |
| Top-level expense categories | Full account hierarchy | Top-level (e.g., "Salaires", "Bureau", "Vehicule") is more readable in a doughnut chart. Drilling down is deferred to VIZ-03. |
| Separate extension JS | Phase 6 shared infrastructure | No custom JS needed -- `renderCharts()` and `animateKPIs()` handle everything via data attributes. |

## Architecture Patterns

### Recommended Project Structure
```
src/compteqc/fava_ext/tableau_bord/
  __init__.py                  # TableauBordExtension class
  templates/
    TableauBordExtension.html  # Dashboard template
```

### Pattern 1: Fava Extension with Computed Data
**What:** Python class inherits `FavaExtensionBase`, sets `report_title`, implements `after_load_file()` to pre-compute all dashboard data, exposes data via methods callable from Jinja2.
**When to use:** Every Fava extension page follows this pattern.
**Example:**
```python
# Source: Existing pattern from compteqc.fava_ext.taxes_qc
class TableauBordExtension(FavaExtensionBase):
    report_title = "Tableau de bord"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._kpis: dict = {}
        self._revenus_mensuels: list[dict] = []
        self._depenses_categories: list[dict] = []
        self._transactions_recentes: list[dict] = []

    def after_load_file(self) -> None:
        """Recompute all dashboard data when ledger reloads."""
        self._compute_kpis()
        self._compute_revenus_mensuels()
        self._compute_depenses_categories()
        self._compute_transactions_recentes()

    def kpis(self) -> dict:
        return self._kpis
    # ... etc
```

### Pattern 2: Chart Data via data-chart HTML Attribute
**What:** Template renders a `<div class="cqc-chart-container" data-chart='{"labels":...,"datasets":...}' data-chart-type="line">` containing a `<canvas>`. Phase 6's `renderCharts()` discovers these containers and creates Chart.js instances.
**When to use:** Any page needing a chart.
**Example:**
```html
<!-- Source: Phase 6 plan 06-01, renderCharts() spec -->
<div class="cqc-chart-container"
     id="chart-revenus-mensuels"
     data-chart='{{ extension.revenus_mensuels_json() }}'
     data-chart-type="line">
  <canvas></canvas>
</div>
```

### Pattern 3: KPI Animation via data-value HTML Attribute
**What:** Template renders KPI values as `<div class="cqc-kpi-value" data-value="123456.78" data-decimals="2" data-suffix=" $">0 $</div>`. Phase 6's `animateKPIs()` animates from 0 to the target value.
**When to use:** Any numeric KPI that should animate on page load.
**Example:**
```html
<!-- Source: Phase 6 plan 06-01, animateKPIs() spec -->
<div class="cqc-kpi-value" data-value="{{ kpis.revenus_ytd }}" data-decimals="2" data-suffix=" $">
  {{ "{:,.2f}".format(kpis.revenus_ytd) }} $
</div>
```
Note: The server-rendered text inside the element serves as fallback for no-JS and is overwritten by the animation. This is critical for accessibility and SEO (though SEO is not relevant here).

### Pattern 4: Registering Extension in main.beancount
**What:** Add `fava-extension` custom directive to `ledger/main.beancount`.
**When to use:** Every new Fava extension.
**Example:**
```beancount
2010-01-01 custom "fava-extension" "compteqc.fava_ext.tableau_bord"
```

### Anti-Patterns to Avoid
- **Duplicating calculation logic:** Do NOT rewrite revenue/expense summing from scratch. Reuse `calculer_soldes()` from `compteqc.mcp.services` and adapt the `etat_resultats` pattern from `compteqc.mcp.tools.ledger`.
- **Client-side data fetching:** Do NOT create an AJAX endpoint for dashboard data. Server-render everything in the template. This is a single-user tool; round-trip latency adds nothing.
- **Custom Chart.js code in template `<script>` blocks:** Do NOT write inline Chart.js initialization. Phase 6's `renderCharts()` handles all chart creation via `[data-chart]` discovery. Writing separate chart code would bypass the registry and cause memory leaks.
- **Hardcoding month names:** Use Python's data-driven approach (iterate months 1-12 for current year). French month names should use a lookup or strftime with locale.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Revenue/expense totals | Custom entry iteration | `calculer_soldes(entries, filtre="Revenus")` from `compteqc.mcp.services` | Already tested, handles all edge cases (zero balances, missing postings) |
| Number formatting | Custom string formatting | `Intl.NumberFormat('fr-CA')` (JS) and `"{:,.2f}".format()` (Python) | Locale-correct thousand separators and decimal points |
| Chart.js lifecycle | Manual canvas management | Phase 6 `renderCharts()` + `chartRegistry` | Handles create/destroy on SPA navigation; prevents canvas leaks |
| KPI count-up animation | Manual requestAnimationFrame | Phase 6 `animateKPIs()` with `[data-value]` attributes | Handles easing, reduced-motion, locale formatting |
| Pending count | Custom query | `lister_pending(entries)` from `compteqc.mcp.services` | Already used by ApprobationExtension |

**Key insight:** Phase 7 needs zero new JavaScript. All frontend behavior (chart rendering, KPI animation, page transitions) is handled by Phase 6's infrastructure. Phase 7 is purely a Python backend + HTML template.

## Common Pitfalls

### Pitfall 1: Beancount Revenue Sign Convention
**What goes wrong:** Revenue accounts in Beancount have negative balances (they are credits). Displaying raw balance shows "-150,000" instead of "150,000".
**Why it happens:** Double-entry accounting: revenue postings are credits (negative in Beancount's internal representation).
**How to avoid:** Negate revenue balances when computing KPIs and chart data. The existing `etat_resultats` MCP tool already does this: `total_revenus = sum(-v for v in revenus.values())`.
**Warning signs:** Negative numbers showing up in KPI cards or chart data points going below zero.

### Pitfall 2: Empty Months in Line Chart
**What goes wrong:** If a month has no transactions (e.g., future months in current fiscal year), the line chart has gaps or incorrect data points.
**Why it happens:** Only months with transactions produce entries. January-to-December iteration must handle months with zero revenue.
**How to avoid:** Initialize all 12 months to zero, then accumulate. Only show months up to the current month (or all 12 if desired as a trailing-zero view).
**Warning signs:** Chart line jumping or months missing from x-axis labels.

### Pitfall 3: Chart.js JSON Escaping in data-chart Attribute
**What goes wrong:** JSON with special characters (quotes, ampersands) breaks the HTML attribute.
**Why it happens:** Jinja2 auto-escaping converts `"` to `&quot;` inside attributes, which is correct for HTML but can cause issues if not handled properly.
**How to avoid:** Use Jinja2's `|tojson` filter which produces valid JSON. Fava's Jinja2 environment has this built in. In the template: `data-chart='{{ data | tojson }}'`. The single-quote wrapping of the attribute avoids double-quote escaping issues.
**Warning signs:** `JSON.parse()` errors in console, `renderCharts()` silently skipping containers.

### Pitfall 4: Tax Owing KPI Complexity
**What goes wrong:** "Tax Owing" is ambiguous -- it could mean GST/QST net remittance, corporate income tax, or combined.
**Why it happens:** Multiple tax obligations exist for a Quebec CCPC.
**How to avoid:** Define "Tax Owing" as **GST/QST net remittance** only (sum of `Passifs:TPS-Percue` and `Passifs:TVQ-Percue` minus `Actifs:TPS-Payee` and `Actifs:TVQ-Payee`). This is what the sole operator needs to track most frequently. Corporate income tax is CPA territory.
**Warning signs:** Confusing or unexpectedly large numbers in the Tax Owing card.

### Pitfall 5: Template Name Must Match Class Name
**What goes wrong:** Fava cannot find the template and renders a blank page or error.
**Why it happens:** Fava discovers templates by looking for `templates/{ClassName}.html` relative to the extension's `__init__.py`.
**How to avoid:** Template file MUST be named `TableauBordExtension.html` to match the class `TableauBordExtension`.
**Warning signs:** 500 error or blank content area when navigating to the extension.

### Pitfall 6: Expense Category Grouping Level
**What goes wrong:** Doughnut chart has 30+ tiny slices, unreadable.
**Why it happens:** Beancount chart of accounts has ~30 expense accounts at leaf level.
**How to avoid:** Group by second-level category (e.g., "Salaires", "Bureau", "Vehicule", "Honoraires-Professionnels", "Assurances"). Take top 6 categories by amount, group remainder into "Autres".
**Warning signs:** Too many legend items, colors becoming indistinguishable.

## Code Examples

Verified patterns from existing codebase:

### Computing Revenue and Expenses YTD
```python
# Source: compteqc/mcp/tools/ledger.py etat_resultats()
# Adapted for dashboard KPI computation
import datetime
from decimal import Decimal
from beancount.core import data

def _compute_kpis(self) -> None:
    annee = datetime.date.today().year
    debut = datetime.date(annee, 1, 1)
    fin = datetime.date.today()

    revenus = Decimal("0")
    depenses = Decimal("0")

    for entry in self.ledger.all_entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date < debut or entry.date > fin:
            continue
        for posting in entry.postings:
            if posting.units is None:
                continue
            if posting.account.startswith("Revenus"):
                revenus -= posting.units.number  # negate (credits are negative)
            elif posting.account.startswith("Depenses"):
                depenses += posting.units.number

    # Pending approvals count
    from compteqc.mcp.services import lister_pending
    pending = lister_pending(self.ledger.all_entries)

    # Tax owing = GST/QST net
    from compteqc.mcp.services import calculer_soldes
    soldes = calculer_soldes(self.ledger.all_entries)
    tps_percue = abs(soldes.get("Passifs:TPS-Percue", Decimal("0")))
    tvq_percue = abs(soldes.get("Passifs:TVQ-Percue", Decimal("0")))
    tps_payee = soldes.get("Actifs:TPS-Payee", Decimal("0"))
    tvq_payee = soldes.get("Actifs:TVQ-Payee", Decimal("0"))
    taxes_dues = (tps_percue + tvq_percue) - (tps_payee + tvq_payee)

    self._kpis = {
        "revenus_ytd": revenus,
        "depenses_ytd": depenses,
        "resultat_net": revenus - depenses,
        "taxes_dues": taxes_dues,
        "pending_count": len(pending),
    }
```

### Monthly Revenue Series for Line Chart
```python
# Source: Pattern from etat_resultats, adapted for monthly bucketing
MOIS_FR = ["Jan", "Fev", "Mar", "Avr", "Mai", "Jun",
           "Jul", "Aou", "Sep", "Oct", "Nov", "Dec"]

def _compute_revenus_mensuels(self) -> None:
    annee = datetime.date.today().year
    mensuels = [Decimal("0")] * 12

    for entry in self.ledger.all_entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date.year != annee:
            continue
        for posting in entry.postings:
            if posting.units and posting.account.startswith("Revenus"):
                mensuels[entry.date.month - 1] -= posting.units.number

    mois_courant = datetime.date.today().month
    self._revenus_mensuels = {
        "labels": MOIS_FR[:mois_courant],
        "datasets": [{
            "label": "Revenus",
            "data": [float(m) for m in mensuels[:mois_courant]],
        }],
    }
```

### Expense Category Doughnut Data
```python
def _compute_depenses_categories(self) -> None:
    annee = datetime.date.today().year
    categories: dict[str, Decimal] = {}

    for entry in self.ledger.all_entries:
        if not isinstance(entry, data.Transaction):
            continue
        if entry.date.year != annee:
            continue
        for posting in entry.postings:
            if posting.units and posting.account.startswith("Depenses:"):
                # Group by second-level: "Depenses:Salaires:Brut" -> "Salaires"
                parts = posting.account.split(":")
                cat = parts[1] if len(parts) >= 2 else "Autres"
                categories[cat] = categories.get(cat, Decimal("0")) + posting.units.number

    # Sort by amount descending, take top 6, group rest as "Autres"
    sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    top = sorted_cats[:6]
    autres = sum(v for _, v in sorted_cats[6:], Decimal("0"))

    labels = [k for k, _ in top]
    values = [float(v) for _, v in top]
    if autres > 0:
        labels.append("Autres")
        values.append(float(autres))

    # Quebec-inspired color palette
    colors = [
        "#003DA5", "#1A5BBF", "#4A7FD4", "#7BA3E0",
        "#16A34A", "#EA580C", "#D97706", "#64748B"
    ]

    self._depenses_categories = {
        "labels": labels,
        "datasets": [{
            "data": values,
            "backgroundColor": colors[:len(labels)],
        }],
    }
```

### Template: KPI Card with data-value Animation
```html
<!-- Source: Phase 6 animateKPIs() spec + existing cqc-kpi pattern from TaxesQCExtension.html -->
<div class="cqc-kpi-row">
  <div class="cqc-kpi">
    <div class="cqc-kpi-label">Revenus YTD</div>
    <div class="cqc-kpi-value" data-value="{{ kpis.revenus_ytd }}" data-decimals="2" data-suffix=" $">
      {{ "{:,.2f}".format(kpis.revenus_ytd) }} $
    </div>
  </div>
  <!-- ... repeat for each KPI -->
</div>
```

### Template: Chart Container with data-chart
```html
<div class="cqc-chart-container"
     id="chart-revenus-mensuels"
     data-chart='{{ extension.revenus_mensuels_json() }}'
     data-chart-type="line">
  <canvas></canvas>
</div>
```

### Recent Transactions Query
```python
def _compute_transactions_recentes(self) -> None:
    from beancount.core import data
    transactions = [
        e for e in self.ledger.all_entries
        if isinstance(e, data.Transaction)
    ]
    # Last 10 by date
    transactions.sort(key=lambda e: e.date, reverse=True)
    recentes = []
    for txn in transactions[:10]:
        montant = Decimal("0")
        for p in txn.postings:
            if p.units and p.units.number > 0:
                montant += p.units.number
        statut = "pending" if txn.tags and "pending" in txn.tags else "ok"
        if txn.flag == "!":
            statut = "attention"
        recentes.append({
            "date": str(txn.date),
            "payee": txn.payee or "",
            "narration": txn.narration or "",
            "montant": montant,
            "statut": statut,
        })
    self._transactions_recentes = recentes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate chart JS per page | Shared `renderCharts()` via `[data-chart]` discovery | Phase 6 (this project) | No per-page JS needed; charts are data-driven from HTML attributes |
| CountUp.js library | Custom rAF animation via `animateKPIs()` | Phase 6 (this project) | Zero dependencies; `[data-value]` attributes drive animation |
| fava-dashboards plugin | Custom Fava extension | This project's architecture decision | Full control, no external plugin dependency, follows existing extension pattern |

**Deprecated/outdated:**
- fava-dashboards: Third-party plugin; not used here because CompteQC already has 9 custom extensions and a consistent pattern. Adding a different extension framework would fragment the architecture.

## Open Questions

1. **Dashboard position in sidebar navigation**
   - What we know: Extensions appear in sidebar in the order they are declared in `main.beancount`. Currently, theme_qc is first, then approbation, paie_qc, etc.
   - What's unclear: Should "Tableau de bord" appear first (before "File d'approbation") to serve as a landing page?
   - Recommendation: Declare `tableau_bord` as the first non-theme extension in `main.beancount` so it appears at the top of the sidebar. Users will naturally click it first.

2. **Fiscal year start**
   - What we know: Current code uses calendar year (Jan 1 - Dec 31). The CCPC's fiscal year end is Dec 31.
   - What's unclear: Is there ever a scenario where fiscal year differs from calendar year?
   - Recommendation: Hardcode calendar year for now. If fiscal year changes, it is a single constant to update.

3. **Dashboard as Fava default page**
   - What we know: Fava opens to the Income Statement page by default. Fava supports `default-page` option.
   - What's unclear: Whether setting `default-page` to the extension URL is supported.
   - Recommendation: Do not attempt to override Fava's default page. The dashboard is accessible via sidebar click. This avoids fragile Fava internals.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `src/compteqc/fava_ext/` -- 9 extensions following identical pattern (read directly)
- Existing codebase: `src/compteqc/mcp/services.py` -- `calculer_soldes()`, `lister_pending()` (read directly)
- Existing codebase: `src/compteqc/mcp/tools/ledger.py` -- `etat_resultats()` pattern for revenue/expense computation (read directly)
- Phase 6 plan: `.planning/phases/06-design-system-foundation/06-01-PLAN.md` -- `renderCharts()`, `animateKPIs()`, `[data-chart]`, `[data-value]` specifications (read directly)
- Fava extension base: `.venv/.../fava/ext/__init__.py` -- `FavaExtensionBase`, template discovery, `extension_endpoint` (read directly)
- Beancount chart of accounts: `ledger/comptes.beancount` -- all account names and structure (read directly)

### Secondary (MEDIUM confidence)
- [Chart.js Doughnut Documentation](https://www.chartjs.org/docs/latest/charts/doughnut.html) -- cutout, radius, rotation, animation options
- [Chart.js Line Chart Documentation](https://www.chartjs.org/docs/latest/charts/line.html) -- tension, point styles, scales
- [Fava Extension Help](https://fava.pythonanywhere.com/example-beancount-file/help/extensions) -- extension registration and template naming

### Tertiary (LOW confidence)
- None. All critical findings verified from codebase or official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Using exact same Fava extension pattern as 9 existing extensions; zero new dependencies
- Architecture: HIGH -- Python backend + Jinja2 template + Phase 6 JS infrastructure; all three layers are proven in this codebase
- Pitfalls: HIGH -- Sign convention, template naming, JSON escaping all verified from existing code; expense grouping logic straightforward
- Chart.js integration: HIGH -- Phase 6 plan specifies exact `[data-chart]` contract; dashboard just needs to emit correct JSON

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable -- no external dependency changes expected)
