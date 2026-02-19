"""Tests pour le module pret actionnaire (shareholder loan).

Couvre:
- Calcul des dates d'alerte s.15(2)
- Solde bidirectionnel
- Alertes actives par niveau d'urgence
- Detection de circularite (patterns pret-remboursement-pret)
"""

import datetime
from decimal import Decimal

from freezegun import freeze_time

from compteqc.quebec.pret_actionnaire.alertes import (
    calculer_dates_alerte,
    obtenir_alertes_actives,
)
from compteqc.quebec.pret_actionnaire.detection import detecter_circularite
from compteqc.quebec.pret_actionnaire.suivi import MouvementPret, calculer_etat_pret

FIN_EXERCICE_DEC31 = datetime.date(2026, 12, 31)


class TestCalculerDatesAlerte:
    """Tests du calcul des dates limites s.15(2)."""

    def test_calculer_dates_alerte_dec31(self):
        """Avance 15 juin 2026, exercice 31 dec.

        Date d'inclusion = 31 dec 2027.
        Alerte 9 mois = 31 mars 2027.
        Alerte 11 mois = 31 janvier 2027.
        Alerte 30 jours = 1 decembre 2027.
        """
        alerte = calculer_dates_alerte(
            date_avance=datetime.date(2026, 6, 15),
            montant=Decimal("5000.00"),
            fin_exercice=FIN_EXERCICE_DEC31,
        )

        assert alerte.date_inclusion == datetime.date(2027, 12, 31)
        assert alerte.alerte_9_mois == datetime.date(2027, 3, 31)
        assert alerte.alerte_11_mois == datetime.date(2027, 1, 31)
        assert alerte.alerte_30_jours == datetime.date(2027, 12, 1)
        assert alerte.solde_restant == Decimal("5000.00")

    def test_calculer_dates_alerte_avance_janvier(self):
        """Avance 5 janvier 2026 -> meme inclusion 31 dec 2027.

        La date d'inclusion est basee sur l'exercice fiscal, PAS la date du pret.
        """
        alerte = calculer_dates_alerte(
            date_avance=datetime.date(2026, 1, 5),
            montant=Decimal("10000.00"),
            fin_exercice=FIN_EXERCICE_DEC31,
        )

        assert alerte.date_inclusion == datetime.date(2027, 12, 31)


class TestSolde:
    """Tests du calcul du solde bidirectionnel."""

    def test_solde_bidirectionnel(self):
        """Avance $5,000, remboursement $3,000 -> solde $2,000 (positif)."""
        mouvements = [
            MouvementPret(
                date=datetime.date(2026, 3, 1),
                montant=Decimal("5000.00"),
                description="Retrait personnel",
                type="avance",
            ),
            MouvementPret(
                date=datetime.date(2026, 6, 1),
                montant=Decimal("-3000.00"),
                description="Remboursement",
                type="remboursement",
            ),
        ]

        etat = calculer_etat_pret(mouvements)

        assert etat.solde == Decimal("2000.00")
        assert len(etat.avances_ouvertes) == 1
        assert etat.avances_ouvertes[0]["solde_restant"] == Decimal("2000.00")

    def test_solde_negatif(self):
        """Corp doit a l'actionnaire $1,000 -> solde -$1,000."""
        mouvements = [
            MouvementPret(
                date=datetime.date(2026, 1, 15),
                montant=Decimal("-1000.00"),
                description="Depot personnel dans la corporation",
                type="depot_personnel",
            ),
        ]

        etat = calculer_etat_pret(mouvements)

        assert etat.solde == Decimal("-1000.00")
        assert len(etat.avances_ouvertes) == 0


