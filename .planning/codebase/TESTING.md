# Testing Patterns

**Analysis Date:** 2026-02-25

## Test Framework

**Runner:**
- pytest (version from `pyproject.toml` dev group — no version pin)
- Config: `pyproject.toml` `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in `assert` statements (no third-party assertion library)

**Supporting packages:**
- `pytest-cov` — coverage reporting
- `freezegun` — freeze `datetime.date.today()` / `datetime.datetime.now()` in scheduling tests
- `unittest.mock` (stdlib) — patching external API calls (OpenAI, Anthropic, filesystem)

**Run Commands:**
```bash
uv run pytest                          # Run all tests
uv run pytest tests/test_rates.py      # Run a single file
uv run pytest -k "TestQPP"             # Run tests matching a pattern
uv run pytest --cov=src/compteqc       # Run with coverage
uv run pytest --co -q                  # Collect without running (dry-run)
```

Total tests collected: **521** (as of 2026-02-25).

## Test File Organization

**Location:** All tests in the top-level `tests/` directory (not co-located with source).

**Naming:** `test_{module_name}.py` matching the source module being tested:
- `src/compteqc/quebec/rates.py` → `tests/test_rates.py`
- `src/compteqc/categorisation/moteur.py` → `tests/test_categorisation.py`
- `src/compteqc/ingestion/rbc_cheques.py` → `tests/test_importers.py`
- `src/compteqc/ledger/validation.py` → `tests/test_ledger.py`
- `src/compteqc/mcp/server.py` → `tests/test_mcp_server.py`

**Fixtures data:** `tests/fixtures/` contains real-format sample files:
- `tests/fixtures/rbc_cheques_sample.csv`
- `tests/fixtures/rbc_carte_sample.csv`
- `tests/fixtures/rbc_combined_sample.csv`
- `tests/fixtures/rbc_real_sample.csv`
- `tests/fixtures/rbc_sample.ofx`

```
tests/
├── __init__.py
├── fixtures/
│   ├── rbc_cheques_sample.csv
│   ├── rbc_carte_sample.csv
│   ├── rbc_combined_sample.csv
│   ├── rbc_real_sample.csv
│   └── rbc_sample.ofx
├── test_categorisation.py
├── test_cotisations.py
├── test_rates.py
├── test_importers.py
├── test_ledger.py
├── test_mcp_server.py
└── ... (25 test files total)
```

## Test Structure

**Suite Organization:** Tests are grouped into classes by domain concept, even when there is no state shared between tests. One file typically contains multiple classes:

```python
# tests/test_rates.py
class TestObtenirTaux:
    """Tests pour la fonction obtenir_taux."""
    def test_obtenir_taux_2026_retourne_taux_annuels(self) -> None: ...
    def test_obtenir_taux_annee_non_disponible_leve_erreur(self) -> None: ...

class TestTauxQPP:
    """Tests des taux QPP 2026."""
    def test_qpp_taux_base(self) -> None: ...

class TestImmutabilite:
    """Tests que les dataclasses sont immuables (frozen)."""
    def test_taux_annuels_immutable(self) -> None: ...

class TestAucunFloat:
    """Verifie qu'aucune valeur n'est un float."""
    def test_tous_les_taux_sont_decimal(self) -> None: ...
```

**Return type annotations** are used on all test methods: `def test_foo(self) -> None:`

**Section separators** use comments: `# ---------------------------------------------------------------------------` to visually divide test groups within a file.

**Helper factories** at module level, prefixed with `_`:

```python
# tests/test_categorisation.py
def _creer_moteur_avec_regles() -> MoteurRegles:
    """Cree un moteur avec quelques regles de test."""
    config = ConfigRegles(regles=[...])
    return MoteurRegles(config, COMPTES_VALIDES)

def _creer_transaction(payee: str, narration: str, montant: Decimal) -> data.Transaction:
    """Helper pour creer une transaction de test."""
    ...
```

**Docstrings** on test methods document the exact calculation being verified:

```python
def test_calcul_normal(self, taux_2026, salaire_bihebd) -> None:
    """$2,307.69 - ($3,500/26 = $134.62) = $2,173.07 * 0.053 = $115.17."""
    result = calculer_qpp_base_employe(...)
    assert result == Decimal("115.17")
```

## Fixtures

**Module-level constants** for shared test inputs:

```python
# tests/test_categorisation.py
RULES_DIR = Path(__file__).parent.parent / "rules"
COMPTES_VALIDES = {
    "Depenses:Non-Classe",
    "Depenses:Bureau:Internet-Telecom",
    ...
}
```

**pytest fixtures** for domain objects and temporary resources:

```python
# tests/test_cotisations.py
@pytest.fixture
def taux_2026():
    return obtenir_taux(2026)

@pytest.fixture
def salaire_bihebd() -> Decimal:
    """Salaire brut bi-hebdomadaire pour $60,000 annuel."""
    return Decimal("2307.69")
```

**Fixtures for file-based tests** use `tmp_path` (built-in pytest) extensively:

```python
# tests/test_importers.py
@pytest.fixture
def importer(self):
    return RBCChequesImporter()
```

**Inline fixture definitions** with `@pytest.fixture` inside test classes are used for importer tests.

**`tmp_path`-based isolated ledgers** for CLI and git integration tests:

```python
# tests/test_cli.py
@pytest.fixture
def ledger_tmp(tmp_path):
    """Cree un ledger temporaire isole dans tmp_path."""
    ledger_dir = tmp_path / "ledger"
    shutil.copy(PROJECT_ROOT / "ledger" / "main.beancount", ledger_dir / "main.beancount")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    ...
    return tmp_path
```

