# Coding Conventions

**Analysis Date:** 2026-02-25

## Language

All source code is **French**. Module docstrings, variable names, function names, class names, field names, error messages, and CLI help text are written in French. This is a deliberate project-wide decision reflecting the Quebec context of the application. English is used only in comments that clarify algorithmic details (e.g., score formulas) or in test docstrings that reference English regulatory terms (T2, T4, QPP, etc.).

## Naming Patterns

**Files:**
- snake_case for all `.py` files: `normalisation.py`, `rbc_cheques.py`, `balance_verification.py`
- Descriptive French names matching the domain: `generateur.py`, `calendrier.py`, `cotisations.py`

**Modules/Packages:**
- All lowercase, French, single-word or underscore-separated: `compteqc`, `categorisation`, `echeances`, `factures`, `rapports`

**Classes:**
- PascalCase, French nouns: `TransactionNormalisee`, `MoteurRegles`, `ConfigRegles`, `ResultatCategorisation`, `TauxAnnuels`, `Correspondance`
- Pydantic models named as nouns: `ConditionRegle`, `Regle`, `ConfigRegles`
- Frozen dataclasses for immutable domain objects: `TauxQPP`, `TauxAnnuels`, `TrancheFederale`

**Functions:**
- snake_case, French verb phrases: `charger_regles()`, `nettoyer_beneficiaire()`, `calculer_echeances()`, `proposer_correspondances()`, `obtenir_taux()`
- Private helpers prefixed with `_`: `_rejeter_float()`, `_ajuster_jour_ouvrable()`, `_find_echeance()`

**Variables:**
- snake_case, French nouns: `chemin_main`, `comptes_valides`, `regles_compilees`, `date_recu`, `score_montant`
- Loop variables use short French names: `nom`, `regle`, `compte`, `tranche`, `e`, `i`

**Constants:**
- UPPER_SNAKE_CASE: `TAUX_2026`, `TAUX`, `COMPTES_VALIDES`, `FIXTURES`, `LEDGER_DIR`

**Type Aliases:**
- PascalCase: `MontantDecimal = Annotated[Decimal, BeforeValidator(_rejeter_float)]`

## Mandatory `from __future__ import annotations`

Every module begins with `from __future__ import annotations`. This is a project-wide convention in all source files and test files.

## No Float for Monetary Values

A hard rule enforced at the Pydantic model level via `BeforeValidator`:

```python
# src/compteqc/models/transaction.py
def _rejeter_float(v: Any) -> Any:
    """Refuse les float pour forcer l'utilisation de Decimal ou str."""
    if isinstance(v, float):
        raise ValueError(
            "Les montants doivent etre Decimal ou str, jamais float. "
            "Utilisez Decimal('100.00') ou '100.00'."
        )
    return v

MontantDecimal = Annotated[Decimal, BeforeValidator(_rejeter_float)]
```

All monetary amounts use `Decimal` with string literals: `Decimal("0.053")`, `Decimal("3500")`. Never `float`. All rate/tax dataclasses (`TauxQPP`, `TauxRQAP`, `TauxAE`, etc.) in `src/compteqc/quebec/rates.py` use `Decimal` for every numeric field.

## Frozen Dataclasses for Domain Constants

Immutable domain objects use `@dataclass(frozen=True)`:

```python
# src/compteqc/quebec/rates.py
@dataclass(frozen=True)
class TauxQPP:
    taux_base: Decimal
    taux_supplementaire_1: Decimal
    ...
```

## Pydantic v2 for Data Models

All data transfer objects and configuration use `pydantic.BaseModel` with explicit `Field()` descriptors:

```python
# src/compteqc/categorisation/regles.py
class Regle(BaseModel):
    nom: str = Field(description="Nom unique de la regle")
    condition: ConditionRegle = Field(description="Conditions pour que la regle s'applique")
    compte: str = Field(description="Compte Beancount cible")
    confiance: float = Field(default=0.9, ge=0.0, le=1.0, description="Niveau de confiance")
```

