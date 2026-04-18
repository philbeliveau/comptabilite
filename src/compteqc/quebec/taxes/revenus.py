"""Normalisation fiscale des encaissements de revenus.

Ce module centralise:
- le calcul TPS/TVQ a partir d'un document de revenu
- l'analyse des depots bancaires bruts de revenus
- la preparation de la reecriture Beancount d'un encaissement
- les anomalies partagees entre Fava, MCP et rapports
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from beancount.core import data
from beancount.core.amount import Amount
from beancount.parser import printer

from compteqc.documents.registre import DocumentFiscal
from compteqc.factures.modeles import QUANTIZE_CENT, TAUX_TPS, TAUX_TVQ
from compteqc.quebec.taxes.calcul import appliquer_taxes, extraire_taxes_selon_traitement
from compteqc.quebec.taxes.sommaire import COMPTE_TPS_PERCUE, COMPTE_TVQ_PERCUE, COMPTES_TAXES
from compteqc.quebec.taxes.traitement import (
    charger_regles_taxes,
    determiner_traitement_revenu,
)

SEUIL_CORRESPONDANCE_REVENUS = 0.5
SEUIL_NORMALISATION_AUTOMATIQUE = 0.85
PREFIXES_BANQUE = ("Actifs:Banque",)
MOTS_REMBourseMENT = ("rembours", "refund", "reimb", "reimbursement")


@dataclass(frozen=True)
class ResumeTaxesRevenu:
    """Montants normalises d'un document de revenu."""

    sous_total: Decimal
    tps: Decimal
    tvq: Decimal
    total: Decimal
    traitement: str


@dataclass(frozen=True)
class CorrespondanceRevenu:
    """Depot bancaire candidat pour un document de revenu."""

    transaction_ref: str
    date: datetime.date
    payee: str
    narration: str
    montant: Decimal
    score: float
    already_normalized: bool
    needs_review: bool
    review_reason: str | None


@dataclass(frozen=True)
class ResultatNormalisationRevenu:
    """Resultat prepare pour l'action de normalisation."""

    status: str
    transaction_ref: str | None
    resume: ResumeTaxesRevenu | None
    review_reason: str | None
    entry_source: str | None = None


@dataclass(frozen=True)
class AnomalieRevenuTaxe:
    """Point d'attention pour coherence revenus/taxes."""

    type: str
    niveau: str
    titre: str
    detail: str
    date: datetime.date | None = None
    transaction_ref: str | None = None
    document_id: str | None = None


@dataclass(frozen=True)
class AuditRevenusTaxes:
    """Etat partage des anomalies de revenus/taxes."""

    anomalies: tuple[AnomalieRevenuTaxe, ...]

    @property
    def count(self) -> int:
        return len(self.anomalies)

    @property
    def needs_review_count(self) -> int:
        return len(
            [anomalie for anomalie in self.anomalies if anomalie.niveau in {"attention", "erreur"}]
        )


@dataclass(frozen=True)
class AnalyseTransactionRevenu:
    """Lecture structurelle d'une transaction de revenu."""

    est_depot_revenu: bool
    transaction_ref: str
    montant_banque: Decimal
    compte_banque: str | None
    comptes_revenus: tuple[str, ...]
    a_taxes: bool
    semble_remboursement: bool
    raison_revue: str | None


def transaction_reference(entry: data.Transaction) -> str:
    """Reference stable d'une transaction a partir de sa position source."""
    fichier = str(entry.meta.get("filename", ""))
    ligne = str(entry.meta.get("lineno", ""))
    return f"{fichier}:{ligne}"


def date_document(document: DocumentFiscal) -> datetime.date | None:
    """Date effective d'un document pour filtrage de periode."""
    try:
        return datetime.date.fromisoformat(document.date)
    except (TypeError, ValueError):
        return document.created_at.date() if document.created_at else None


