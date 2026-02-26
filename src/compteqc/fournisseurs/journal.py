"""Generation d'ecritures Beancount pour les factures fournisseurs (AP).

Produit les ecritures de comptes fournisseurs (bill recording) et de paiement.
Gere les ITC/ITR partiels pour les depenses a eligibilite restreinte (repas a 50%).
"""

from __future__ import annotations

import datetime
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from compteqc.factures.modeles import TAUX_TPS, TAUX_TVQ, QUANTIZE_CENT
from compteqc.fournisseurs.modeles import FactureFournisseur


# Default payment account mapping
COMPTE_PAIEMENT = {
    "cheque": "Actifs:Banque:RBC:Cheques",
    "virement": "Actifs:Banque:RBC:Cheques",
    "carte-credit": "Passifs:CartesCredit:RBC",
}
COMPTE_PAIEMENT_DEFAUT = "Actifs:Banque:RBC:Cheques"


def generer_ecriture_facture_fournisseur(facture: FactureFournisseur) -> str:
    """Genere l'ecriture Beancount pour l'enregistrement d'une facture fournisseur.

    Pour chaque ligne:
      - Debite le compte de depense pour le montant HT
      - Si TPS applicable: ITC claimable -> Actifs:TPS-Payee, non-claimable -> depense
      - Si TVQ applicable: ITR claimable -> Actifs:TVQ-Payee, non-claimable -> depense
    Credite Passifs:ComptesFournisseurs pour le total (balancing amount).
    """
    postings: dict[str, Decimal] = defaultdict(Decimal)

    for ligne in facture.lignes:
        # Pre-tax amount -> debit expense
        postings[ligne.categorie_depense] += ligne.montant

        # GST / ITC
        if ligne.tps_applicable:
            full_gst = (ligne.montant * TAUX_TPS).quantize(
                QUANTIZE_CENT, rounding=ROUND_HALF_UP
            )
            claimable_itc = (full_gst * ligne.taux_itc).quantize(
                QUANTIZE_CENT, rounding=ROUND_HALF_UP
            )
            non_claimable_gst = full_gst - claimable_itc
            if claimable_itc > 0:
                postings["Actifs:TPS-Payee"] += claimable_itc
            if non_claimable_gst > 0:
                postings[ligne.categorie_depense] += non_claimable_gst

        # QST / ITR
        if ligne.tvq_applicable:
            full_qst = (ligne.montant * TAUX_TVQ).quantize(
                QUANTIZE_CENT, rounding=ROUND_HALF_UP
            )
            claimable_itr = (full_qst * ligne.taux_itr).quantize(
                QUANTIZE_CENT, rounding=ROUND_HALF_UP
            )
            non_claimable_qst = full_qst - claimable_itr
            if claimable_itr > 0:
                postings["Actifs:TVQ-Payee"] += claimable_itr
            if non_claimable_qst > 0:
                postings[ligne.categorie_depense] += non_claimable_qst

    # Round all postings to the cent
    for account in postings:
        postings[account] = postings[account].quantize(
            QUANTIZE_CENT, rounding=ROUND_HALF_UP
        )

    # AP credit is the balancing amount (negative sum of all debits)
    total_debits = sum(postings.values())
    postings["Passifs:ComptesFournisseurs"] = -total_debits

    # Build Beancount entry
    date_str = facture.date_facture.isoformat()
    narration = (
        f"Facture fournisseur {facture.numero_interne} - {facture.fournisseur}"
    )

    lines = [f'{date_str} * "{narration}"']

    # Sort accounts for deterministic output: expenses first, then assets, then liabilities
    def _sort_key(item: tuple[str, Decimal]) -> tuple[int, str]:
        account = item[0]
        if account.startswith("Depenses:"):
            return (0, account)
        if account.startswith("Actifs:"):
            return (1, account)
        return (2, account)

    for account, amount in sorted(postings.items(), key=_sort_key):
        lines.append(f"  {account}  {amount} CAD")

    return "\n".join(lines)


def generer_ecriture_paiement_fournisseur(
    facture: FactureFournisseur,
    montant: Decimal | None = None,
    methode: str | None = None,
    date_paiement: datetime.date | None = None,
) -> str:
    """Genere l'ecriture Beancount pour le paiement d'une facture fournisseur.

    Args:
        facture: La facture fournisseur a payer.
        montant: Montant du paiement. Si None, paie le solde complet.
        methode: Methode de paiement ("cheque", "virement", "carte-credit").
                 Si None, utilise facture.methode_paiement ou "cheque".
        date_paiement: Date du paiement. Si None, utilise facture.date_paiement
                       ou la date du jour.
    """
    # Determine payment amount
    if montant is None:
        montant = facture.solde

    # Determine payment method
    if methode is None:
        methode = facture.methode_paiement or "cheque"

    # Determine payment date
    if date_paiement is None:
        date_paiement = facture.date_paiement or datetime.date.today()

    # Determine credit account
    compte_credit = COMPTE_PAIEMENT.get(methode, COMPTE_PAIEMENT_DEFAUT)

    # Determine if partial
    is_partial = montant < facture.total

    date_str = date_paiement.isoformat()
    type_paiement = "Paiement partiel" if is_partial else "Paiement"
    narration = (
        f"{type_paiement} facture fournisseur "
        f"{facture.numero_interne} - {facture.fournisseur}"
    )

    # Round amount
    montant = montant.quantize(QUANTIZE_CENT, rounding=ROUND_HALF_UP)

    lines = [
        f'{date_str} * "{narration}"',
        f"  Passifs:ComptesFournisseurs  {montant} CAD",
        f"  {compte_credit}  -{montant} CAD",
    ]

    return "\n".join(lines)
