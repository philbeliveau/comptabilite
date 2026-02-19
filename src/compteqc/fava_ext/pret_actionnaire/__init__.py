"""Extension Fava: Suivi du pret actionnaire et alerte s.15(2).

Affiche le solde net, l'historique des mouvements, et un compte a rebours
colore pour la date d'inclusion s.15(2) de la Loi de l'impot sur le revenu.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase

from compteqc.quebec.pret_actionnaire.alertes import calculer_dates_alerte, obtenir_alertes_actives
from compteqc.quebec.pret_actionnaire.suivi import EtatPret, obtenir_etat_pret


def niveau_alerte_s152(jours_restants: int) -> str:
    """Retourne le niveau d'alerte pour le compte a rebours s.15(2).

    Args:
        jours_restants: Nombre de jours avant la date d'inclusion.

    Returns:
        'normal' (> 270 jours / 9 mois), 'attention' (180-270 / 6-9 mois),
        'urgent' (30-180), ou 'critique' (< 30 jours).
    """
    if jours_restants > 270:
        return "normal"
    if jours_restants > 180:
        return "attention"
    if jours_restants > 30:
        return "urgent"
    return "critique"


class PretActionnaireExtension(FavaExtensionBase):
    """Suivi du pret actionnaire avec alerte s.15(2)."""

    report_title = "Pret actionnaire"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._etat: EtatPret | None = None
        self._annee: int = datetime.date.today().year
        self._fin_exercice = datetime.date(self._annee, 12, 31)

    def after_load_file(self) -> None:
        """Recalcule l'etat du pret apres chargement du ledger."""
        self._annee = datetime.date.today().year
        self._fin_exercice = datetime.date(self._annee, 12, 31)
        entries = self.ledger.all_entries
        self._etat = obtenir_etat_pret(entries, self._fin_exercice)

    def loan_status(self) -> dict:
        """Retourne l'etat du pret actionnaire pour le template.

        Structure:
        - solde_net: Solde net du pret
        - direction: Description de la direction du solde
        - mouvements: Liste de mouvements en ordre chronologique inverse
        """
        if not self._etat:
            return {
                "solde_net": Decimal("0"),
                "direction": "Aucun mouvement",
                "mouvements": [],
            }

        solde = self._etat.solde
        if solde > 0:
            direction = "L'actionnaire doit a la societe"
        elif solde < 0:
            direction = "La societe doit a l'actionnaire"
        else:
            direction = "Solde nul"

        # Mouvements en ordre chronologique inverse
        mouvements = []
        solde_courant = Decimal("0")
        for m in self._etat.mouvements:
            solde_courant += m.montant
            mouvements.append({
                "date": m.date,
                "description": m.description,
                "montant": m.montant,
                "solde_courant": solde_courant,
            })
        mouvements.reverse()

        return {
            "solde_net": abs(solde),
            "direction": direction,
            "mouvements": mouvements,
        }

    def s152_status(self) -> dict | None:
        """Retourne le statut s.15(2) pour le template.

        Structure:
        - date_inclusion: Date d'inclusion la plus proche
        - jours_restants: Nombre de jours avant inclusion
        - niveau_alerte: 'normal', 'attention', 'urgent', ou 'critique'
        - message: Message descriptif
        - avances: Liste des avances ouvertes avec leurs deadlines

        Retourne None si aucune avance ouverte.
        """
        if not self._etat or not self._etat.avances_ouvertes:
            return None

        today = datetime.date.today()
        avances_avec_alertes = []

        date_inclusion_plus_proche = None
        for avance in self._etat.avances_ouvertes:
            alerte = calculer_dates_alerte(
                date_avance=avance["date"],
                montant=avance["montant_initial"],
                fin_exercice=self._fin_exercice,
                solde_restant=avance["solde_restant"],
            )
            jours = (alerte.date_inclusion - today).days
            avances_avec_alertes.append({
                "date_avance": avance["date"],
                "montant": avance["montant_initial"],
                "solde_restant": avance["solde_restant"],
                "date_inclusion": alerte.date_inclusion,
                "jours_restants": jours,
                "niveau": niveau_alerte_s152(jours),
            })

            if date_inclusion_plus_proche is None or alerte.date_inclusion < date_inclusion_plus_proche:
                date_inclusion_plus_proche = alerte.date_inclusion

        # Prendre le pire cas pour l'alerte globale
        jours_restants_min = min(a["jours_restants"] for a in avances_avec_alertes)
        niveau = niveau_alerte_s152(jours_restants_min)

        messages = {
            "normal": "Aucune echeance imminente.",
            "attention": "Planifier le remboursement dans les prochains mois.",
            "urgent": "Remboursement requis prochainement pour eviter l'inclusion au revenu.",
            "critique": "URGENT: Moins de 30 jours avant l'inclusion au revenu de l'actionnaire.",
        }

        return {
            "date_inclusion": date_inclusion_plus_proche,
            "jours_restants": jours_restants_min,
            "niveau_alerte": niveau,
            "message": messages[niveau],
            "avances": avances_avec_alertes,
        }