def determiner_traitement_document_revenu(document: DocumentFiscal) -> str:
    """Determine le traitement fiscal du revenu selon les regles clients."""
    regles = charger_regles_taxes("rules/taxes.yaml")
    return determiner_traitement_revenu(document.fournisseur, document.description or "", regles)


def calculer_resume_taxes_revenu(document: DocumentFiscal) -> ResultatNormalisationRevenu:
    """Calcule le split HT/TPS/TVQ d'un document de revenu."""
    if document.pricing_mode == "unknown":
        return ResultatNormalisationRevenu(
            status="matched_needs_review",
            transaction_ref=document.matched_transaction_ref,
            resume=None,
            review_reason="Mode de prix non confirme; impossible d'inferer le split de taxes.",
        )

    traitement_regles = determiner_traitement_document_revenu(document)
    if document.pricing_mode == "explicit_tax_lines":
        if document.montant_tps is None and document.montant_tvq is None:
            return ResultatNormalisationRevenu(
                status="matched_needs_review",
                transaction_ref=document.matched_transaction_ref,
                resume=None,
                review_reason=(
                    "Aucune ligne TPS/TVQ extraite du document; impossible de confirmer "
                    "un split fiscal explicite."
                ),
            )
        tps = _q(document.montant_tps or Decimal("0"))
        tvq = _q(document.montant_tvq or Decimal("0"))
        sous_total = _q(document.sous_total)
        total = _q(document.total)
        if (
            traitement_regles == "tps_tvq"
            and (document.montant_tps is None or document.montant_tvq is None)
            and (tps > 0 or tvq > 0)
        ):
            return ResultatNormalisationRevenu(
                status="matched_needs_review",
                transaction_ref=document.matched_transaction_ref,
                resume=None,
                review_reason=(
                    "Une des lignes TPS/TVQ extraites semble incomplete pour un revenu "
                    "normalement taxe; revue manuelle requise."
                ),
            )
        if abs((sous_total + tps + tvq) - total) > Decimal("0.02"):
            return ResultatNormalisationRevenu(
                status="matched_needs_review",
                transaction_ref=document.matched_transaction_ref,
                resume=None,
                review_reason=(
                    "Les montants explicites du document ne totalisent pas le montant final. "
                    "Revue manuelle requise."
                ),
            )
        traitement = _traitement_depuis_montants(tps, tvq)
        return ResultatNormalisationRevenu(
            status="matched_and_normalized",
            transaction_ref=document.matched_transaction_ref,
            resume=ResumeTaxesRevenu(
                sous_total=sous_total,
                tps=tps,
                tvq=tvq,
                total=total,
                traitement=traitement,
            ),
            review_reason=None,
        )

    if document.pricing_mode == "tax_included":
        sous_total, tps, tvq = extraire_taxes_selon_traitement(
            _q(document.total),
            traitement_regles,
            TAUX_TPS,
            TAUX_TVQ,
        )
        return ResultatNormalisationRevenu(
            status="matched_and_normalized",
            transaction_ref=document.matched_transaction_ref,
            resume=ResumeTaxesRevenu(
                sous_total=_q(sous_total),
                tps=_q(tps),
                tvq=_q(tvq),
                total=_q(document.total),
                traitement=traitement_regles,
            ),
            review_reason=None,
        )

    if document.pricing_mode == "pre_tax":
        resume = _appliquer_taxes_selon_traitement(_q(document.sous_total), traitement_regles)
        return ResultatNormalisationRevenu(
            status="matched_and_normalized",
            transaction_ref=document.matched_transaction_ref,
            resume=resume,
            review_reason=None,
        )

    return ResultatNormalisationRevenu(
        status="matched_needs_review",
        transaction_ref=document.matched_transaction_ref,
        resume=None,
        review_reason="Mode de prix non supporte.",
    )


