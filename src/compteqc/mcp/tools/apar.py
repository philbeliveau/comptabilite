"""Outils MCP pour la gestion des comptes a payer et a recevoir (AP/AR).

Outils: ap_list, ap_add, ap_pay, ar_aging, ap_aging, apar_summary.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from compteqc.mcp.server import AppContext, mcp
from compteqc.mcp.services import formater_montant


@mcp.tool()
def ap_list(
    statut: str | None = None,
    fournisseur: str | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Lister les factures fournisseurs (comptes a payer).

    Filtre optionnel par statut (received/approved/paid/partial/disputed)
    et/ou par sous-chaine du nom fournisseur (insensible a la casse).
    Limite a 50 resultats.

    Args:
        statut: Filtrer par statut (received, approved, paid, partial, disputed).
        fournisseur: Filtrer par sous-chaine du nom fournisseur.
    """
    from compteqc.fournisseurs.registre import RegistreFournisseurs
    from compteqc.fournisseurs.modeles import BillStatus

    registre = RegistreFournisseurs()
    if statut:
        try:
            bill_status = BillStatus(statut.lower())
        except ValueError:
            return {"erreur": f"Statut invalide: {statut}. Valeurs: received, approved, paid, partial, disputed"}
        factures = registre.lister(statut=bill_status)
    else:
        factures = registre.lister()

    if fournisseur:
        filtre = fournisseur.lower()
        factures = [f for f in factures if filtre in f.fournisseur.lower()]

    resultats = []
    for f in factures[:50]:
        resultats.append({
            "numero_interne": f.numero_interne,
            "fournisseur": f.fournisseur,
            "numero_reference": f.numero_reference,
            "date_facture": f.date_facture.isoformat(),
            "date_echeance": f.date_echeance.isoformat(),
            "montant_ht": formater_montant(f.montant_ht),
            "tps": formater_montant(f.tps),
            "tvq": formater_montant(f.tvq),
            "total": formater_montant(f.total),
            "montant_paye": formater_montant(f.montant_paye),
            "solde": formater_montant(f.solde),
            "statut": f.statut.value,
        })

    return {
        "nb_factures": len(resultats),
        "factures": resultats,
        "tronque": len(factures) > 50,
    }


