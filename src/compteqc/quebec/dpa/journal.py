"""Generation de transactions Beancount pour la DPA (amortissement).

Chaque classe DPA genere une transaction distincte:
- Dr Depenses:Amortissement (montant DPA)
- Cr Actifs:Immobilisations:Amortissement-Cumule (montant DPA)

Les transactions sont marquees '!' (needs review) car la DPA est discretionnaire:
le contribuable peut choisir de ne pas la reclamer ou de reclamer un montant partiel.
"""

from datetime import date
from decimal import Decimal

from beancount.core import amount, data
from beancount.core.number import D

from compteqc.quebec.dpa.calcul import PoolDPA
from compteqc.quebec.dpa.classes import CLASSES_DPA

META_SOURCE = {"source": "compteqc-dpa"}


def generer_transactions_dpa(
    pools: dict[int, PoolDPA],
    date_fin_exercice: date,
) -> list[data.Transaction]:
    """Genere les transactions Beancount de DPA pour chaque classe.

    Args:
        pools: Pools DPA calcules pour l'annee
        date_fin_exercice: Date de fin d'exercice (ex: 2026-12-31)

    Returns:
        Liste de transactions Beancount (une par classe avec DPA > 0,
        plus des transactions de recapture si applicable)
    """
    transactions = []

    for classe in sorted(pools.keys()):
        pool = pools[classe]
        dpa = pool.calculer_dpa()
        desc = CLASSES_DPA.get(classe, {}).get("description", f"Classe {classe}")

        # Transaction de DPA (amortissement)
        if dpa > Decimal("0.00"):
            meta = data.new_metadata("<compteqc-dpa>", 0)
            meta.update(META_SOURCE)
            meta["classe_dpa"] = str(classe)
            meta["taux"] = str(pool.taux)
            meta["ucc_ouverture"] = str(pool.ucc_ouverture)
            meta["ucc_fermeture"] = str(pool.ucc_fermeture)

            postings = [
                data.Posting(
                    account="Depenses:Amortissement",
                    units=amount.Amount(D(str(dpa)), "CAD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta=None,
                ),
                data.Posting(
                    account="Actifs:Immobilisations:Amortissement-Cumule",
                    units=amount.Amount(-D(str(dpa)), "CAD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta=None,
                ),
            ]

            txn = data.Transaction(
                meta=meta,
                date=date_fin_exercice,
                flag="!",
                payee=None,
                narration=f"DPA classe {classe} - {desc}",
                tags=frozenset({"dpa"}),
                links=frozenset(),
                postings=postings,
            )
            transactions.append(txn)

        # Transaction de recapture (ajoutee au revenu)
        recapture = pool.recapture
        if recapture > Decimal("0.00"):
            meta_recap = data.new_metadata("<compteqc-dpa>", 0)
            meta_recap.update(META_SOURCE)
            meta_recap["classe_dpa"] = str(classe)
            meta_recap["type"] = "recapture"

            postings_recap = [
                data.Posting(
                    account="Actifs:Immobilisations:Amortissement-Cumule",
                    units=amount.Amount(D(str(recapture)), "CAD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta=None,
                ),
                data.Posting(
                    account="Revenus:Autres",
                    units=amount.Amount(-D(str(recapture)), "CAD"),
                    cost=None,
                    price=None,
                    flag=None,
                    meta=None,
                ),
            ]

            txn_recap = data.Transaction(
                meta=meta_recap,
                date=date_fin_exercice,
                flag="!",
                payee=None,
                narration=f"Recapture DPA classe {classe} - {desc}",
                tags=frozenset({"dpa", "recapture"}),
                links=frozenset(),
                postings=postings_recap,
            )
            transactions.append(txn_recap)

    return transactions
