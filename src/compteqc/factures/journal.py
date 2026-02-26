"""Generation d'ecritures Beancount pour les factures.

Produit les ecritures de comptes clients (AR) et de paiement.
Supporte les comptes de revenu par ligne et les paiements partiels.
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from decimal import Decimal

from compteqc.factures.modeles import Facture


def generer_ecriture_facture(facture: Facture) -> str:
    """Genere l'ecriture Beancount pour la creation d'une facture (AR).

    Debit: Actifs:ComptesClients (total)
    Credit: par compte de revenu (sous-totaux groupes par compte_revenu)
    Credit: Passifs:TPS-Percue (TPS)
    Credit: Passifs:TVQ-Percue (TVQ)
    """
    date_str = facture.date.isoformat()
    total = facture.total
    tps = facture.tps
    tvq = facture.tvq

    # Group line subtotals by revenue account
    revenus_par_compte: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for ligne in facture.lignes:
        revenus_par_compte[ligne.compte_revenu] += ligne.sous_total

    lignes = [
        f'{date_str} * "Facture {facture.numero} - {facture.nom_client}"',
        f"  Actifs:ComptesClients  {total} CAD",
    ]

    for compte, montant in revenus_par_compte.items():
        lignes.append(f"  {compte}  -{montant} CAD")

    if tps > 0:
        lignes.append(f"  Passifs:TPS-Percue  -{tps} CAD")
    if tvq > 0:
        lignes.append(f"  Passifs:TVQ-Percue  -{tvq} CAD")

    return "\n".join(lignes)


def generer_ecriture_paiement(facture: Facture) -> str:
    """Genere l'ecriture Beancount pour le paiement complet d'une facture.

    Debit: Actifs:Banque:RBC:Cheques (total)
    Credit: Actifs:ComptesClients (-total)
    """
    date_str = (facture.date_paiement or facture.date).isoformat()
    total = facture.total

    lignes = [
        f'{date_str} * "Paiement facture {facture.numero} - {facture.nom_client}"',
        f"  Actifs:Banque:RBC:Cheques  {total} CAD",
        f"  Actifs:ComptesClients  -{total} CAD",
    ]

    return "\n".join(lignes)


def generer_ecriture_paiement_partiel(
    facture: Facture,
    montant: Decimal,
    date_paiement: datetime.date | None = None,
) -> str:
    """Genere l'ecriture Beancount pour un paiement partiel.

    Debit: Actifs:Banque:RBC:Cheques (montant)
    Credit: Actifs:ComptesClients (-montant)
    """
    date_str = (date_paiement or facture.date).isoformat()

    lignes = [
        f'{date_str} * "Paiement partiel facture {facture.numero} - {facture.nom_client}"',
        f"  Actifs:Banque:RBC:Cheques  {montant} CAD",
        f"  Actifs:ComptesClients  -{montant} CAD",
    ]

    return "\n".join(lignes)