Use `model_validate()` (Pydantic v2 API), not `parse_obj()`.

## Module-Level Logger

Every module that logs uses `logging.getLogger(__name__)` at module level:

```python
# src/compteqc/categorisation/moteur.py
import logging
logger = logging.getLogger(__name__)
```

Log calls use `%`-style formatting: `logger.warning("Regle '%s' pointe vers: '%s'", nom, compte)`. No f-strings in log calls.

## Import Organization

```python
from __future__ import annotations   # 1. Future

import datetime                       # 2. Standard library
import re
from decimal import Decimal
from pathlib import Path

import yaml                           # 3. Third-party
from pydantic import BaseModel, Field

from compteqc.models.transaction import TransactionNormalisee  # 4. Internal
```

**`noqa` suppression** is used only for circular-import workarounds at module load time in `src/compteqc/cli/app.py` (late imports of subcommands) and `src/compteqc/mcp/server.py` (side-effect tool registration imports).

## Docstrings

Google-style docstrings in French with explicit `Args:`, `Returns:`, `Raises:` sections:

```python
def charger_regles(chemin: Path) -> ConfigRegles:
    """Charge les regles de categorisation depuis un fichier YAML.

    Args:
        chemin: Chemin du fichier YAML.

    Returns:
        Configuration des regles validee par Pydantic.

    Raises:
        ValueError: Si le YAML est invalide ou ne respecte pas le schema.
        FileNotFoundError: Si le fichier n'existe pas.
    """
```

Short single-sentence docstrings are used for simple utility functions.

## Error Handling

**Pattern: raise specific built-ins with French messages:**

```python
# FileNotFoundError for missing files
raise FileNotFoundError(f"Fichier de regles introuvable: {chemin}")

# ValueError for invalid data/config
raise ValueError(f"Fichier de regles invalide ({chemin}): {e}") from e

# ValueError for missing domain data
raise ValueError(
    f"Taux non disponibles pour l'annee {annee}. "
    f"Annees disponibles: {sorted(TAUX.keys())}"
)
```

**Silent degradation with logging** for non-fatal rule errors:

```python
logger.warning("Regex invalide pour regle '%s' (payee): %s", regle.nom, e)
continue  # skip the bad rule, keep processing
```

**Exception chaining** is used when re-raising: `raise ValueError(...) from e`.

**Subprocess timeout** is always specified for external tool calls: `timeout=30`.

## Return Types

Functions always return explicit types. Tuples use the `tuple[bool, list[str]]` form (no `Tuple` from `typing`). Union types use the `X | Y` syntax (Python 3.10+ style, enabled by `from __future__ import annotations`).

## Code Style

**Formatter/Linter:** Ruff (`pyproject.toml`)
- Line length: 100 characters
- Target: Python 3.12
- Enabled rules: E (pycodestyle), F (pyflakes), I (isort), W (warnings)

**No Black** — Ruff handles formatting exclusively.

## Path Handling

All file paths use `pathlib.Path`. String paths appear only when calling external tools that require them (e.g., `subprocess.run`, `beancount.loader.load_file(str(path))`).

## Lazy Imports for Heavy Dependencies

Heavy optional dependencies are imported inside functions to avoid slowing down module load:

```python
# src/compteqc/documents/matching.py
def proposer_correspondances(...):
    from beancount.core import data as beancount_data  # lazy import
    ...

# src/compteqc/factures/generateur.py
def generer_pdf(...):
    import weasyprint  # lazy import
    ...
```

## Constants and Configuration Registries

Fiscal year constants are defined as top-level module constants and stored in a `dict` registry for multi-year lookup:

```python
# src/compteqc/quebec/rates.py
TAUX_2026 = TauxAnnuels(annee=2026, ...)
TAUX: dict[int, TauxAnnuels] = {2026: TAUX_2026}
```

---

*Convention analysis: 2026-02-25*
