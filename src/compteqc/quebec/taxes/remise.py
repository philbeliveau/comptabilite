"""Preparation operationnelle des remises TPS/TVQ par trimestre.

Ce module produit une vue "preparation de remise" a partir des ecritures
Beancount existantes. Il ne tente pas de mapper les montants aux lignes
officielles de declaration et ne remplace pas la revue CPA.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from beancount.core import data
from dateutil.relativedelta import relativedelta

from compteqc.documents.registre import DocumentFiscal, RegistreDocumentsFiscaux
from compteqc.echeances.calendrier import _ajuster_jour_ouvrable
from compteqc.quebec.taxes.revenus import AuditRevenusTaxes, auditer_revenus_taxes
from compteqc.quebec.taxes.sommaire import (
    COMPTE_TPS_PAYEE,
    COMPTE_TPS_PERCUE,
    COMPTE_TVQ_PAYEE,
    COMPTE_TVQ_PERCUE,
    COMPTES_TAXES,
    SommairePeriode,
    generer_sommaire_periode,
    verifier_concordance_tps_tvq,
)

QUARTERS: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {
    1: ((1, 1), (3, 31)),
    2: ((4, 1), (6, 30)),
    3: ((7, 1), (9, 30)),
    4: ((10, 1), (12, 31)),
}

COMPTES_LIQUIDITE_PREFIXES = (
    "Actifs:Banque",
    "Passifs:CartesCredit",
    "Actifs:ComptesClients",
    "Passifs:ComptesFournisseurs",
)


@dataclass(frozen=True)
class PeriodeRemise:
    """Periode trimestrielle de preparation TPS/TVQ."""

    code: str
    label: str
    annee: int
    trimestre: int
    debut: datetime.date
    fin: datetime.date
    date_limite: datetime.date
    est_terminee: bool
    est_future: bool


@dataclass(frozen=True)
class LigneRemise:
    """Transaction source utile a la preparation de remise."""

    date: datetime.date
    payee: str
    narration: str
    categorie: str
    compte_reference: str
    montant_reference: Decimal
    tps: Decimal
    tvq: Decimal
    comptes_taxes: tuple[str, ...]
    remarques: tuple[str, ...]


@dataclass(frozen=True)
class AvertissementRemise:
    """Message d'alerte ou de contexte pour l'operateur."""

    niveau: str
    titre: str
    detail: str


@dataclass(frozen=True)
class PreparationRemise:
    """Vue complete pour l'onglet de preparation trimestrielle."""

    periode: PeriodeRemise
    sommaire: SommairePeriode
    audit_revenus: AuditRevenusTaxes
    lignes: tuple[LigneRemise, ...]
    lignes_collecte: tuple[LigneRemise, ...]
    lignes_intrants: tuple[LigneRemise, ...]
    lignes_ajustements: tuple[LigneRemise, ...]
    avertissements: tuple[AvertissementRemise, ...]

    @property
    def nb_collecte(self) -> int:
        return len(self.lignes_collecte)

    @property
    def nb_intrants(self) -> int:
        return len(self.lignes_intrants)

    @property
    def nb_ajustements(self) -> int:
        return len(self.lignes_ajustements)

    @property
    def nb_anomalies_revenus(self) -> int:
        return self.audit_revenus.count


def trimestre_dates(annee: int, trimestre: int) -> tuple[datetime.date, datetime.date]:
    """Retourne les dates de debut et fin d'un trimestre civil."""
    if trimestre not in QUARTERS:
        raise ValueError(f"Trimestre invalide: Q{trimestre}")
    debut_md, fin_md = QUARTERS[trimestre]
    return (
        datetime.date(annee, debut_md[0], debut_md[1]),
        datetime.date(annee, fin_md[0], fin_md[1]),
    )


def trimestre_precedent(date_reference: datetime.date | None = None) -> tuple[int, int]:
    """Retourne le dernier trimestre civil complet a preparer."""
    reference = date_reference or datetime.date.today()
    if reference.month <= 3:
        return reference.year - 1, 4
    if reference.month <= 6:
        return reference.year, 1
    if reference.month <= 9:
        return reference.year, 2
    return reference.year, 3


def construire_periode_remise(
    code: str | None = None,
    date_reference: datetime.date | None = None,
) -> PeriodeRemise:
    """Construit une periode trimestrielle a partir d'un code `YYYY-QN`."""
    reference = date_reference or datetime.date.today()

    if code:
        try:
            annee_str, trimestre_str = code.split("-Q", maxsplit=1)
            annee = int(annee_str)
            trimestre = int(trimestre_str)
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"Format de periode invalide: {code}") from exc
    else:
        annee, trimestre = trimestre_precedent(reference)

    debut, fin = trimestre_dates(annee, trimestre)
    date_limite = _ajuster_jour_ouvrable(fin + relativedelta(months=1))

    return PeriodeRemise(
        code=f"{annee}-Q{trimestre}",
        label=f"T{trimestre} {annee}",
        annee=annee,
        trimestre=trimestre,
        debut=debut,
        fin=fin,
        date_limite=date_limite,
        est_terminee=fin < reference,
        est_future=debut > reference,
    )


