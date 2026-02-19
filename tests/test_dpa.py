"""Tests pour le module DPA (deduction pour amortissement / CCA).

Couvre:
- Calcul DPA classe 50 premiere et deuxieme annee
- Regle du demi-taux sur additions nettes
- Recapture quand la FNACC devient negative
- Perte finale quand la classe est vide
- Persistance YAML du registre d'actifs
- Flag '!' sur les transactions generees
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from compteqc.quebec.dpa.calcul import PoolDPA, construire_pools
from compteqc.quebec.dpa.journal import generer_transactions_dpa
from compteqc.quebec.dpa.registre import Actif, RegistreActifs


class TestPoolDPA:
    """Tests du calcul DPA par pool."""

    def test_dpa_classe_50_premiere_annee(self):
        """Acquérir un ordinateur a $3,000 en classe 50.

        UCC ouverture = 0. Acquisitions = $3,000. Dispositions = 0.
        Additions nettes = $3,000 (positif -> regle du demi-taux).
        Base = 0 + (3000 * 0.5) = $1,500.
        DPA = $1,500 * 0.55 = $825.00.
        UCC fermeture = $3,000 - $825 = $2,175.00.
        """
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("0.00"),
            acquisitions=Decimal("3000.00"),
            dispositions=Decimal("0.00"),
        )

        assert pool.additions_nettes == Decimal("3000.00")
        assert pool.calculer_dpa() == Decimal("825.00")
        assert pool.ucc_fermeture == Decimal("2175.00")
        assert pool.recapture == Decimal("0.00")

    def test_dpa_classe_50_deuxieme_annee(self):
        """Deuxieme annee: UCC ouverture = $2,175. Pas de nouvelles acquisitions.

        Base = $2,175 (pas de demi-taux, additions nettes = 0).
        DPA = $2,175 * 0.55 = $1,196.25.
        UCC fermeture = $2,175 - $1,196.25 = $978.75.
        """
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("2175.00"),
            acquisitions=Decimal("0.00"),
            dispositions=Decimal("0.00"),
        )

        assert pool.additions_nettes == Decimal("0.00")
        assert pool.calculer_dpa() == Decimal("1196.25")
        assert pool.ucc_fermeture == Decimal("978.75")

    def test_dpa_demi_taux_additions_nettes(self):
        """Annee avec acquisition $3,000 ET disposition $1,000.

        Actif dispose: cout $1,500, produit $1,000.
        Montant disposition = min($1,500, $1,000) = $1,000.
        Additions nettes = $3,000 - $1,000 = $2,000 (positif -> demi-taux).
        UCC ouverture = $2,175.
        Base = $2,175 + ($2,000 * 0.5) = $3,175.
        DPA = $3,175 * 0.55 = $1,746.25.
        """
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("2175.00"),
            acquisitions=Decimal("3000.00"),
            dispositions=Decimal("1000.00"),
        )

        assert pool.additions_nettes == Decimal("2000.00")
        assert pool.calculer_dpa() == Decimal("1746.25")

    def test_recapture(self):
        """UCC ouverture = $500, disposition = $800 -> FNACC negative -> recapture $300.

        ucc_ouverture + additions_nettes = $500 + (0 - $800) = -$300
        Recapture = $300.
        DPA = $0 (base negative).
        """
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("500.00"),
            acquisitions=Decimal("0.00"),
            dispositions=Decimal("800.00"),
        )

        assert pool.recapture == Decimal("300.00")
        assert pool.calculer_dpa() == Decimal("0.00")

    def test_perte_finale(self):
        """UCC ouverture = $200, tous les actifs disposes a $0 -> perte finale $200.

        Disposition montant = min(cout, $0) = $0 (produit = 0).
        Additions nettes = 0 - 0 = 0.
        DPA = $200 * 0.55 = $110.
        UCC fermeture = $200 - $110 = $90.
        Perte finale = $90 (0 actifs restants et UCC > 0).

        Note: en pratique la perte finale remplace la DPA, mais le calcul
        montre la FNACC restante qui constitue la perte finale.
        """
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("200.00"),
            acquisitions=Decimal("0.00"),
            dispositions=Decimal("0.00"),
        )

        # Avec 0 actifs restants et UCC fermeture positive
        assert pool.ucc_fermeture == Decimal("90.00")
        assert pool.perte_finale(nb_actifs_restants=0) == Decimal("90.00")

        # Avec des actifs restants, pas de perte finale
        assert pool.perte_finale(nb_actifs_restants=1) == Decimal("0.00")

    def test_additions_nettes_negatives_pas_de_demi_taux(self):
        """Si les additions nettes sont negatives, pas de regle du demi-taux.

        UCC ouverture = $1,000. Acquisitions = $500. Dispositions = $800.
        Additions nettes = $500 - $800 = -$300.
        Base = $1,000 + (-$300) = $700 (pas de demi-taux).
        DPA = $700 * 0.20 = $140.00.
        """
        pool = PoolDPA(
            classe=8,
            taux=Decimal("0.20"),
            ucc_ouverture=Decimal("1000.00"),
            acquisitions=Decimal("500.00"),
            dispositions=Decimal("800.00"),
        )

        assert pool.additions_nettes == Decimal("-300.00")
        assert pool.calculer_dpa() == Decimal("140.00")


class TestConstruirePools:
    """Tests de la construction des pools a partir du registre."""

    def test_construire_pools_premiere_annee(self):
        """Construction des pools avec un seul actif, premiere annee."""
        actifs = [
            Actif(
                id="mac-studio",
                description="Mac Studio M4",
                classe=50,
                cout=Decimal("3000.00"),
                date_acquisition=date(2026, 3, 15),
            )
        ]

        pools = construire_pools(actifs, {}, 2026)

        assert 50 in pools
        assert pools[50].acquisitions == Decimal("3000.00")
        assert pools[50].dispositions == Decimal("0.00")
        assert pools[50].ucc_ouverture == Decimal("0.00")

    def test_construire_pools_avec_disposition(self):
        """Pool avec un actif dispose durant l'annee."""
        actifs = [
            Actif(
                id="vieux-laptop",
                description="Ancien laptop",
                classe=50,
                cout=Decimal("1500.00"),
                date_acquisition=date(2024, 1, 1),
                date_disposition=date(2026, 6, 1),
                produit_disposition=Decimal("1000.00"),
            ),
        ]

        pools = construire_pools(
            actifs,
            {50: Decimal("2175.00")},
            2026,
        )

        assert pools[50].dispositions == Decimal("1000.00")  # min(1500, 1000)
        assert pools[50].ucc_ouverture == Decimal("2175.00")


