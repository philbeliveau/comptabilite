"""Taux et seuils annuels pour le Quebec et le federal.

Toutes les valeurs sont en Decimal -- jamais de float.
Source: T4127 122e edition (jan 2026), Retraite Quebec, Revenu Quebec.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TauxQPP:
    """Taux du Regime de rentes du Quebec pour une annee donnee."""

    taux_base: Decimal  # 5.3% en 2026
    taux_supplementaire_1: Decimal  # 1.0% en 2026
    taux_supplementaire_2: Decimal  # 4.0% en 2026
    exemption: Decimal  # $3,500
    mga: Decimal  # Maximum des gains admissibles ($74,600 en 2026)
    mgap: Decimal  # MGA supplementaire ($85,000 en 2026)
    max_base: Decimal  # $3,768.30
    max_supp1: Decimal  # $711.00
    max_supp2: Decimal  # $416.00


@dataclass(frozen=True)
class TauxRQAP:
    """Taux du Regime quebecois d'assurance parentale."""

    taux_employeur: Decimal  # 0.602%
    taux_employe: Decimal  # 0.430%
    mra: Decimal  # Maximum des revenus assurables ($103,000)
    max_employeur: Decimal  # $620.06
    max_employe: Decimal  # $442.90


@dataclass(frozen=True)
class TauxAE:
    """Taux d'assurance-emploi (taux Quebec)."""

    taux_employe: Decimal  # 1.30%
    taux_employeur: Decimal  # 1.82% (1.4x)
    mra: Decimal  # Maximum de la remuneration assurable ($68,900)
    max_employe: Decimal  # $895.70
    max_employeur: Decimal  # $1,253.98


@dataclass(frozen=True)
class TauxFSS:
    """Taux du Fonds des services de sante (employeur seulement)."""

    taux_service_petite: Decimal  # 1.65% (masse salariale <= $1M, secteur services)
    seuil_masse_salariale: Decimal  # $1,000,000


@dataclass(frozen=True)
class TrancheFederale:
    """Tranche d'imposition federale avec seuil, taux et constante K."""

    seuil: Decimal
    taux: Decimal
    constante_k: Decimal


@dataclass(frozen=True)
class TrancheQuebec:
    """Tranche d'imposition Quebec avec seuil, taux et constante."""

    seuil: Decimal
    taux: Decimal
    constante: Decimal


@dataclass(frozen=True)
class TauxAnnuels:
    """Ensemble complet des taux pour une annee fiscale."""

    annee: int
    qpp: TauxQPP
    rqap: TauxRQAP
    ae: TauxAE
    fss: TauxFSS
    cnesst_taux: Decimal  # Configurable par employeur
    normes_travail_taux: Decimal  # 0.06%
    normes_travail_max_gains: Decimal  # $103,000
    tranches_federales: tuple[TrancheFederale, ...]
    tranches_quebec: tuple[TrancheQuebec, ...]
    montant_personnel_federal: Decimal  # $16,452
    montant_personnel_quebec: Decimal  # $18,952
    abattement_quebec: Decimal  # 0.165 (16.5%)
    tps_taux: Decimal  # 0.05
    tvq_taux: Decimal  # 0.09975


TAUX_2026 = TauxAnnuels(
    annee=2026,
    qpp=TauxQPP(
        taux_base=Decimal("0.053"),
        taux_supplementaire_1=Decimal("0.01"),
        taux_supplementaire_2=Decimal("0.04"),
        exemption=Decimal("3500"),
        mga=Decimal("74600"),
        mgap=Decimal("85000"),
        max_base=Decimal("3768.30"),
        max_supp1=Decimal("711.00"),
        max_supp2=Decimal("416.00"),
    ),
    rqap=TauxRQAP(
        taux_employeur=Decimal("0.00602"),
        taux_employe=Decimal("0.00430"),
        mra=Decimal("103000"),
        max_employeur=Decimal("620.06"),
        max_employe=Decimal("442.90"),
    ),
    ae=TauxAE(
        taux_employe=Decimal("0.0130"),
        taux_employeur=Decimal("0.0182"),
        mra=Decimal("68900"),
        max_employe=Decimal("895.70"),
        max_employeur=Decimal("1253.98"),
    ),
    fss=TauxFSS(
        taux_service_petite=Decimal("0.0165"),
        seuil_masse_salariale=Decimal("1000000"),
    ),
    cnesst_taux=Decimal("0.0080"),  # Defaut; l'employeur doit configurer son taux reel
    normes_travail_taux=Decimal("0.0006"),
    normes_travail_max_gains=Decimal("103000"),
    tranches_federales=(
        TrancheFederale(
            seuil=Decimal("58523"),
            taux=Decimal("0.14"),
            constante_k=Decimal("0"),
        ),
        TrancheFederale(
            seuil=Decimal("117045"),
            taux=Decimal("0.205"),
            constante_k=Decimal("3804"),
        ),
        TrancheFederale(
            seuil=Decimal("181440"),
            taux=Decimal("0.26"),
            constante_k=Decimal("10237"),
        ),
        TrancheFederale(
            seuil=Decimal("258482"),
            taux=Decimal("0.29"),
            constante_k=Decimal("15680"),
        ),
        TrancheFederale(
            seuil=Decimal("999999999"),
            taux=Decimal("0.33"),
            constante_k=Decimal("26019"),
        ),
    ),
    tranches_quebec=(
        TrancheQuebec(
            seuil=Decimal("54345"),
            taux=Decimal("0.14"),
            constante=Decimal("0"),
        ),
        TrancheQuebec(
            seuil=Decimal("108680"),
            taux=Decimal("0.19"),
            constante=Decimal("2717"),
        ),
        TrancheQuebec(
            seuil=Decimal("132245"),
            taux=Decimal("0.24"),
            constante=Decimal("5151"),
        ),
        TrancheQuebec(
            seuil=Decimal("999999999"),
            taux=Decimal("0.2575"),
            constante=Decimal("7465"),
        ),
    ),
    montant_personnel_federal=Decimal("16452"),
    montant_personnel_quebec=Decimal("18952"),
    abattement_quebec=Decimal("0.165"),
    tps_taux=Decimal("0.05"),
    tvq_taux=Decimal("0.09975"),
)

# Registre multi-annee
TAUX: dict[int, TauxAnnuels] = {2026: TAUX_2026}


def obtenir_taux(annee: int) -> TauxAnnuels:
    """Retourne les taux pour une annee donnee.

    Raises:
        ValueError: Si les taux ne sont pas disponibles pour l'annee demandee.
    """
    if annee not in TAUX:
        raise ValueError(
            f"Taux non disponibles pour l'annee {annee}. "
            f"Annees disponibles: {sorted(TAUX.keys())}"
        )
    return TAUX[annee]
