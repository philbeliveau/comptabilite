"""Detection des patterns circulaires pret-remboursement-pret.

Section 15(2.6) de la Loi de l'impot sur le revenu:
Un remboursement suivi rapidement d'une nouvelle avance de montant similaire
peut etre considere comme un arrangement pour eviter l'inclusion au revenu.

Detection: si un remboursement est suivi d'une nouvelle avance de montant
similaire (tolerance de 20%) dans une fenetre configurable (defaut 30 jours).
"""

from decimal import Decimal

from compteqc.quebec.pret_actionnaire.suivi import MouvementPret


def detecter_circularite(
    mouvements: list[MouvementPret],
    fenetre_jours: int = 30,
    tolerance: Decimal = Decimal("0.20"),
) -> list[dict]:
    """Detecte les patterns circulaires remboursement-avance.

    Un pattern est flagge si:
    1. Un remboursement (montant < 0) est suivi d'une avance (montant > 0)
    2. L'avance est dans les `fenetre_jours` jours suivant le remboursement
    3. Le montant de l'avance est dans la tolerance du remboursement (20%)

    Args:
        mouvements: Liste des mouvements du pret actionnaire
        fenetre_jours: Nombre de jours de la fenetre de detection (defaut 30)
        tolerance: Tolerance sur le montant (defaut 0.20 = 20%)

    Returns:
        Liste de dicts: {
            date_remboursement, montant_remboursement,
            date_avance, montant_avance, ecart_jours
        }
    """
    mouvements_tries = sorted(mouvements, key=lambda m: m.date)
    patterns: list[dict] = []

    # Identifier les remboursements et les avances
    remboursements = [m for m in mouvements_tries if m.montant < 0]
    avances = [m for m in mouvements_tries if m.montant > 0]

    for remb in remboursements:
        montant_remb = abs(remb.montant)

        for avance in avances:
            # L'avance doit etre apres le remboursement
            if avance.date <= remb.date:
                continue

            ecart = (avance.date - remb.date).days
            if ecart > fenetre_jours:
                continue

            # Verifier la tolerance sur le montant
            montant_avance = avance.montant
            difference = abs(montant_avance - montant_remb)
            if montant_remb > 0 and (difference / montant_remb) <= tolerance:
                patterns.append({
                    "date_remboursement": remb.date,
                    "montant_remboursement": remb.montant,
                    "date_avance": avance.date,
                    "montant_avance": avance.montant,
                    "ecart_jours": ecart,
                })

    return patterns