def proposer_correspondances_revenu(
    document: DocumentFiscal,
    entries: Iterable[object],
    seuil: float = SEUIL_CORRESPONDANCE_REVENUS,
) -> list[CorrespondanceRevenu]:
    """Trouve les depots bancaires susceptibles de correspondre au document."""
    doc_date = date_document(document)
    resume_resultat = calculer_resume_taxes_revenu(document)
    montant_cible = (
        resume_resultat.resume.total
        if resume_resultat.resume is not None
        else _q(document.total)
    )
    correspondances: list[CorrespondanceRevenu] = []

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue

        analyse = analyser_transaction_revenu(entry)
        if not analyse.est_depot_revenu:
            continue

        score = _score_correspondance(montant_cible, doc_date, analyse.montant_banque, entry.date)
        if score < seuil:
            continue

        already_normalized = False
        review_reason = analyse.raison_revue
        if review_reason is None and analyse.a_taxes:
            if (
                resume_resultat.resume is not None
                and _transaction_est_normalisee(entry, resume_resultat.resume)
            ):
                already_normalized = True
            else:
                review_reason = (
                    "La transaction contient deja des comptes de taxes mais le split "
                    "ne concorde pas avec le document."
                )

        correspondances.append(
            CorrespondanceRevenu(
                transaction_ref=analyse.transaction_ref,
                date=entry.date,
                payee=entry.payee or "",
                narration=entry.narration or "",
                montant=analyse.montant_banque,
                score=round(score, 3),
                already_normalized=already_normalized,
                needs_review=bool(review_reason),
                review_reason=review_reason,
            )
        )

    correspondances.sort(key=lambda item: item.score, reverse=True)
    return correspondances[:5]


def analyser_transaction_revenu(entry: data.Transaction) -> AnalyseTransactionRevenu:
    """Analyse si une transaction est un encaissement de revenu candidat."""
    banque = [
        posting
        for posting in entry.postings
        if posting.account.startswith(PREFIXES_BANQUE)
        and posting.units is not None
        and Decimal(str(posting.units.number)) > 0
    ]
    revenus = [
        posting for posting in entry.postings
        if posting.account.startswith("Revenus:")
    ]
    a_taxes = any(posting.account in COMPTES_TAXES for posting in entry.postings)
    autres = [
        posting
        for posting in entry.postings
        if posting not in banque and posting not in revenus and posting.account not in COMPTES_TAXES
    ]

    raison_revue = None
    if len(revenus) != 1:
        raison_revue = "La transaction n'a pas une seule contrepartie de revenu."
    elif autres:
        raison_revue = (
            "La transaction contient d'autres contreparties; "
            "normalisation manuelle requise."
        )

    texte = " ".join(
        str(valeur)
        for valeur in (
            entry.payee or "",
            entry.narration or "",
            entry.meta.get("note", ""),
        )
    ).lower()
    semble_remboursement = any(mot in texte for mot in MOTS_REMBourseMENT)
    if semble_remboursement:
        raison_revue = (
            "La transaction ressemble a un remboursement ou pass-through client; "
            "ne pas normaliser automatiquement."
        )

    montant_banque = sum((_posting_number(posting) for posting in banque), Decimal("0"))
    return AnalyseTransactionRevenu(
        est_depot_revenu=bool(banque and revenus),
        transaction_ref=transaction_reference(entry),
        montant_banque=_q(montant_banque),
        compte_banque=banque[0].account if banque else None,
        comptes_revenus=tuple(posting.account for posting in revenus),
        a_taxes=a_taxes,
        semble_remboursement=semble_remboursement,
        raison_revue=raison_revue,
    )