class TestAlertesActives:
    """Tests des alertes actives par niveau d'urgence."""

    def test_alertes_actives_9_mois(self):
        """Date courante en avril 2027 (apres le seuil 9 mois de mars 31)."""
        avances_ouvertes = [
            {
                "date": datetime.date(2026, 6, 15),
                "montant_initial": Decimal("5000.00"),
                "solde_restant": Decimal("5000.00"),
            }
        ]

        with freeze_time("2027-04-15"):
            alertes = obtenir_alertes_actives(
                avances_ouvertes,
                FIN_EXERCICE_DEC31,
                datetime.date.today(),
            )

        assert len(alertes) == 1
        assert alertes[0]["urgence"] == "9_mois"
        assert alertes[0]["deadline"] == datetime.date(2027, 12, 31)

    def test_alertes_actives_depasse(self):
        """Date courante en janvier 2028 (apres la date d'inclusion)."""
        avances_ouvertes = [
            {
                "date": datetime.date(2026, 6, 15),
                "montant_initial": Decimal("5000.00"),
                "solde_restant": Decimal("5000.00"),
            }
        ]

        with freeze_time("2028-01-15"):
            alertes = obtenir_alertes_actives(
                avances_ouvertes,
                FIN_EXERCICE_DEC31,
                datetime.date.today(),
            )

        assert len(alertes) == 1
        assert alertes[0]["urgence"] == "depasse"

    def test_alertes_cleared_advance(self):
        """Avance completement remboursee -> pas d'alerte."""
        avances_ouvertes = [
            {
                "date": datetime.date(2026, 6, 15),
                "montant_initial": Decimal("5000.00"),
                "solde_restant": Decimal("0.00"),
            }
        ]

        with freeze_time("2027-12-15"):
            alertes = obtenir_alertes_actives(
                avances_ouvertes,
                FIN_EXERCICE_DEC31,
                datetime.date.today(),
            )

        assert len(alertes) == 0

    def test_alertes_11_mois(self):
        """Date courante en fevrier 2027 (apres le seuil 11 mois de jan 31)."""
        avances_ouvertes = [
            {
                "date": datetime.date(2026, 6, 15),
                "montant_initial": Decimal("5000.00"),
                "solde_restant": Decimal("5000.00"),
            }
        ]

        with freeze_time("2027-02-15"):
            alertes = obtenir_alertes_actives(
                avances_ouvertes,
                FIN_EXERCICE_DEC31,
                datetime.date.today(),
            )

        assert len(alertes) == 1
        assert alertes[0]["urgence"] == "11_mois"

    def test_alertes_30_jours(self):
        """Date courante le 5 decembre 2027 (apres le seuil 30 jours du 1er dec)."""
        avances_ouvertes = [
            {
                "date": datetime.date(2026, 6, 15),
                "montant_initial": Decimal("5000.00"),
                "solde_restant": Decimal("5000.00"),
            }
        ]

        with freeze_time("2027-12-05"):
            alertes = obtenir_alertes_actives(
                avances_ouvertes,
                FIN_EXERCICE_DEC31,
                datetime.date.today(),
            )

        assert len(alertes) == 1
        assert alertes[0]["urgence"] == "30_jours"


class TestCircularite:
    """Tests de la detection de patterns circulaires."""

    def test_circularite_detectee(self):
        """Remboursement $5,000 le 15 jan, nouvelle avance $4,800 le 1 fev.

        17 jours d'ecart, montant dans la tolerance 20% -> flagge.
        """
        mouvements = [
            MouvementPret(
                date=datetime.date(2026, 1, 1),
                montant=Decimal("5000.00"),
                description="Avance initiale",
                type="avance",
            ),
            MouvementPret(
                date=datetime.date(2026, 1, 15),
                montant=Decimal("-5000.00"),
                description="Remboursement",
                type="remboursement",
            ),
            MouvementPret(
                date=datetime.date(2026, 2, 1),
                montant=Decimal("4800.00"),
                description="Nouvelle avance",
                type="avance",
            ),
        ]

        patterns = detecter_circularite(mouvements)

        assert len(patterns) == 1
        assert patterns[0]["ecart_jours"] == 17
        assert patterns[0]["montant_avance"] == Decimal("4800.00")
        assert patterns[0]["montant_remboursement"] == Decimal("-5000.00")

    def test_circularite_ok(self):
        """Remboursement $5,000 le 15 jan, avance $1,000 le 1 juin.

        Montant different et hors fenetre -> pas flagge.
        """
        mouvements = [
            MouvementPret(
                date=datetime.date(2026, 1, 1),
                montant=Decimal("5000.00"),
                description="Avance initiale",
                type="avance",
            ),
            MouvementPret(
                date=datetime.date(2026, 1, 15),
                montant=Decimal("-5000.00"),
                description="Remboursement",
                type="remboursement",
            ),
            MouvementPret(
                date=datetime.date(2026, 6, 1),
                montant=Decimal("1000.00"),
                description="Petite avance",
                type="avance",
            ),
        ]

        patterns = detecter_circularite(mouvements)

        assert len(patterns) == 0

    def test_pas_de_circularite_montant_different(self):
        """Remboursement $5,000, avance $500 dans la fenetre.

        Montant pas dans la tolerance 20% ($500 vs $5,000) -> pas flagge.
        """
        mouvements = [
            MouvementPret(
                date=datetime.date(2026, 1, 15),
                montant=Decimal("-5000.00"),
                description="Remboursement",
                type="remboursement",
            ),
            MouvementPret(
                date=datetime.date(2026, 2, 1),
                montant=Decimal("500.00"),
                description="Petite avance",
                type="avance",
            ),
        ]

        patterns = detecter_circularite(mouvements)

        assert len(patterns) == 0
