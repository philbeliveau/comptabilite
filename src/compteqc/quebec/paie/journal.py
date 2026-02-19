"""Generation de transactions Beancount a partir d'un ResultatPaie.

Cree une transaction complete avec ~20 postings pour une periode de paie,
utilisant les sous-comptes de passifs pour le suivi YTD.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from beancount.core import data

from compteqc.quebec.paie.moteur import ResultatPaie


def generer_transaction_paie(
    date_paie: datetime.date,
    resultat: ResultatPaie,
    salary_offset: Decimal | None = None,
) -> data.Transaction:
    """Genere une transaction Beancount complete pour une periode de paie.

    Args:
        date_paie: Date de la paie.
        resultat: ResultatPaie avec toutes les retenues et cotisations.
        salary_offset: Montant optionnel a appliquer contre le pret actionnaire.
            Si fourni, reduit le depot bancaire net d'autant.

    Returns:
        Transaction Beancount avec ~20 postings, equilibree a zero.

    Raises:
        ValueError: Si salary_offset > net pay.
    """
    if salary_offset is not None and salary_offset > resultat.net:
        raise ValueError(
            f"salary_offset ({salary_offset}) ne peut pas depasser "
            f"le salaire net ({resultat.net})"
        )

    meta = data.new_metadata("<paie>", 0)
    meta["type"] = "paie"
    meta["periode"] = str(resultat.numero_periode)
    meta["brut"] = str(resultat.brut)
    if salary_offset is not None and salary_offset > Decimal("0"):
        meta["salary_offset"] = str(salary_offset)

    narration = (
        f"Paie #{resultat.numero_periode} - "
        f"Salaire brut {resultat.brut} CAD"
    )

    txn = data.Transaction(
        meta=meta,
        date=date_paie,
        flag="*",
        payee=None,
        narration=narration,
        tags=frozenset({"paie"}),
        links=frozenset(),
        postings=[],
    )

    cad = "CAD"

    # --- Depense: Salaire brut ---
    _ajouter_posting(txn, "Depenses:Salaires:Brut", resultat.brut, cad)

    # --- Retenues employe (credits aux passifs) ---
    _ajouter_posting(txn, "Passifs:Retenues:QPP-Base", -resultat.qpp_base, cad)
    _ajouter_posting(
        txn, "Passifs:Retenues:QPP-Supp1", -resultat.qpp_supp1, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Retenues:QPP-Supp2", -resultat.qpp_supp2, cad,
    )
    _ajouter_posting(txn, "Passifs:Retenues:RQAP", -resultat.rqap, cad)
    _ajouter_posting(txn, "Passifs:Retenues:AE", -resultat.ae, cad)
    _ajouter_posting(
        txn, "Passifs:Retenues:Impot-Federal", -resultat.impot_federal, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Retenues:Impot-Quebec", -resultat.impot_quebec, cad,
    )

    # --- Depot bancaire (net ou net - offset) ---
    depot = resultat.net
    if salary_offset is not None and salary_offset > Decimal("0"):
        depot = resultat.net - salary_offset
    _ajouter_posting(txn, "Actifs:Banque:RBC:Cheques", -depot, cad)

    # --- Compensation pret actionnaire (si applicable) ---
    # Credit au passif: reduit le solde debiteur du pret actionnaire
    # (le salaire net est applique contre le pret au lieu d'etre verse en banque)
    if salary_offset is not None and salary_offset > Decimal("0"):
        _ajouter_posting(
            txn, "Passifs:Pret-Actionnaire", -salary_offset, cad,
        )

    # --- Depenses: Cotisations employeur ---
    rrq_empl_total = (
        resultat.qpp_base_employeur
        + resultat.qpp_supp1_employeur
        + resultat.qpp_supp2_employeur
    )
    _ajouter_posting(
        txn, "Depenses:Salaires:RRQ-Employeur", rrq_empl_total, cad,
    )
    _ajouter_posting(
        txn, "Depenses:Salaires:RQAP-Employeur", resultat.rqap_employeur, cad,
    )
    _ajouter_posting(
        txn, "Depenses:Salaires:AE-Employeur", resultat.ae_employeur, cad,
    )
    _ajouter_posting(txn, "Depenses:Salaires:FSS", resultat.fss, cad)
    _ajouter_posting(txn, "Depenses:Salaires:CNESST", resultat.cnesst, cad)
    _ajouter_posting(
        txn, "Depenses:Salaires:Normes-Travail", resultat.normes_travail, cad,
    )

    # --- Passifs: Cotisations employeur ---
    _ajouter_posting(
        txn, "Passifs:Cotisations-Employeur:QPP", -rrq_empl_total, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Cotisations-Employeur:RQAP",
        -resultat.rqap_employeur, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Cotisations-Employeur:AE",
        -resultat.ae_employeur, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Cotisations-Employeur:FSS", -resultat.fss, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Cotisations-Employeur:CNESST", -resultat.cnesst, cad,
    )
    _ajouter_posting(
        txn, "Passifs:Cotisations-Employeur:Normes-Travail",
        -resultat.normes_travail, cad,
    )

    return txn


def _ajouter_posting(
    txn: data.Transaction,
    compte: str,
    montant: Decimal,
    devise: str,
) -> None:
    """Ajoute un posting a la transaction (helper)."""
    data.create_simple_posting(txn, compte, montant, devise)