**Inline Beancount ledger strings** for MCP/service tests:

```python
# tests/test_mcp_server.py
LEDGER_SIMPLE = """\
option "name_assets" "Actifs"
...
2026-01-15 * "Client ABC" "Facture consultation janvier"
  Actifs:Banque:Desjardins  5000.00 CAD
  Revenus:Consultation      -5000.00 CAD
"""

def _parse(text: str) -> list:
    entries, errors, options = beancount_parser.parse_string(text)
    return entries
```

## Mocking

**Framework:** `unittest.mock` (`MagicMock`, `patch`) from stdlib.

**LLM API calls are always mocked.** Never make real API calls in tests:

```python
# tests/test_llm.py
def _make_mock_response(compte: str, confiance: float, raisonnement: str, est_capex: bool = False):
    """Cree un mock de reponse OpenAI ChatCompletion."""
    content_json = json.dumps({...})
    message = MagicMock()
    message.content = content_json
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    response.usage = MagicMock(prompt_tokens=150, completion_tokens=50)
    return response

class TestClassificateurLLM:
    def test_classification_valide(self, classificateur, chemin_log):
        with patch.object(classificateur, "_get_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_response
            resultat = classificateur.classifier("Tim Hortons", "cafe", Decimal("5.50"))
```

**`patch.object`** is preferred over `patch("module.path.Class")` when patching methods on instances.

**PIL image creation** is used for document upload tests instead of mocking:

```python
# tests/test_documents.py
@pytest.fixture
def sample_jpg(tmp_path):
    """Cree une petite image JPEG de test."""
    img = Image.new("RGB", (100, 80), color="red")
    path = tmp_path / "receipt.jpg"
    img.save(path)
    return path
```

**What to mock:**
- External API calls (OpenAI, Anthropic)
- LLM client instantiation via `_get_client` method
- Any `MagicMock` for Beancount objects when not parsing real ledger text

**What NOT to mock:**
- File I/O with `tmp_path` (use real temp files instead)
- Beancount ledger parsing (use `beancount_parser.parse_string()` with inline ledger strings)
- `subprocess` calls for `git` in ledger integration tests (use real git repos in `tmp_path`)
- Tax calculation functions (test with real `Decimal` values, no mocking)

## Pytest Marks and Skips

Conditional skip for optional real-file fixtures:

```python
@pytest.fixture
def real_file(self):
    path = FIXTURES / "rbc_real_sample.csv"
    if not path.exists():
        pytest.skip("Fichier reel RBC non disponible")
    return path
```

**No `@pytest.mark.parametrize`** is used in the current test suite. Tests are written as individual methods with explicit values.

## Test Types

**Unit Tests (majority):**
- Test individual functions and class methods in isolation
- Use `tmp_path`, inline YAML, or literal values as inputs
- `tests/test_rates.py`, `tests/test_cotisations.py`, `tests/test_categorisation.py`, `tests/test_importers.py`

**Integration Tests:**
- Test the real ledger file (`ledger/main.beancount`) with actual `bean-check`
- `tests/test_ledger.py::TestValidation` runs `uv run bean-check` as a subprocess against the live ledger
- `tests/test_cli.py` runs full CLI commands via `typer.testing.CliRunner` with a real copied ledger

**Fava Extension Tests:**
- `tests/test_fava_ext.py`, `tests/test_fava_quebec.py`, `tests/test_fava_gap_closure.py`

**No E2E or browser tests.**

## Accounting Invariant Patterns

A recurring pattern across importer and categorisation tests: verify double-entry bookkeeping invariant:

```python
def test_postings_balancent_apres_categorisation(self):
    resultat = appliquer_categorisation(txns, moteur)
    for txn in resultat:
        total = sum(p.units.number for p in txn.postings)
        assert total == Decimal("0")
```

This `sum(postings) == 0` assertion appears in `test_importers.py`, `test_categorisation.py`, and `test_mcp_server.py`.

## Error Testing

```python
# FileNotFoundError
def test_charger_fichier_inexistant(self, tmp_path):
    with pytest.raises(FileNotFoundError):
        charger_regles(tmp_path / "inexistant.yaml")

# ValueError with message match
def test_charger_fichier_invalide(self, tmp_path):
    with pytest.raises(ValueError, match="invalide"):
        charger_regles(f)

# ValueError for missing fiscal year
def test_obtenir_taux_annee_non_disponible_leve_erreur(self) -> None:
    with pytest.raises(ValueError, match="Taux non disponibles pour l'annee 2025"):
        obtenir_taux(2025)

# AttributeError for frozen dataclass mutation
def test_taux_annuels_immutable(self) -> None:
    with pytest.raises(AttributeError):
        taux.annee = 2025  # type: ignore[misc]
```

## Async Testing

Not used. All code is synchronous. No `pytest-asyncio` or `async def` test methods.

## Time-Dependent Testing

Use `freezegun` for any test that calls `datetime.date.today()` or checks scheduling deadlines:

```python
# tests/test_echeances.py
from freezegun import freeze_time

@freeze_time("2026-02-15")
def test_alertes_en_cours(self) -> None:
    alertes = obtenir_alertes(echeances, seuil_jours=30)
    ...
```

## Coverage

**Requirements:** No minimum threshold enforced in CI.

**View Coverage:**
```bash
uv run pytest --cov=src/compteqc --cov-report=term-missing
uv run pytest --cov=src/compteqc --cov-report=html
```

---

*Testing analysis: 2026-02-25*
