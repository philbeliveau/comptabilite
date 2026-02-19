"""Tests pour les outils MCP de mutation (categorisation, approbation, paie).

Teste la logique des outils MCP en mockant les operations I/O et le ledger.
Les modules domaine sont deja testes dans les phases 2/3.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from compteqc.mcp.server import AppContext
from compteqc.mcp.services import trouver_pending_par_id


# ---------- Helpers ----------

def _make_ctx(*, read_only: bool = False, entries: list | None = None, ledger_path: str = "ledger/main.beancount"):
    """Cree un faux contexte MCP pour les tests."""
    app = AppContext(
        ledger_path=ledger_path,
        entries=entries or [],
        errors=[],
        options={},
        read_only=read_only,
    )
    # Desactiver reload() pour eviter les I/O
    app.reload = MagicMock()

    ctx = MagicMock()
    ctx.request_context.lifespan_context = app
    return ctx, app


def _make_pending_list(montants: list[tuple[str, str, str, Decimal]]) -> list[dict]:
    """Cree une liste de pending transactions pour les tests.

    Args:
        montants: Liste de (date, payee, narration, montant).
    """
    return [
        {
            "date": date,
            "payee": payee,
            "narration": narration,
            "montant": montant,
            "confiance": "0.85",
            "source": "ml",
            "compte_propose": "Depenses:Non-Classe",
        }
        for date, payee, narration, montant in montants
    ]


# ---------- Tests trouver_pending_par_id ----------

class TestTrouverPendingParId:
    def test_trouve_par_id(self):
        pending = _make_pending_list([
            ("2026-01-15", "Amazon", "Achat fournitures", Decimal("150.00")),
            ("2026-01-20", "Bell", "Facture internet mensuelle", Decimal("89.99")),
        ])
        idx = trouver_pending_par_id(pending, "2026-01-20|Bell|Facture internet men")
        assert idx == 1

    def test_introuvable(self):
        pending = _make_pending_list([
            ("2026-01-15", "Amazon", "Achat fournitures", Decimal("150.00")),
        ])
        idx = trouver_pending_par_id(pending, "2026-99-99|Inexistant|Rien")
        assert idx is None

    def test_narration_tronquee_20_chars(self):
        pending = _make_pending_list([
            ("2026-01-15", "Amazon", "Achat de fournitures informatiques tres long", Decimal("150.00")),
        ])
        # Narration[:20] = "Achat de fournitures"
        idx = trouver_pending_par_id(pending, "2026-01-15|Amazon|Achat de fournitures")
        assert idx == 0


# ---------- Tests proposer_categorie ----------

class TestProposerCategorie:
    def _patch_pipeline(self, resultat):
        """Context manager to mock the entire categorisation pipeline."""
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.categoriser.return_value = resultat
        return [
            patch("compteqc.categorisation.pipeline.PipelineCategorisation", return_value=mock_pipeline_instance),
            patch("compteqc.categorisation.moteur.MoteurRegles", return_value=MagicMock()),
            patch("compteqc.categorisation.capex.DetecteurCAPEX", return_value=MagicMock()),
            patch("os.path.exists", return_value=False),
        ]

    def test_retourne_champs_requis(self):
        from contextlib import ExitStack
        from compteqc.categorisation.pipeline import ResultatPipeline

        resultat = ResultatPipeline(
            compte="Depenses:Fournitures", confiance=0.85, source="ml",
            regle=None, est_capex=False, classe_dpa=None,
            revue_obligatoire=False, suggestions=None,
        )

        ctx, app = _make_ctx()
        from compteqc.mcp.tools.categorisation import proposer_categorie

        with ExitStack() as stack:
            for p in self._patch_pipeline(resultat):
                stack.enter_context(p)
            result = proposer_categorie(payee="Amazon", narration="Fournitures", montant="150.00", ctx=ctx)

        assert "compte_propose" in result
        assert "confiance" in result
        assert "source" in result
        assert "raison" in result
        assert result["compte_propose"] == "Depenses:Fournitures"
        assert result["source"] == "ml"
        assert "Modele ML" in result["raison"]

    def test_auto_approuve_haute_confiance_faible_montant(self):
        from contextlib import ExitStack
        from compteqc.categorisation.pipeline import ResultatPipeline

        resultat = ResultatPipeline(
            compte="Depenses:Internet", confiance=0.98, source="regle",
            regle="bell_internet", est_capex=False, classe_dpa=None,
            revue_obligatoire=False, suggestions=None,
        )

        ctx, app = _make_ctx()
        from compteqc.mcp.tools.categorisation import proposer_categorie

        with ExitStack() as stack:
            for p in self._patch_pipeline(resultat):
                stack.enter_context(p)
            result = proposer_categorie(payee="Bell", narration="Internet", montant="500.00", ctx=ctx)

        assert result["auto_approuve"] is True

    def test_pas_auto_approuve_gros_montant(self):
        from contextlib import ExitStack
        from compteqc.categorisation.pipeline import ResultatPipeline

        resultat = ResultatPipeline(
            compte="Depenses:Fournitures", confiance=0.98, source="regle",
            regle="amazon", est_capex=False, classe_dpa=None,
            revue_obligatoire=False, suggestions=None,
        )

        ctx, app = _make_ctx()
        from compteqc.mcp.tools.categorisation import proposer_categorie

        with ExitStack() as stack:
            for p in self._patch_pipeline(resultat):
                stack.enter_context(p)
            result = proposer_categorie(payee="Apple", narration="MacBook", montant="3000.00", ctx=ctx)

        assert result["auto_approuve"] is False

    def test_raison_regle(self):
        from compteqc.mcp.tools.categorisation import _construire_raison

        raison = _construire_raison("regle", "Depenses:Internet", 1.0, "bell_internet")
        assert "Regle 'bell_internet'" in raison

    def test_raison_non_classe(self):
        from compteqc.mcp.tools.categorisation import _construire_raison

        raison = _construire_raison("non-classe", "Depenses:Non-Classe", 0.0, None)
        assert "Aucun classificateur" in raison


# ---------- Tests approbation ----------

class TestApprouverLot:
    def test_read_only_bloque(self):
        ctx, app = _make_ctx(read_only=True)

        from compteqc.mcp.tools.approbation import approuver_lot

        result = approuver_lot(ids=["2026-01-15|Amazon|Fournitures"], ctx=ctx)
        assert result["status"] == "erreur"
        assert "lecture seule" in result["message"].lower()

    @patch("compteqc.mcp.tools.approbation.lister_pending")
    def test_garde_fou_2000(self, mock_lister):
        mock_lister.return_value = _make_pending_list([
            ("2026-01-15", "Apple", "MacBook Pro", Decimal("3500.00")),
        ])
        ctx, app = _make_ctx()

        from compteqc.mcp.tools.approbation import approuver_lot

        result = approuver_lot(ids=["2026-01-15|Apple|MacBook Pro"], ctx=ctx)
        assert result["status"] == "confirmation_requise"
        assert len(result["transactions_gros_montants"]) == 1

    @patch("compteqc.mcp.tools.approbation.lister_pending")
    @patch("compteqc.categorisation.pending.approuver_transactions")
    def test_approuve_avec_confirmation(self, mock_approuver, mock_lister):
        mock_lister.return_value = _make_pending_list([
            ("2026-01-15", "Apple", "MacBook Pro", Decimal("3500.00")),
        ])
        mock_approuver.return_value = 1

        ctx, app = _make_ctx()

        from compteqc.mcp.tools.approbation import approuver_lot

        result = approuver_lot(
            ids=["2026-01-15|Apple|MacBook Pro"],
            confirmer_gros_montants=True,
            ctx=ctx,
        )
        assert result["status"] == "ok"
        assert result["nb_approuve"] == 1
        app.reload.assert_called_once()


class TestRejeter:
    def test_read_only_bloque(self):
        ctx, app = _make_ctx(read_only=True)

        from compteqc.mcp.tools.approbation import rejeter

        result = rejeter(id="2026-01-15|Amazon|Fournitures", ctx=ctx)
        assert result["status"] == "erreur"
        assert "lecture seule" in result["message"].lower()

    @patch("compteqc.mcp.tools.approbation.lister_pending")
    @patch("compteqc.mcp.tools.approbation._corriger_pending")
    @patch("compteqc.categorisation.pending.rejeter_transactions")
    def test_rejeter_avec_correction(self, mock_rejeter_txn, mock_corriger, mock_lister):
        mock_lister.return_value = _make_pending_list([
            ("2026-01-15", "Amazon", "Fournitures bureau", Decimal("150.00")),
        ])
        mock_rejeter_txn.return_value = 1

        ctx, app = _make_ctx()

        from compteqc.mcp.tools.approbation import rejeter

        result = rejeter(
            id="2026-01-15|Amazon|Fournitures bureau",
            compte_corrige="Depenses:Bureau",
            ctx=ctx,
        )
        assert result["status"] == "ok"
        assert "Depenses:Bureau" in result["message"]
        mock_corriger.assert_called_once()
        app.reload.assert_called_once()


# ---------- Tests paie ----------

class TestCalculerPaieTool:
    @patch("compteqc.quebec.paie.moteur.calculer_paie")
    def test_retourne_structure_correcte(self, mock_calc):
        from compteqc.quebec.paie.moteur import ResultatPaie

        mock_calc.return_value = ResultatPaie(
            brut=Decimal("4230.77"),
            numero_periode=1,
            nb_periodes=26,
            qpp_base=Decimal("200.00"),
            qpp_supp1=Decimal("15.00"),
            qpp_supp2=Decimal("5.00"),
            rqap=Decimal("20.00"),
            ae=Decimal("30.00"),
            impot_federal=Decimal("500.00"),
            impot_quebec=Decimal("400.00"),
            qpp_base_employeur=Decimal("200.00"),
            qpp_supp1_employeur=Decimal("15.00"),
            qpp_supp2_employeur=Decimal("5.00"),
            rqap_employeur=Decimal("28.00"),
            ae_employeur=Decimal("42.00"),
            fss=Decimal("70.00"),
            cnesst=Decimal("25.00"),
            normes_travail=Decimal("3.00"),
            total_retenues=Decimal("1170.00"),
            total_cotisations_employeur=Decimal("388.00"),
            net=Decimal("3060.77"),
        )

        ctx, app = _make_ctx()

        from compteqc.mcp.tools.paie import calculer_paie_tool

        result = calculer_paie_tool(salaire_brut="4230.77", ctx=ctx)

        assert "salaire_brut" in result
        assert "retenues_employe" in result
        assert "cotisations_employeur" in result
        assert "salaire_net" in result
        assert "cout_total_employeur" in result
        assert len(result["retenues_employe"]) == 7
        assert len(result["cotisations_employeur"]) == 8


class TestLancerPaie:
    def test_read_only_bloque(self):
        ctx, app = _make_ctx(read_only=True)

        from compteqc.mcp.tools.paie import lancer_paie

        result = lancer_paie(salaire_brut="4230.77", ctx=ctx)
        assert result["status"] == "erreur"
        assert "lecture seule" in result["message"].lower()

    def test_confirmation_gros_montant(self):
        """Meme montant que precedent mais > 2000 -> raison=gros_montant."""
        from beancount.core import data as bdata

        # Creer une transaction paie precedente avec le meme brut
        meta = {"filename": "<test>", "lineno": 0, "brut": "4230.77"}
        txn = bdata.Transaction(
            meta=meta,
            date=None,
            flag="*",
            payee=None,
            narration="Paie #1",
            tags=frozenset({"paie"}),
            links=frozenset(),
            postings=[],
        )

        ctx, app = _make_ctx(entries=[txn])

        from compteqc.mcp.tools.paie import lancer_paie

        result = lancer_paie(salaire_brut="4230.77", ctx=ctx)
        assert result["status"] == "confirmation_requise"
        assert result["raison"] == "gros_montant"

    def test_confirmation_nouveau_montant(self):
        """Montant different du precedent mais <= 2000 -> raison=nouveau_montant."""
        from beancount.core import data as bdata

        meta = {"filename": "<test>", "lineno": 0, "brut": "1500.00"}
        txn = bdata.Transaction(
            meta=meta,
            date=None,
            flag="*",
            payee=None,
            narration="Paie #1",
            tags=frozenset({"paie"}),
            links=frozenset(),
            postings=[],
        )

        ctx, app = _make_ctx(entries=[txn])

        from compteqc.mcp.tools.paie import lancer_paie

        result = lancer_paie(salaire_brut="1800.00", ctx=ctx)
        assert result["status"] == "confirmation_requise"
        assert result["raison"] == "nouveau_montant"

    def test_confirmation_nouveau_et_gros_montant(self):
        """Montant different ET > 2000 -> raison=nouveau_et_gros_montant."""
        from beancount.core import data as bdata

        meta = {"filename": "<test>", "lineno": 0, "brut": "3000.00"}
        txn = bdata.Transaction(
            meta=meta,
            date=None,
            flag="*",
            payee=None,
            narration="Paie #1",
            tags=frozenset({"paie"}),
            links=frozenset(),
            postings=[],
        )

        ctx, app = _make_ctx(entries=[txn])

        from compteqc.mcp.tools.paie import lancer_paie

        result = lancer_paie(salaire_brut="4230.77", ctx=ctx)
        assert result["status"] == "confirmation_requise"
        assert result["raison"] == "nouveau_et_gros_montant"
