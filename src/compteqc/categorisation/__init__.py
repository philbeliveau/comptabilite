"""Module de categorisation automatique pour CompteQC."""

from __future__ import annotations

import copy

from beancount.core import data

from compteqc.categorisation.moteur import MoteurRegles, ResultatCategorisation

__all__ = [
    "MoteurRegles",
    "ResultatCategorisation",
    "appliquer_categorisation",
]


def appliquer_categorisation(
    transactions: list[data.Transaction], moteur: MoteurRegles
) -> list[data.Transaction]:
    """Applique la categorisation par regles aux transactions non-classees.

    Pour chaque transaction avec categorisation="non-classe" dans ses metadata,
    appelle le moteur de regles. Si une regle matche, remplace le posting
    Depenses:Non-Classe par le compte retourne.

    IMPORTANT: Cette fonction ne mute PAS les transactions originales.
    Elle cree de nouvelles instances.

    Args:
        transactions: Liste de transactions Beancount.
        moteur: Le moteur de regles a utiliser.

    Returns:
        Nouvelle liste de transactions (potentiellement categorisees).
    """
    resultat = []

    for txn in transactions:
        if not isinstance(txn, data.Transaction):
            resultat.append(txn)
            continue

        if txn.meta.get("categorisation") != "non-classe":
            resultat.append(txn)
            continue

        # Extraire payee, narration, montant du premier posting
        payee = txn.payee or ""
        narration = txn.narration or ""
        montant = txn.postings[0].units.number if txn.postings else 0

        cat = moteur.categoriser(payee, narration, montant)

        if cat.source == "non-classe":
            resultat.append(txn)
            continue

        # Creer de nouveaux postings avec le compte categorise
        nouveaux_postings = []
        for posting in txn.postings:
            if posting.account == "Depenses:Non-Classe":
                nouveau_posting = data.Posting(
                    account=cat.compte,
                    units=posting.units,
                    cost=posting.cost,
                    price=posting.price,
                    flag=posting.flag,
                    meta=posting.meta,
                )
                nouveaux_postings.append(nouveau_posting)
            else:
                nouveaux_postings.append(posting)

        # Creer une nouvelle transaction avec metadata mises a jour
        nouveau_meta = copy.copy(txn.meta)
        nouveau_meta["categorisation"] = cat.source
        nouveau_meta["regle"] = cat.regle
        nouveau_meta["confiance"] = str(cat.confiance)

        nouvelle_txn = data.Transaction(
            meta=nouveau_meta,
            date=txn.date,
            flag=txn.flag,
            payee=txn.payee,
            narration=txn.narration,
            tags=txn.tags,
            links=txn.links,
            postings=nouveaux_postings,
        )

        resultat.append(nouvelle_txn)

    return resultat