def preparer_normalisation_transaction_revenu(
    document: DocumentFiscal,
    entry: data.Transaction,
    score: float | None = None,
) -> ResultatNormalisationRevenu:
    """Prepare la reecriture d'une transaction selon le document de revenu."""
    resume_resultat = calculer_resume_taxes_revenu(document)
    if resume_resultat.resume is None:
        return resume_resultat

    analyse = analyser_transaction_revenu(entry)
    if not analyse.est_depot_revenu:
        return ResultatNormalisationRevenu(
            status="matched_needs_review",
            transaction_ref=analyse.transaction_ref,
            resume=resume_resultat.resume,
            review_reason="La transaction cible n'est pas un depot bancaire de revenu compatible.",
        )

    if analyse.raison_revue:
        return ResultatNormalisationRevenu(
            status="matched_needs_review",
            transaction_ref=analyse.transaction_ref,
            resume=resume_resultat.resume,
            review_reason=analyse.raison_revue,
        )

    if analyse.a_taxes:
        if _transaction_est_normalisee(entry, resume_resultat.resume):
            return ResultatNormalisationRevenu(
                status="already_normalized",
                transaction_ref=analyse.transaction_ref,
                resume=resume_resultat.resume,
                review_reason=None,
            )
        return ResultatNormalisationRevenu(
            status="matched_needs_review",
            transaction_ref=analyse.transaction_ref,
            resume=resume_resultat.resume,
            review_reason=(
                "La transaction contient deja des comptes de taxes mais le split "
                "ne concorde pas avec le document."
            ),
        )

    if score is not None and score < SEUIL_NORMALISATION_AUTOMATIQUE:
        return ResultatNormalisationRevenu(
            status="matched_needs_review",
            transaction_ref=analyse.transaction_ref,
            resume=resume_resultat.resume,
            review_reason=(
                f"Score de correspondance insuffisant ({round(score * 100)} %). "
                "Confirmer manuellement avant reecriture."
            ),
        )

    entry_source = construire_transaction_normalisee(entry, document, resume_resultat.resume)
    return ResultatNormalisationRevenu(
        status="matched_and_normalized",
        transaction_ref=analyse.transaction_ref,
        resume=resume_resultat.resume,
        review_reason=None,
        entry_source=entry_source,
    )


def construire_transaction_normalisee(
    entry: data.Transaction,
    document: DocumentFiscal,
    resume: ResumeTaxesRevenu,
) -> str:
    """Construit le texte Beancount remplaceant un depot brut de revenu."""
    revenu_original = next(
        posting for posting in entry.postings if posting.account.startswith("Revenus:")
    )
    banque = next(
        posting for posting in entry.postings
        if posting.account.startswith(PREFIXES_BANQUE)
        and posting.units is not None
        and Decimal(str(posting.units.number)) > 0
    )
    devise = revenu_original.units.currency if revenu_original.units is not None else "CAD"

    meta = copy.copy(entry.meta)
    meta["document"] = document.chemin_document
    meta["document_fiscal_id"] = document.id
    meta["document_kind"] = "revenue"
    meta["pricing_mode"] = document.pricing_mode
    meta["traitement_taxes_revenu"] = resume.traitement
    meta["normalisation_revenu"] = "oui"

    postings = [banque]
    postings.append(
        data.Posting(
            account=revenu_original.account,
            units=Amount(-resume.sous_total, devise),
            cost=revenu_original.cost,
            price=revenu_original.price,
            flag=revenu_original.flag,
            meta=revenu_original.meta,
        )
    )
    if resume.tps > 0:
        postings.append(
            data.Posting(
                account=COMPTE_TPS_PERCUE,
                units=Amount(-resume.tps, devise),
                cost=None,
                price=None,
                flag=None,
                meta=None,
            )
        )
    if resume.tvq > 0:
        postings.append(
            data.Posting(
                account=COMPTE_TVQ_PERCUE,
                units=Amount(-resume.tvq, devise),
                cost=None,
                price=None,
                flag=None,
                meta=None,
            )
        )

    normalisee = data.Transaction(
        meta=meta,
        date=entry.date,
        flag=entry.flag,
        payee=entry.payee,
        narration=entry.narration,
        tags=entry.tags,
        links=entry.links,
        postings=postings,
    )
    return printer.format_entry(normalisee).strip()