def lister_periodes_remise(
    entries: list,
    date_reference: datetime.date | None = None,
) -> list[PeriodeRemise]:
    """Retourne les trimestres disponibles pour la navigation Fava."""
    reference = date_reference or datetime.date.today()
    annees = {trimestre_precedent(reference)[0], reference.year}

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if any(posting.account in COMPTES_TAXES for posting in entry.postings):
            annees.add(entry.date.year)

    periodes: list[PeriodeRemise] = []
    for annee in sorted(annees, reverse=True):
        for trimestre in range(4, 0, -1):
            periodes.append(
                construire_periode_remise(
                    f"{annee}-Q{trimestre}",
                    date_reference=reference,
                )
            )
    return periodes


def preparer_remise_trimestrielle(
    entries: list,
    code_periode: str | None = None,
    date_reference: datetime.date | None = None,
    documents: list[DocumentFiscal] | None = None,
    ledger_path: str | Path | None = None,
) -> PreparationRemise:
    """Construit la vue operationnelle de preparation TPS/TVQ."""
    periode = construire_periode_remise(code_periode, date_reference)
    sommaire = generer_sommaire_periode(entries, periode.debut, periode.fin)
    if documents is None:
        try:
            registre_path = (
                Path(ledger_path).parent / "documents" / "registre.yaml"
                if ledger_path is not None
                else None
            )
            documents = RegistreDocumentsFiscaux(registre_path).lister_revenus()
        except Exception:
            documents = []
    audit_revenus = auditer_revenus_taxes(
        entries,
        documents,
        debut=periode.debut,
        fin=periode.fin,
    )

    lignes: list[LigneRemise] = []
    for entry in entries:
        ligne = _transformer_transaction(entry, periode.debut, periode.fin)
        if ligne is not None:
            lignes.append(ligne)

    lignes.sort(key=lambda ligne: (ligne.date, ligne.payee, ligne.narration))

    lignes_collecte = tuple(ligne for ligne in lignes if ligne.categorie == "collecte")
    lignes_intrants = tuple(ligne for ligne in lignes if ligne.categorie == "intrants")
    lignes_ajustements = tuple(
        ligne for ligne in lignes if ligne.categorie == "ajustements"
    )

    avertissements = tuple(
        _generer_avertissements(
            entries,
            periode,
            lignes_collecte,
            lignes_intrants,
            lignes_ajustements,
            audit_revenus,
        )
    )

    return PreparationRemise(
        periode=periode,
        sommaire=sommaire,
        audit_revenus=audit_revenus,
        lignes=tuple(lignes),
        lignes_collecte=lignes_collecte,
        lignes_intrants=lignes_intrants,
        lignes_ajustements=lignes_ajustements,
        avertissements=avertissements,
    )


def checklist_operateur_remise() -> list[dict[str, str]]:
    """Checklist neutre de preparation, inspiree des sources officielles."""
    return [
        {
            "titre": "Confirmer la periode de declaration",
            "detail": (
                "Utiliser le trimestre civil selectionne et verifier la "
                "date limite avant de preparer la remise."
            ),
        },
        {
            "titre": "Verifier les ventes taxables de la periode",
            "detail": (
                "Confirmer que les revenus du trimestre refletent bien "
                "les montants taxes percus ou percevables selon les ecritures."
            ),
        },
        {
            "titre": "Verifier les achats avec pieces justificatives",
            "detail": (
                "Confirmer que chaque CTI/RTI reclame repose sur une "
                "facture ou un recu suffisant et sur une depense liee a l'entreprise."
            ),
        },
        {
            "titre": "Examiner les ecarts et ajustements",
            "detail": (
                "Revoir les transactions avec TPS sans TVQ, TVQ sans TPS "
                "ou sans contrepartie de revenu/depense claire avant la remise."
            ),
        },
        {
            "titre": "Documenter les points incertains pour le CPA",
            "detail": (
                "Conserver les notes sur les exceptions, allocations "
                "partielles ou traitements ambigus plutot que de les traiter comme confirmes."
            ),
        },
    ]


def _transformer_transaction(
    entry: object,
    debut: datetime.date,
    fin: datetime.date,
) -> LigneRemise | None:
    if not isinstance(entry, data.Transaction):
        return None
    if entry.date < debut or entry.date > fin:
        return None

    tps = Decimal("0.00")
    tvq = Decimal("0.00")
    comptes_taxes: list[str] = []
    for posting in entry.postings:
        montant = _posting_amount(posting)
        if posting.account == COMPTE_TPS_PERCUE:
            tps += abs(montant)
            comptes_taxes.append(posting.account)
        elif posting.account == COMPTE_TVQ_PERCUE:
            tvq += abs(montant)
            comptes_taxes.append(posting.account)
        elif posting.account == COMPTE_TPS_PAYEE:
            tps += montant
            comptes_taxes.append(posting.account)
        elif posting.account == COMPTE_TVQ_PAYEE:
            tvq += montant
            comptes_taxes.append(posting.account)

    if not comptes_taxes:
        return None

    categorie, compte_reference, montant_reference, remarques = _classifier_transaction(entry)
    return LigneRemise(
        date=entry.date,
        payee=entry.payee or "",
        narration=entry.narration or "",
        categorie=categorie,
        compte_reference=compte_reference,
        montant_reference=montant_reference,
        tps=tps,
        tvq=tvq,
        comptes_taxes=tuple(sorted(set(comptes_taxes))),
        remarques=tuple(remarques),
    )