@mcp.tool()
def ap_add(
    fournisseur: str,
    numero_reference: str,
    montant_ht: str,
    categorie_depense: str,
    date_facture: str,
    date_echeance: str,
    tps_applicable: bool = True,
    tvq_applicable: bool = True,
    taux_itc: str = "1.0",
    taux_itr: str = "1.0",
    notes: str = "",
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Creer une nouvelle facture fournisseur (compte a payer).

    Cree la facture dans le registre YAML et genere l'ecriture Beancount.
    Pour des lignes multiples, utiliser l'interface web.

    Args:
        fournisseur: Nom du fournisseur (ex: "Cabinet Comptable XYZ").
        numero_reference: Numero de facture du fournisseur (ex: "INV-2026-042").
        montant_ht: Montant hors taxes en CAD (ex: "1000.00").
        categorie_depense: Compte de depense (ex: "Depenses:Honoraires-Professionnels:Comptable").
        date_facture: Date de la facture (format AAAA-MM-JJ).
        date_echeance: Date d'echeance (format AAAA-MM-JJ).
        tps_applicable: TPS applicable sur cette facture (defaut: true).
        tvq_applicable: TVQ applicable sur cette facture (defaut: true).
        taux_itc: Taux ITC (1.0 = 100%, 0.5 = 50% pour repas). Defaut: 1.0.
        taux_itr: Taux ITR (1.0 = 100%, 0.5 = 50% pour repas). Defaut: 1.0.
        notes: Notes optionnelles.
    """
    from compteqc.fournisseurs.modeles import (
        FactureFournisseur, LigneFactureFournisseur, BillStatus
    )
    from compteqc.fournisseurs.registre import RegistreFournisseurs
    from compteqc.fournisseurs.journal import generer_ecriture_facture_fournisseur

    app = ctx.request_context.lifespan_context
    if app.read_only:
        return {"erreur": "Mode lecture seule -- impossible de creer une facture fournisseur."}

    registre = RegistreFournisseurs()
    dt_facture = datetime.date.fromisoformat(date_facture)
    dt_echeance = datetime.date.fromisoformat(date_echeance)
    numero_interne = registre.prochain_numero(dt_facture.year)

    ligne = LigneFactureFournisseur(
        description=f"Facture {numero_reference} - {fournisseur}",
        montant=Decimal(montant_ht),
        categorie_depense=categorie_depense,
        tps_applicable=tps_applicable,
        tvq_applicable=tvq_applicable,
        taux_itc=Decimal(taux_itc),
        taux_itr=Decimal(taux_itr),
    )

    bill = FactureFournisseur(
        numero_reference=numero_reference,
        numero_interne=numero_interne,
        fournisseur=fournisseur,
        date_facture=dt_facture,
        date_echeance=dt_echeance,
        lignes=[ligne],
        statut=BillStatus.RECEIVED,
        notes=notes,
    )

    registre.ajouter(bill)

    # Generate and append journal entry
    ecriture = generer_ecriture_facture_fournisseur(bill)
    journal_path = Path("ledger/fournisseurs/journal.beancount")
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with open(journal_path, "a", encoding="utf-8") as f:
        f.write("\n" + ecriture + "\n")

    # Reload ledger
    app.reload()

    return {
        "succes": True,
        "numero_interne": numero_interne,
        "fournisseur": fournisseur,
        "total": formater_montant(bill.total),
        "ecriture_apercu": ecriture[:300],
    }


@mcp.tool()
def ap_pay(
    numero_interne: str,
    montant: str | None = None,
    methode_paiement: str = "virement",
    date_paiement: str | None = None,
    ctx: Context[ServerSession, AppContext] = None,
) -> dict:
    """Enregistrer le paiement d'une facture fournisseur.

    Paiement complet par defaut. Si montant est specifie, paiement partiel.
    Met a jour le statut (PAID ou PARTIAL) et genere l'ecriture de paiement.

    Args:
        numero_interne: Numero interne de la facture (ex: "FOUR-2026-001").
        montant: Montant du paiement en CAD (defaut: solde restant = paiement complet).
        methode_paiement: Methode de paiement (virement, cheque, carte-credit). Defaut: virement.
        date_paiement: Date du paiement (format AAAA-MM-JJ, defaut: aujourd'hui).
    """
    from compteqc.fournisseurs.registre import RegistreFournisseurs
    from compteqc.fournisseurs.modeles import BillStatus
    from compteqc.fournisseurs.journal import generer_ecriture_paiement_fournisseur

    app = ctx.request_context.lifespan_context
    if app.read_only:
        return {"erreur": "Mode lecture seule -- impossible d'enregistrer un paiement."}

    registre = RegistreFournisseurs()
    bill = registre.obtenir(numero_interne)
    if not bill:
        return {"erreur": f"Facture fournisseur {numero_interne} introuvable."}

    dt_paiement = datetime.date.fromisoformat(date_paiement) if date_paiement else datetime.date.today()
    montant_paiement = Decimal(montant) if montant else bill.solde

    if montant_paiement <= 0:
        return {"erreur": "Le montant du paiement doit etre positif."}
    if montant_paiement > bill.solde:
        return {"erreur": f"Le montant ({montant_paiement}) depasse le solde ({bill.solde})."}

    nouveau_montant_paye = bill.montant_paye + montant_paiement
    nouveau_solde = bill.total - nouveau_montant_paye
    nouveau_statut = BillStatus.PAID if nouveau_solde <= 0 else BillStatus.PARTIAL

    registre.mettre_a_jour_statut(
        numero_interne=numero_interne,
        statut=nouveau_statut,
        date_paiement=dt_paiement,
        montant_paye=nouveau_montant_paye,
        methode_paiement=methode_paiement,
    )

    # Generate payment journal entry
    ecriture = generer_ecriture_paiement_fournisseur(bill, montant_paiement, methode_paiement, dt_paiement)
    journal_path = Path("ledger/fournisseurs/journal.beancount")
    with open(journal_path, "a", encoding="utf-8") as f:
        f.write("\n" + ecriture + "\n")

    app.reload()

    return {
        "succes": True,
        "numero_interne": numero_interne,
        "montant_paye": formater_montant(montant_paiement),
        "nouveau_solde": formater_montant(nouveau_solde),
        "statut": nouveau_statut.value,
    }