def _transaction_est_normalisee(
    entry: data.Transaction,
    resume: ResumeTaxesRevenu,
) -> bool:
    banque = [
        posting
        for posting in entry.postings
        if posting.account.startswith(PREFIXES_BANQUE)
        and posting.units is not None
        and Decimal(str(posting.units.number)) > 0
    ]
    revenus = [
        posting for posting in entry.postings
        if posting.account.startswith("Revenus:")
    ]
    autres = [
        posting
        for posting in entry.postings
        if posting not in banque and posting not in revenus and posting.account not in COMPTES_TAXES
    ]
    if len(banque) != 1 or len(revenus) != 1 or autres:
        return False

    montant_banque = _q(sum((_posting_number(posting) for posting in banque), Decimal("0")))
    montant_revenu = _q(abs(_posting_number(revenus[0])))
    tps = _q(
        sum(
            (
                abs(_posting_number(posting))
                for posting in entry.postings
                if posting.account == COMPTE_TPS_PERCUE
            ),
            Decimal("0"),
        )
    )
    tvq = _q(
        sum(
            (
                abs(_posting_number(posting))
                for posting in entry.postings
                if posting.account == COMPTE_TVQ_PERCUE
            ),
            Decimal("0"),
        )
    )
    return (
        montant_banque == _q(resume.total)
        and montant_revenu == _q(resume.sous_total)
        and tps == _q(resume.tps)
        and tvq == _q(resume.tvq)
    )


def auditer_revenus_taxes(
    entries: Iterable[object],
    documents: Iterable[DocumentFiscal],
    debut: datetime.date | None = None,
    fin: datetime.date | None = None,
) -> AuditRevenusTaxes:
    """Construit les anomalies partagees entre les surfaces."""
    documents_revenus = [document for document in documents if document.document_kind == "revenue"]
    refs_documentees = {
        document.matched_transaction_ref
        for document in documents_revenus
        if document.matched_transaction_ref
    }

    anomalies: list[AnomalieRevenuTaxe] = []

    for document in documents_revenus:
        date_doc = date_document(document)
        if not _date_dans_periode(date_doc, debut, fin):
            continue

        if document.normalization_status == "unmatched":
            anomalies.append(
                AnomalieRevenuTaxe(
                    type="document_revenu_non_apparie",
                    niveau="attention",
                    titre="Document de revenu non apparie",
                    detail=(
                        f"{document.fournisseur}: document televerse sans depot bancaire associe."
                    ),
                    date=date_doc,
                    document_id=document.id,
                )
            )
        elif document.normalization_status == "matched_needs_review":
            anomalies.append(
                AnomalieRevenuTaxe(
                    type="document_revenu_revue",
                    niveau="attention",
                    titre="Document de revenu a revoir",
                    detail=(
                        document.review_reason
                        or "Confirmation manuelle requise avant normalisation."
                    ),
                    date=date_doc,
                    document_id=document.id,
                    transaction_ref=document.matched_transaction_ref,
                )
            )

    for entry in entries:
        if not isinstance(entry, data.Transaction):
            continue
        if not _date_dans_periode(entry.date, debut, fin):
            continue
        analyse = analyser_transaction_revenu(entry)
        if not analyse.est_depot_revenu:
            continue

        if analyse.a_taxes:
            if analyse.semble_remboursement:
                anomalies.append(
                    AnomalieRevenuTaxe(
                        type="encaissement_taxe_remboursement_a_revoir",
                        niveau="attention",
                        titre="Encaissement taxe ressemblant a un remboursement",
                        detail=(
                            f"{entry.payee or entry.narration or 'Transaction sans libelle'}: "
                            "le split TPS/TVQ existe deja au ledger, mais le libelle ressemble "
                            "a un remboursement ou pass-through. Revue CPA recommandee."
                        ),
                        date=entry.date,
                        transaction_ref=analyse.transaction_ref,
                    )
                )
            if (
                entry.meta.get("normalisation_revenu") == "oui"
                and not entry.meta.get("document_fiscal_id")
            ):
                anomalies.append(
                    AnomalieRevenuTaxe(
                        type="revenu_normalise_sans_document",
                        niveau="attention",
                        titre="Revenu normalise sans document lie",
                        detail=(
                            f"{entry.payee or entry.narration or 'Transaction sans libelle'}: "
                            "split fiscal present mais aucun document fiscal lie dans le registre."
                        ),
                        date=entry.date,
                        transaction_ref=analyse.transaction_ref,
                    )
                )
            continue

        if analyse.transaction_ref in refs_documentees:
            continue
        anomalies.append(
            AnomalieRevenuTaxe(
                type="reception_brute_sans_taxes",
                niveau="attention",
                titre="Depot de revenu sans split TPS/TVQ",
                detail=(
                    f"{entry.payee or entry.narration or 'Transaction sans libelle'}: "
                    "encaissement credite entierement au revenu sans comptes de taxes."
                ),
                date=entry.date,
                transaction_ref=analyse.transaction_ref,
            )
        )

    anomalies.sort(key=lambda item: (item.date or datetime.date.min, item.titre, item.detail))
    return AuditRevenusTaxes(anomalies=tuple(anomalies))


