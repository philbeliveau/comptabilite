# Phase 3: AI Categorization and Review Workflow - Research

**Researched:** 2026-02-19
**Domain:** ML/LLM categorization pipeline, confidence scoring, staging/approval workflow
**Confidence:** HIGH

## Summary

Phase 3 adds two AI tiers (ML via smart_importer, LLM via Anthropic Claude) on top of the existing rule-based categorizer, plus a pending-transaction staging workflow with CLI-based approval. The existing codebase has a clean `MoteurRegles` engine producing `ResultatCategorisation(compte, confiance, source, regle)` and an `appliquer_categorisation` function that creates immutable Transaction instances. The new pipeline must extend this to cascade: rules -> ML -> LLM, where each tier only processes the previous tier's leftovers.

A critical finding is that **smart_importer's SVC(kernel="linear") does NOT provide probability/confidence scores** -- it uses hard classification only. To get confidence scores for the ML tier, we must subclass `EntryPredictor` and override `define_pipeline()` to use `SVC(kernel="linear", probability=True)` which enables Platt scaling for `predict_proba()`, or replace SVC with `SGDClassifier(loss="log_loss")` which natively supports probabilities. The LLM tier is straightforward: the Anthropic Python SDK (`anthropic>=0.82`) provides `client.messages.parse()` with Pydantic models for structured output, making it easy to constrain Claude to the closed chart of accounts and extract a confidence score.

