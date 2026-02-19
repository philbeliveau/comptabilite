"""Generation d'ecritures Beancount pour les factures.

Produit les ecritures de comptes clients (AR) et de paiement.
"""

from __future__ import annotations

from compteqc.factures.modeles import Facture


def generer_ecriture_facture(facture: Facture) -> str:
    """Genere l'ecriture Beancount pour la creation d'une facture (AR).

    Debit: Actifs:ComptesClients (total)
    Credit: Revenus:Consultation (sous-total)
    Credit: Passifs:TPS-Percue (TPS)
    Credit: Passifs:TVQ-Percue (TVQ)
    """
    date_str = facture.date.isoformat()
    total = facture.total
    sous_total = facture.sous_total
    tps = facture.tps
    tvq = facture.tvq

    lignes = [
        f'{date_str} * "Facture {facture.numero} - {facture.nom_client}"',
        f"  Actifs:ComptesClients  {total} CAD",
        f"  Revenus:Consultation  -{sous_total} CAD",
    ]

    if tps > 0:
        lignes.append(f"  Passifs:TPS-Percue  -{tps} CAD")
    if tvq > 0:
        lignes.append(f"  Passifs:TVQ-Percue  -{tvq} CAD")

    return "\n".join(lignes)


def generer_ecriture_paiement(facture: Facture) -> str:
    """Genere l'ecriture Beancount pour le paiement d'une facture.

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