class TestRegistreActifs:
    """Tests du registre d'actifs avec persistance YAML."""

    def test_registre_ajouter_et_charger(self, tmp_path: Path):
        """Round-trip: ajouter, sauvegarder, charger."""
        chemin = tmp_path / "actifs.yaml"
        registre = RegistreActifs(chemin)

        actif = Actif(
            id="mac-studio-2026",
            description="Mac Studio M4 Ultra",
            classe=50,
            cout=Decimal("3499.99"),
            date_acquisition=date(2026, 2, 15),
        )
        registre.ajouter(actif)
        registre.sauvegarder()

        # Recharger dans un nouveau registre
        registre2 = RegistreActifs(chemin)
        actifs = registre2.charger()

        assert len(actifs) == 1
        assert actifs[0].id == "mac-studio-2026"
        assert actifs[0].cout == Decimal("3499.99")
        assert actifs[0].classe == 50
        assert actifs[0].date_acquisition == date(2026, 2, 15)
        assert actifs[0].date_disposition is None

    def test_registre_disposer(self, tmp_path: Path):
        """Disposition d'un actif dans le registre."""
        chemin = tmp_path / "actifs.yaml"
        registre = RegistreActifs(chemin)

        actif = Actif(
            id="laptop-2024",
            description="Laptop Dell",
            classe=50,
            cout=Decimal("1500.00"),
            date_acquisition=date(2024, 1, 15),
        )
        registre.ajouter(actif)
        registre.disposer("laptop-2024", date(2026, 6, 1), Decimal("800.00"))

        assert registre.actifs[0].date_disposition == date(2026, 6, 1)
        assert registre.actifs[0].produit_disposition == Decimal("800.00")

    def test_registre_id_unique(self, tmp_path: Path):
        """Impossible d'ajouter deux actifs avec le meme ID."""
        chemin = tmp_path / "actifs.yaml"
        registre = RegistreActifs(chemin)

        actif = Actif(
            id="mac-1",
            description="Mac",
            classe=50,
            cout=Decimal("3000.00"),
            date_acquisition=date(2026, 1, 1),
        )
        registre.ajouter(actif)

        with pytest.raises(ValueError, match="existe deja"):
            registre.ajouter(actif)

    def test_registre_fichier_vide(self, tmp_path: Path):
        """Charger un fichier qui n'existe pas retourne une liste vide."""
        chemin = tmp_path / "inexistant.yaml"
        registre = RegistreActifs(chemin)
        actifs = registre.charger()
        assert actifs == []


class TestJournalDPA:
    """Tests de la generation de transactions Beancount."""

    def test_journal_dpa_flag_review(self):
        """Les transactions DPA sont marquees '!' pour revision."""
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("2175.00"),
            acquisitions=Decimal("0.00"),
            dispositions=Decimal("0.00"),
        )

        transactions = generer_transactions_dpa({50: pool}, date(2026, 12, 31))

        assert len(transactions) == 1
        txn = transactions[0]
        assert txn.flag == "!"
        assert txn.narration == "DPA classe 50 - Materiel informatique (ordinateurs, moniteurs)"
        assert txn.date == date(2026, 12, 31)
        assert len(txn.postings) == 2
        assert txn.postings[0].account == "Depenses:Amortissement"
        assert txn.postings[1].account == "Actifs:Immobilisations:Amortissement-Cumule"
        assert "dpa" in txn.tags

    def test_journal_dpa_recapture(self):
        """Transaction de recapture generee quand la FNACC est negative."""
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("500.00"),
            acquisitions=Decimal("0.00"),
            dispositions=Decimal("800.00"),
        )

        transactions = generer_transactions_dpa({50: pool}, date(2026, 12, 31))

        # Pas de DPA (base negative), mais une recapture
        assert len(transactions) == 1
        txn = transactions[0]
        assert "recapture" in txn.tags
        assert txn.narration.startswith("Recapture DPA")

    def test_journal_dpa_pas_de_transaction_zero(self):
        """Pas de transaction si la DPA est zero et pas de recapture."""
        pool = PoolDPA(
            classe=50,
            taux=Decimal("0.55"),
            ucc_ouverture=Decimal("0.00"),
            acquisitions=Decimal("0.00"),
            dispositions=Decimal("0.00"),
        )

        transactions = generer_transactions_dpa({50: pool}, date(2026, 12, 31))
        assert len(transactions) == 0