def _classifier_transaction(
    entry: data.Transaction,
) -> tuple[str, str, Decimal, list[str]]:
    revenus = [
        posting for posting in entry.postings
        if posting.account.startswith("Revenus:")
    ]
    contreparties = [
        posting for posting in entry.postings
        if posting.account not in COMPTES_TAXES
        and not posting.account.startswith(COMPTES_LIQUIDITE_PREFIXES)
    ]
    depenses_ou_actifs = [
        posting for posting in contreparties
        if posting.account.startswith("Depenses:")
        or posting.account.startswith("Actifs:Immobilisations")
        or posting.account.startswith("Actifs:Prepaye")
    ]

    remarques: list[str] = []
    if revenus:
        compte = revenus[0].account
        montant = sum(abs(_posting_amount(posting)) for posting in revenus)
        return "collecte", compte, montant, remarques

    if depenses_ou_actifs:
        compte = depenses_ou_actifs[0].account
        montant = sum(abs(_posting_amount(posting)) for posting in depenses_ou_actifs)
        return "intrants", compte, montant, remarques

    compte = contreparties[0].account if contreparties else "Revue manuelle"
    montant = sum(abs(_posting_amount(posting)) for posting in contreparties)
    remarques.append("Contrepartie non classee automatiquement")
    return "ajustements", compte, montant, remarques


def _generer_avertissements(
    entries: list,
    periode: PeriodeRemise,
    lignes_collecte: tuple[LigneRemise, ...],
    lignes_intrants: tuple[LigneRemise, ...],
    lignes_ajustements: tuple[LigneRemise, ...],
    audit_revenus: AuditRevenusTaxes,
) -> list[AvertissementRemise]:
    avertissements: list[AvertissementRemise] = []

    if not periode.est_terminee:
        avertissements.append(
            AvertissementRemise(
                niveau="attention",
                titre="Periode non terminee",
                detail=(
                    "Le trimestre selectionne n'est pas encore complet. "
                    "Les montants peuvent changer avant la date limite."
                ),
            )
        )

    if not lignes_collecte and not lignes_intrants and not lignes_ajustements:
        avertissements.append(
            AvertissementRemise(
                niveau="info",
                titre="Aucune ecriture de taxe detectee",
                detail=(
                    "Aucune transaction avec comptes TPS/TVQ n'a ete detectee "
                    "dans la periode selectionnee."
                ),
            )
        )

    divergences = [
        divergence
        for divergence in verifier_concordance_tps_tvq(entries, periode.annee)
        if periode.debut <= divergence["date"] <= periode.fin
    ]
    if divergences:
        avertissements.append(
            AvertissementRemise(
                niveau="attention",
                titre="Transactions TPS/TVQ asymetriques",
                detail=(
                    f"{len(divergences)} transaction(s) de la periode ont de la TPS sans TVQ, "
                    "ou l'inverse. Revue manuelle recommandee."
                ),
            )
        )

    if lignes_ajustements:
        avertissements.append(
            AvertissementRemise(
                niveau="attention",
                titre="Ajustements ou remises a revoir",
                detail=(
                    f"{len(lignes_ajustements)} transaction(s) avec comptes de taxes n'ont pas "
                    "de contrepartie de revenu ou de depense clairement identifiable."
                ),
            )
        )

    if audit_revenus.count:
        avertissements.append(
            AvertissementRemise(
                niveau="attention",
                titre="Revenus sans split fiscal explicite",
                detail=(
                    f"{audit_revenus.count} element(s) de revenu du trimestre restent a revoir. "
                    "Les totaux de remise affiches n'incluent que les ecritures deja normalisees "
                    "dans le ledger."
                ),
            )
        )

    lignes_taxe = lignes_collecte + lignes_intrants + lignes_ajustements
    if any(not ligne.payee and not ligne.narration for ligne in lignes_taxe):
        avertissements.append(
            AvertissementRemise(
                niveau="info",
                titre="Description incomplete",
                detail=(
                    "Au moins une transaction de taxe n'a ni payee ni narration. "
                    "La piste d'audit peut etre insuffisante."
                ),
            )
        )

    avertissements.append(
            AvertissementRemise(
                niveau="info",
                titre="Portee de l'onglet",
                detail=(
                    "Cet onglet prepare la remise a partir du ledger. Il ne verifie pas "
                    "la suffisance documentaire CTI/RTI et ne constitue pas "
                    "une transmission officielle."
                ),
            )
        )
    return avertissements


def _posting_amount(posting: data.Posting) -> Decimal:
    if posting.units is None:
        return Decimal("0.00")
    return Decimal(str(posting.units.number))