def _date_dans_periode(
    valeur: datetime.date | None,
    debut: datetime.date | None,
    fin: datetime.date | None,
) -> bool:
    if valeur is None:
        return debut is None and fin is None
    if debut and valeur < debut:
        return False
    if fin and valeur > fin:
        return False
    return True


def _appliquer_taxes_selon_traitement(
    montant_ht: Decimal,
    traitement: str,
) -> ResumeTaxesRevenu:
    if traitement == "aucune_taxe":
        return ResumeTaxesRevenu(
            sous_total=_q(montant_ht),
            tps=Decimal("0.00"),
            tvq=Decimal("0.00"),
            total=_q(montant_ht),
            traitement=traitement,
        )
    if traitement == "tps_seulement":
        tps = _q(montant_ht * TAUX_TPS)
        return ResumeTaxesRevenu(
            sous_total=_q(montant_ht),
            tps=tps,
            tvq=Decimal("0.00"),
            total=_q(montant_ht + tps),
            traitement=traitement,
        )
    tps, tvq, total = appliquer_taxes(_q(montant_ht), TAUX_TPS, TAUX_TVQ)
    return ResumeTaxesRevenu(
        sous_total=_q(montant_ht),
        tps=_q(tps),
        tvq=_q(tvq),
        total=_q(total),
        traitement=traitement,
    )


def _traitement_depuis_montants(tps: Decimal, tvq: Decimal) -> str:
    if tps > 0 and tvq > 0:
        return "tps_tvq"
    if tps > 0:
        return "tps_seulement"
    return "aucune_taxe"


def _posting_number(posting: data.Posting) -> Decimal:
    if posting.units is None:
        return Decimal("0")
    return Decimal(str(posting.units.number))


def _score_correspondance(
    montant_document: Decimal,
    date_document_val: datetime.date | None,
    montant_txn: Decimal,
    date_txn: datetime.date,
) -> float:
    diff_montant = abs(_q(montant_document) - _q(montant_txn))
    if diff_montant <= Decimal("0.05"):
        score_montant = 1.0
    elif diff_montant >= Decimal("5.00"):
        score_montant = 0.0
    else:
        score_montant = float(Decimal("1") - (diff_montant - Decimal("0.05")) / Decimal("4.95"))

    if date_document_val is None:
        score_date = 0.0
    else:
        diff_jours = abs((date_txn - date_document_val).days)
        if diff_jours == 0:
            score_date = 1.0
        elif diff_jours == 1:
            score_date = 0.8
        elif diff_jours >= 7:
            score_date = 0.0
        else:
            score_date = 0.8 * (1.0 - (diff_jours - 1) / 6.0)

    return 0.6 * score_montant + 0.4 * score_date


def _q(montant: Decimal) -> Decimal:
    return Decimal(str(montant)).quantize(QUANTIZE_CENT)