**Primary recommendation:** Build a three-tier `PipelineCategorisation` orchestrator that wraps the existing `MoteurRegles`, a custom `PredicteurML` (subclassed from smart_importer's `EntryPredictor` with probability support), and a new `ClassificateurLLM` using Anthropic's structured output. All results flow into a unified `ResultatCategorisation` with source tags. Transactions below thresholds go to `pending.beancount` with `#pending` tag; CLI commands handle batch review.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Pipeline tiers & handoff
- Categorization runs at import time -- every transaction goes through the full pipeline during import, not as a separate step
- Pipeline order: rules first, ML (smart_importer) second, LLM (Claude) third -- each tier only processes what the previous couldn't handle
- Skip ML tier if untrained -- during cold start, uncategorized transactions go directly from rules to LLM; smart_importer activates once sufficient corrected data accumulates
- LLM receives rich context: the transaction itself, chart of accounts with descriptions, recent similar categorized transactions, and vendor history -- accuracy over token cost (volume is low)
- LLM proposes account classification only (expense/revenue account, CAPEX vs OPEX flag) -- GST/QST legs are calculated deterministically by the Phase 2 tax module, never by the LLM

#### Confidence & flagging
- Rule-engine results are implicitly 100% confident -- no score needed, auto-posted directly
- Three-tier confidence thresholds for ML/LLM results:
  - Below 80%: mandatory human review
  - 80-95%: posted to pending queue, review optional (can sample or focus on higher-risk items)
  - Above 95%: auto-approved and posted directly, visible in audit logs for later inspection
- Tier disagreement (ML says account A, LLM says account B) forces mandatory review regardless of individual confidence scores -- both suggestions shown side by side
- CAPEX detection uses amount + vendor/description patterns:
  - Configurable amount threshold (default $500)
  - Known vendor patterns (Apple, Dell, B&H, etc.) flag potential assets even below threshold
  - Always overridable (expense vs CAPEX)
  - Suggests CCA class when flagging

#### Approval workflow
- Batch review mode: table/list of pending transactions, select multiple to approve, reject, or recategorize
- Each row shows: proposed account + confidence score, source tier (rule/ml/llm), vendor history (last categorizations), CAPEX/flag indicators
- Approved transactions move directly to monthly ledger files (e.g. 2026-01.beancount), no intermediate staging
- Corrections accept optional notes (prompted but skippable) -- useful for later analysis

#### Feedback & learning
- Auto-generate rules silently after 2 identical corrections (same vendor -> same account twice = new rule created automatically)
- Smart_importer ML retraining is manual only -- user runs `cqc retrain` when they decide; no auto-retrain
- LLM prompt/response pairs stored for debugging and drift detection

### Claude's Discretion

- Pending queue filtering approach (by vendor, confidence range, date, etc.)
- LLM drift monitoring strategy (store prompt/response pairs, alerting approach)
- Exact batch review table layout and column ordering
- How to surface the 80-95% "optional review" items distinctly from <80% mandatory items

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAT-02 | smart_importer ML predicts account postings from historical data (handles ~20-25% of remainder) | smart_importer v1.2 provides `PredictPostings` with SVC classifier; must subclass `EntryPredictor` and override `define_pipeline()` for probability support |
| CAT-03 | Claude LLM categorizes remaining edge cases, constrained to closed chart of accounts list | Anthropic SDK `messages.parse()` with Pydantic model constrains output to valid accounts; structured output ensures schema compliance |
| CAT-04 | Every categorization has a confidence score and source tag (rule/ml/llm/human) | Existing `ResultatCategorisation` already has `confiance` and `source` fields; extend to support ml/llm/human source tags |
| CAT-05 | Transactions below 80% confidence are flagged for mandatory human review | Pipeline orchestrator applies threshold logic after each tier produces a result |
| CAT-06 | AI-categorized transactions go to pending.beancount staging file with #pending tag | Beancount supports tags on transactions (`#pending`); `pending.beancount` included in `main.beancount`; existing `ecrire_transactions` can write to it |
| CAT-07 | User can approve, reject, or recategorize pending transactions | New Typer CLI commands (`cqc reviser`) using Rich tables for batch review; reads/writes `pending.beancount` |
| CAT-08 | Approved transactions move from pending to monthly ledger files | Existing `chemin_fichier_mensuel` and `ecrire_transactions` handle writing to monthly files; remove `#pending` tag and move |
| CAT-09 | Transactions >$500 are auto-flagged as potential CAPEX with suggested CCA class | Phase 2 `CLASSES_DPA` dict provides CCA classes; CAPEX detection is amount threshold + vendor pattern matching |
| CAT-10 | User corrections feed back into rule engine (auto-generate rules after N identical corrections) | Track corrections in YAML/JSON store; after 2 identical vendor->account mappings, auto-append to `rules/categorisation.yaml` |
| CAT-11 | LLM categorizations stored with prompt/response for drift detection | Store as JSON lines file (`data/llm_log/categorisations.jsonl`) with timestamp, transaction hash, prompt, response, account, confidence |
| CLI-02 | User can run categorization pipeline via CLI command | Extend existing `cqc importer fichier` to include full pipeline, or add `cqc categoriser` command |
| CLI-03 | User can review and approve pending transactions via CLI | New `cqc reviser` command with Rich table, multi-select, approve/reject/recategorize actions |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| smart-importer | 1.2 | ML-based account prediction for Beancount | Only ML library purpose-built for Beancount; uses sklearn SVC under the hood; hooks into beangulp pipeline |
| anthropic | >=0.82 | Claude API client for LLM categorization | Official Python SDK; `messages.parse()` provides native Pydantic structured output; type-safe |
| scikit-learn | (transitive via smart-importer) | ML pipeline and classifiers | Industry standard; smart_importer already depends on it |
| pydantic | >=2 (already installed) | Structured output schemas for LLM responses | Already in project; used by Anthropic SDK's `messages.parse()` |
| typer | >=0.24 (already installed) | CLI commands for review workflow | Already used for `cqc` CLI |
| rich | (already installed) | Terminal tables for batch review display | Already used for import summaries |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | (already installed) | Read/write categorization rules | For auto-generated rules from corrections |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| smart_importer's SVC | Custom sklearn pipeline from scratch | smart_importer handles Beancount data wrangling, feature extraction, and training data loading; reimplementing this is ~500 lines for marginal benefit |
| Anthropic structured output | Tool use / function calling | `messages.parse()` with Pydantic is cleaner than tool_use for single-classification tasks; both work but parse() is more direct |
| SVC with probability=True | SGDClassifier(loss="log_loss") | SGD trains faster on large data, native probability; SVC with Platt scaling is slower but more accurate on small datasets -- SVC better for this use case (~200-500 transactions) |

**Installation:**
```bash
uv add smart-importer anthropic
```

## Architecture Patterns

### Recommended Project Structure
```
src/compteqc/
  categorisation/
    __init__.py          # appliquer_categorisation (existing)
    moteur.py            # MoteurRegles (existing rule engine)
    regles.py            # ConfigRegles, charger_regles (existing)
    pipeline.py          # NEW: PipelineCategorisation orchestrator
    ml.py                # NEW: PredicteurML (smart_importer wrapper with confidence)
    llm.py               # NEW: ClassificateurLLM (Anthropic Claude)
    capex.py             # NEW: CAPEX detector (amount + vendor patterns)
    feedback.py          # NEW: correction tracking, auto-rule generation
    pending.py           # NEW: pending.beancount read/write/move operations
  cli/
    reviser.py           # NEW: batch review CLI commands
data/
  llm_log/
    categorisations.jsonl  # NEW: LLM prompt/response log
  corrections/
    historique.json        # NEW: correction history for auto-rule generation
```

### Pattern 1: Pipeline Orchestrator
**What:** A `PipelineCategorisation` class that takes a transaction and cascades through tiers.
**When to use:** Every import; replaces direct `appliquer_categorisation` calls.
**Example:**
```python
from dataclasses import dataclass
from decimal import Decimal
from compteqc.categorisation.moteur import MoteurRegles, ResultatCategorisation

@dataclass(frozen=True)
class ResultatPipeline:
    """Extended result with multi-tier support."""
    compte: str
    confiance: float
    source: str  # "regle" | "ml" | "llm" | "non-classe"
    regle: str | None = None
    capex: bool = False
    classe_dpa: int | None = None
    suggestions_alternatives: list[tuple[str, float]] | None = None
    # ML and LLM may both have suggestions when they disagree
    ml_suggestion: str | None = None
    llm_suggestion: str | None = None

class PipelineCategorisation:
    def __init__(
        self,
        moteur_regles: MoteurRegles,
        predicteur_ml: "PredicteurML | None",
        classificateur_llm: "ClassificateurLLM | None",
        detecteur_capex: "DetecteurCAPEX",
    ):
        self._regles = moteur_regles
        self._ml = predicteur_ml
        self._llm = classificateur_llm
        self._capex = detecteur_capex

    def categoriser(self, payee, narration, montant) -> ResultatPipeline:
        # Tier 1: Rules
        r = self._regles.categoriser(payee, narration, montant)
        if r.source == "regle":
            capex_info = self._capex.verifier(montant, payee, narration)
            return ResultatPipeline(
                compte=r.compte, confiance=1.0, source="regle",
                regle=r.regle, capex=capex_info.est_capex,
                classe_dpa=capex_info.classe_suggeree,
            )

        # Tier 2: ML (skip if untrained)
        ml_result = None
        if self._ml and self._ml.est_entraine:
            ml_result = self._ml.predire(payee, narration, montant)

        # Tier 3: LLM
        llm_result = None
        if self._llm:
            llm_result = self._llm.classifier(payee, narration, montant)

        # Resolution logic: handle agreement, disagreement, single-tier
        return self._resoudre(ml_result, llm_result, montant, payee, narration)
```

### Pattern 2: smart_importer Subclass with Probability
**What:** Override `define_pipeline()` to enable confidence scoring.
**When to use:** For the ML tier.
**Example:**
```python
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC
from sklearn.feature_extraction.text import CountVectorizer
from smart_importer.predictor import EntryPredictor

class PredicteurAvecConfiance(EntryPredictor):
    """smart_importer predictor that provides probability scores."""

    weights = {"narration": 1.0, "payee": 0.8}

    def define_pipeline(self):
        """Override to use SVC with probability=True."""
        from sklearn.pipeline import FeatureUnion
        transformers = [
            (attribute, self.get_pipeline(attribute))
            for attribute in self.weights
        ]
        self.pipeline = make_pipeline(
            FeatureUnion(
                transformer_list=transformers,
                transformer_weights=self.weights,
            ),
            SVC(kernel="linear", probability=True),
        )

    def predire_avec_confiance(self, payee: str, narration: str) -> tuple[str, float]:
        """Predict account with confidence score."""
        # Build feature dict and use pipeline.predict_proba
        probas = self.pipeline.predict_proba([features])
        best_idx = probas[0].argmax()
        return self.pipeline.classes_[best_idx], probas[0][best_idx]
```

### Pattern 3: Anthropic Structured Output for Classification
**What:** Use `messages.parse()` with a Pydantic model to constrain LLM to valid accounts.
**When to use:** For the LLM tier.
**Example:**
```python
import anthropic
from pydantic import BaseModel, Field
from typing import Literal

class ResultatClassificationLLM(BaseModel):
    """Schema for LLM classification response."""
    compte: str = Field(description="Beancount account from chart of accounts")
    confiance: float = Field(ge=0.0, le=1.0, description="Confidence 0-1")
    raisonnement: str = Field(description="Brief explanation of classification")
    est_capex: bool = Field(default=False, description="Whether this is a capital expenditure")

def classifier_transaction(
    client: anthropic.Anthropic,
    payee: str,
    narration: str,
    montant: str,
    comptes_valides: list[str],
    historique_vendeur: list[dict],
) -> ResultatClassificationLLM:
    prompt = f"""Classify this transaction into one of the valid accounts.

Transaction:
- Payee: {payee}
- Description: {narration}
- Amount: {montant} CAD

Valid accounts:
{chr(10).join(f'- {c}' for c in comptes_valides)}

Recent similar transactions by this vendor:
{historique_vendeur}

Rules:
- Choose ONLY from the valid accounts listed above
- Set est_capex=true if this looks like a capital asset purchase (computer, furniture, etc.)
- Provide a confidence between 0.0 and 1.0
"""

    result = client.messages.parse(
        model="claude-sonnet-4-5-20250929",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
        output_format=ResultatClassificationLLM,
    )
    return result.parsed_output
```

### Pattern 4: Pending File Management
**What:** Use a dedicated `pending.beancount` file with `#pending` tags; included in main.beancount.
**When to use:** For AI-categorized transactions awaiting review.
**Example:**
```python
from beancount.core import data
from beancount.parser import printer
from beancount import loader

def ecrire_pending(chemin_pending, transactions):
    """Write transactions to pending.beancount with #pending tag."""
    tagged = []
    for txn in transactions:
        new_tags = (txn.tags or frozenset()) | {"pending"}
        tagged.append(txn._replace(tags=frozenset(new_tags)))
    texte = "\n".join(printer.format_entry(t) for t in tagged)
    # Append to pending file
    ecrire_transactions(chemin_pending, texte)

def approuver_transactions(chemin_pending, chemin_main, ids_approuves):
    """Move approved transactions from pending to monthly files."""
    entries, _, _ = loader.load_file(str(chemin_pending))
    approuvees = []
    restantes = []
    for entry in entries:
        if isinstance(entry, data.Transaction) and _get_id(entry) in ids_approuves:
            # Remove #pending tag
            new_tags = entry.tags - {"pending"}
            approuvees.append(entry._replace(tags=frozenset(new_tags)))
        else:
            restantes.append(entry)
    # Write approved to monthly files
    # Rewrite pending with remaining
```

### Anti-Patterns to Avoid
- **LLM computing tax splits:** The LLM must ONLY propose account + CAPEX flag. GST/QST legs are always computed by Phase 2's `extraire_taxes()`. Never let the LLM propose dollar amounts.
- **Mutating existing transactions:** The codebase convention is immutable transformation via `_replace()` or new `data.Transaction()`. Never mutate in place.
- **Silent auto-approval:** Even >95% confidence transactions must be logged. The user decided auto-approval is OK above 95% but they must appear in audit logs.
- **Combining ML and LLM into one step:** The tiers must be sequential. Running both in parallel and "voting" was explicitly rejected -- cascade only.
- **Training ML on pending/unreviewed data:** ML must only train on approved, human-verified transactions. Never include #pending transactions in training data.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text feature extraction for ML | Custom TF-IDF pipeline | smart_importer's `EntryPredictor` base class | Handles Beancount-specific feature extraction, training data filtering, account denylisting |
| Structured LLM responses | JSON parsing with regex | Anthropic `messages.parse()` with Pydantic | Type-safe, schema-validated, handles retries on malformed output |
| Beancount file I/O | Custom parser/writer | `beancount.loader.load_file()` and `beancount.parser.printer.format_entry()` | Already used in codebase; handles all edge cases |
| CLI interactive tables | Custom terminal UI | Rich library (`Table`, `Prompt`, `Confirm`) | Already a dependency; handles terminal width, colors, pagination |
| Transaction deduplication | Custom hash logic | Existing dedup in importers | Already implemented in Phase 1 importers |

**Key insight:** The ML complexity is already handled by smart_importer + sklearn. The LLM complexity is handled by Anthropic's structured output. What we're really building is the **orchestration layer** (pipeline, thresholds, routing) and the **review workflow** (pending file, CLI approval, feedback loop).

## Common Pitfalls

### Pitfall 1: smart_importer Cold Start
**What goes wrong:** No training data means ML tier throws errors or produces garbage predictions.
**Why it happens:** smart_importer needs existing categorized transactions to train; a new ledger has none.
**How to avoid:** Check if training data exists before invoking ML tier. If `len(training_entries) < MIN_TRAINING_SIZE` (suggest 20), skip ML entirely and go straight to LLM. The pipeline must gracefully degrade.
**Warning signs:** Errors from sklearn about empty arrays or single-class training data.

### Pitfall 2: SVC probability=True Performance
**What goes wrong:** `SVC(probability=True)` uses Platt scaling via 5-fold cross-validation internally, which is slow on larger datasets.
**Why it happens:** Platt scaling fits a logistic regression on SVC decision values to produce probabilities.
**How to avoid:** For this use case (~200-500 transactions/year), performance is fine. If it becomes slow, switch to `SGDClassifier(loss="log_loss")` which provides native probabilities without cross-validation overhead. Set a hard timeout for the ML tier.
**Warning signs:** ML categorization taking >5 seconds per batch.

### Pitfall 3: LLM Hallucinating Accounts
**What goes wrong:** LLM returns an account name not in the chart of accounts, even when constrained.
**Why it happens:** Structured output constrains the schema shape but not enum values unless explicitly listed. Even with a list in the prompt, the LLM can invent slight variations.
**How to avoid:** Validate the returned `compte` against `comptes_valides` set AFTER receiving the LLM response. If invalid, fall back to "Depenses:Non-Classe" with low confidence. Consider passing accounts as an enum in the Pydantic model (using `Literal` with all values) for stronger enforcement.
**Warning signs:** LLM returns accounts like "Depenses:Bureau:Logiciels" (slight variation of actual "Depenses:Bureau:Abonnements-Logiciels").

### Pitfall 4: Pending File Growing Unbounded
**What goes wrong:** `pending.beancount` accumulates hundreds of transactions that are never reviewed.
**Why it happens:** User ignores review step; imports keep adding to pending.
**How to avoid:** Show pending count in import summary. Consider a warning threshold (e.g., >50 pending transactions triggers alert). The `cqc reviser` command should be discoverable.
**Warning signs:** `pending.beancount` file growing larger than monthly files.

### Pitfall 5: Race Condition in Auto-Rule Generation
**What goes wrong:** Two corrections for the same vendor happen in different sessions, but the rule counter doesn't persist between sessions.
**Why it happens:** Correction history stored only in memory.
**How to avoid:** Persist correction history to disk (`data/corrections/historique.json`). Load at startup, update after each correction, atomic write.
**Warning signs:** Rules not being auto-generated despite repeated identical corrections.

### Pitfall 6: Beancount v3 Tag Syntax
**What goes wrong:** Tags in Beancount v3 must be valid (alphanumeric, hyphens, no spaces). Using `#pending` is fine but `#pending_review` might have issues.
**Why it happens:** Beancount v3 has specific tag syntax rules.
**How to avoid:** Stick to simple alphanumeric tags: `#pending`, `#reviewed`, `#capex`. Test tag round-tripping (write then read back).
**Warning signs:** `bean-check` errors about invalid tag format.

## Code Examples

### Existing ResultatCategorisation (current codebase)
```python
# Source: src/compteqc/categorisation/moteur.py
@dataclass(frozen=True)
class ResultatCategorisation:
    compte: str
    confiance: float
    regle: str | None
    source: str  # "regle" ou "non-classe"
```
This must be extended to support "ml", "llm", "human" sources plus CAPEX metadata.

### Anthropic Structured Output with Pydantic
```python
# Source: Context7 /anthropics/anthropic-sdk-python
import pydantic
import anthropic

class Classification(pydantic.BaseModel):
    compte: str
    confiance: float
    raisonnement: str

client = anthropic.Anthropic()
parsed = client.messages.parse(
    model="claude-sonnet-4-5-20250929",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=256,
    output_format=Classification,
)
result = parsed.parsed_output  # type: Classification
```

### smart_importer Hook Pattern
```python
# Source: Context7 /beancount/smart_importer
from smart_importer import PredictPostings

predictor = PredictPostings(
    denylist_accounts=['Depenses:Non-Classe']
)
# Use as beangulp hook or standalone
```

### Beancount Transaction with Tags
```python
# Source: Context7 /websites/beancount_github_io_index
# Tags are frozenset of strings on Transaction
txn = data.Transaction(
    meta=meta, date=date, flag="!", payee="Vendor",
    narration="Purchase", tags=frozenset({"pending"}),
    links=frozenset(), postings=postings,
)
# Rendered as: 2026-01-15 ! "Vendor" "Purchase" #pending
```

### Auto-Rule Generation from Corrections
```python
# Pattern: track corrections, auto-generate after threshold
import json
from pathlib import Path

def enregistrer_correction(
    historique_path: Path,
    vendeur: str,
    compte_corrige: str,
    seuil: int = 2,
) -> Regle | None:
    """Track correction and auto-generate rule if threshold met."""
    historique = json.loads(historique_path.read_text()) if historique_path.exists() else {}

    cle = vendeur.upper().strip()
    entry = historique.setdefault(cle, {})
    entry.setdefault(compte_corrige, 0)
    entry[compte_corrige] += 1

    historique_path.write_text(json.dumps(historique, indent=2))

    if entry[compte_corrige] >= seuil:
        # Generate rule
        return Regle(
            nom=f"auto-{cle[:20].lower().replace(' ', '-')}",
            condition=ConditionRegle(payee=re.escape(cle)),
            compte=compte_corrige,
            confiance=0.9,
        )
    return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| smart_importer with beancount v2 | smart_importer v1.2 supports beangulp hooks (beancount v3) | 2025 | Must use hook/wrap pattern, not old extract-based API |
| Anthropic tool_use for structured data | `messages.parse()` with Pydantic output_format | Nov 2025 (structured-outputs-2025-11-13 beta) | Cleaner than tool_use; native Pydantic support |
| Manual JSON schema for Claude | Pydantic model auto-converted to JSON schema | Nov 2025 | Less boilerplate, type-safe responses |

**Deprecated/outdated:**
- smart_importer's old `bean-extract` CLI pattern: replaced by beangulp hooks in v1.2
- Anthropic's `completion` API: fully replaced by `messages` API

## Claude's Discretion Recommendations

### Pending Queue Filtering
**Recommendation:** Filter by three axes: confidence band (mandatory <80%, optional 80-95%), date range, and vendor substring. Use Rich's `Prompt.ask()` for filter input. Default view shows mandatory-review items first, then optional items separated by a visual divider.

### LLM Drift Monitoring
**Recommendation:** Store all LLM categorizations as JSONL with fields: `timestamp`, `transaction_hash`, `prompt_hash`, `model`, `response`, `compte`, `confiance`, `tokens_used`. For drift detection, a simple monthly report comparing account distribution (LLM vs rules+ML) is sufficient at this volume. No alerting needed yet -- manual `cqc drift-rapport` command.

### Batch Review Table Layout
**Recommendation:** Table columns in order:
1. `#` (row index for selection)
2. `Date`
3. `Montant` (right-aligned, colored red for debits)
4. `Beneficiaire` (truncated to 25 chars)
5. `Compte propose` (the AI's suggestion)
6. `Conf.` (confidence %, colored by band: red <80%, yellow 80-95%, green >95%)
7. `Source` (rule/ml/llm)
8. `Flags` (CAPEX indicator if applicable)

Mandatory review items (<80%) shown first with `[red]` styling. Optional review items (80-95%) shown below a separator. Auto-approved items (>95%) not shown in review but logged.

### Surfacing Optional vs Mandatory Review
**Recommendation:** Use visual separation and color coding:
- Mandatory (<80%): Red confidence, `!` flag on transaction, listed first
- Optional (80-95%): Yellow confidence, listed after a `---` separator, can be bulk-approved with `cqc reviser --approuver-optionnel`
- Auto-approved (>95%): Not in review table; visible via `cqc reviser --journal` audit log

## Open Questions

1. **smart_importer minimum training size**
   - What we know: sklearn SVC needs at least 2 classes with multiple samples each to train
   - What's unclear: The exact minimum for useful predictions in this domain
   - Recommendation: Set MIN_TRAINING_SIZE = 20 transactions (configurable). Test with real data and adjust. Log training data stats on each run.

2. **Anthropic API key management**
   - What we know: The SDK reads `ANTHROPIC_API_KEY` from environment by default
   - What's unclear: Whether to also support config file for the key
   - Recommendation: Use environment variable only (`ANTHROPIC_API_KEY`). If missing, skip LLM tier with a warning (graceful degradation, like ML cold start).

3. **Concurrent pending.beancount writes**
   - What we know: Only one user (solo consultant), imports are sequential
   - What's unclear: Whether Beancount's `load_file` handles partially written files
   - Recommendation: Use atomic write pattern (write to temp file, then rename). Low risk given single-user scenario.

4. **smart_importer v1.2 compatibility with Beancount v3**
   - What we know: v1.2 supports beangulp hooks and Python 3.12
   - What's unclear: Whether `PredictPostings` works standalone (outside beangulp extract flow) for our custom pipeline
   - Recommendation: Test during implementation. Fallback: use `EntryPredictor` base class directly and bypass `PredictPostings` wrapper. The `define_pipeline()` and training logic can be used independently.

## Sources

### Primary (HIGH confidence)
- Context7 `/beancount/smart_importer` - PredictPostings API, EntryPredictor base class, hooks/wrap patterns, feature weights, denylist
- Context7 `/anthropics/anthropic-sdk-python` - `messages.parse()`, Pydantic structured output, tool definitions
- Context7 `/websites/beancount_github_io_index` - Transaction tags, metadata, data model API
- [smart_importer source code](https://github.com/beancount/smart_importer) - EntryPredictor.define_pipeline() uses hardcoded `SVC(kernel="linear")` without probability support
- [smart-importer on PyPI](https://pypi.org/project/smart-importer/) - v1.2, released 2025-10-17, supports Python 3.9-3.13
- [anthropic on PyPI](https://pypi.org/project/anthropic/) - v0.82.0, released 2026-02-18

### Secondary (MEDIUM confidence)
- [Anthropic structured output docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - messages.parse() with Pydantic output_format
- [sklearn SVC predict_proba](https://www.geeksforgeeks.org/machine-learning/understanding-the-predictproba-function-in-scikit-learns-svc/) - Platt scaling for probability estimation

### Tertiary (LOW confidence)
- Beancount pending file pattern: No official documentation found for a "pending.beancount" staging pattern. This is a custom convention that will need to be implemented and tested. The `#pending` tag approach is well-supported by Beancount's tag system.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries verified via Context7 and PyPI; versions confirmed current
- Architecture: HIGH - pipeline pattern is straightforward; existing codebase conventions are clear and well-tested
- Pitfalls: HIGH - smart_importer's lack of probability support is verified from source code; LLM hallucination is well-documented; cold start is inherent to ML
- Smart_importer standalone usage: MEDIUM - needs testing whether EntryPredictor can be used outside beangulp flow

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (30 days -- stable domain, libraries not fast-moving)
