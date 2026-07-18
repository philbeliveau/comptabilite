"""Planification de remuneration proprietaire hors grand-livre corporatif.

Les depenses personnelles servent uniquement a planifier le besoin de tresorerie
personnel. Elles ne sont jamais transformees en ecritures corporatives ici.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from compteqc.mcp.services import calculer_soldes
from compteqc.quebec.paie.moteur import ResultatPaie, calculer_paie

CAD = Decimal("0.01")
MOIS_MOYEN_JOURS = Decimal("30.4375")

FEDERAL_2026_BRACKETS = [
    {
        "label": "0 $ a 58 523 $",
        "min": Decimal("0"),
        "max": Decimal("58523"),
        "rate": Decimal("0.14"),
    },
    {
        "label": "58 523,01 $ a 117 045 $",
        "min": Decimal("58523.01"),
        "max": Decimal("117045"),
        "rate": Decimal("0.205"),
    },
    {
        "label": "117 045,01 $ a 181 440 $",
        "min": Decimal("117045.01"),
        "max": Decimal("181440"),
        "rate": Decimal("0.26"),
    },
    {
        "label": "181 440,01 $ a 258 482 $",
        "min": Decimal("181440.01"),
        "max": Decimal("258482"),
        "rate": Decimal("0.29"),
    },
    {
        "label": "plus de 258 482 $",
        "min": Decimal("258482.01"),
        "max": None,
        "rate": Decimal("0.33"),
    },
]

QUEBEC_2026_BRACKETS = [
    {
        "label": "0 $ a 54 345 $",
        "min": Decimal("0"),
        "max": Decimal("54345"),
        "rate": Decimal("0.14"),
    },
    {
        "label": "plus de 54 345 $ a 108 680 $",
        "min": Decimal("54345.01"),
        "max": Decimal("108680"),
        "rate": Decimal("0.19"),
    },
    {
        "label": "plus de 108 680 $ a 132 245 $",
        "min": Decimal("108680.01"),
        "max": Decimal("132245"),
        "rate": Decimal("0.24"),
    },
    {
        "label": "plus de 132 245 $",
        "min": Decimal("132245.01"),
        "max": None,
        "rate": Decimal("0.2575"),
    },
]


@dataclass(frozen=True)
class LigneCourbeSalaire:
    salaire_brut_annuel: Decimal
    net_annuel: Decimal
    retenues_employe_annuelles: Decimal
    cotisations_employeur_annuelles: Decimal

    @property
    def cout_corporatif_annuel(self) -> Decimal:
        return _q(self.salaire_brut_annuel + self.cotisations_employeur_annuelles)


@dataclass(frozen=True)
class ParametresScenario:
    nom: str
    depenses_mensuelles: Decimal
    marge_mensuelle: Decimal = Decimal("0")
    epargne_urgence_mensuelle: Decimal = Decimal("0")
    mariage_cible: Decimal = Decimal("0")
    mariage_date: dt.date | None = None
    maison_cible: Decimal = Decimal("0")
    maison_date: dt.date | None = None
    celiapp_cible_annuelle: Decimal = Decimal("8000")
    celiapp_deja_cotise: Decimal = Decimal("8000")
    reer_cible_annuelle: Decimal = Decimal("0")
    reserve_corporative_cible: Decimal = Decimal("0")


@dataclass(frozen=True)
class ResultatScenario:
    nom: str
    net_mensuel_requis: Decimal
    net_annuel_requis: Decimal
    salaire_brut_annuel_estime: Decimal
    retenues_employe_annuelles: Decimal
    cotisations_employeur_annuelles: Decimal
    cout_corporatif_annuel: Decimal
    retenu_apres_impot_corporatif: Decimal
    cout_opportunite_retenu: Decimal
    marge_reserve_corporative: Decimal | None
    avertissements: tuple[str, ...]


@dataclass(frozen=True)
class ReserveLedger:
    encaisse_corporative: Decimal
    taxes_tps_tvq_net: Decimal
    disponible_apres_taxes: Decimal


def charger_depenses_mensuelles(path: Path) -> dict[str, Decimal]:
    """Charge le CSV mensuel personnel sans toucher au ledger corporatif."""
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {
            row["month"]: Decimal(
                row.get("gross_recurring_spend")
                or row.get("recurring_spend")
                or row.get("net_recurring_spend")
                or "0"
            ).quantize(CAD)
            for row in reader
        }


def moyenne_depenses_recurrentes(path: Path) -> Decimal:
    """Retourne la moyenne mensuelle recurrente depuis le CSV personnel."""
    valeurs = list(charger_depenses_mensuelles(path).values())
    if not valeurs:
        return Decimal("0.00")
    return _q(sum(valeurs, Decimal("0")) / Decimal(len(valeurs)))


def mensualite_objectif(
    cible: Decimal,
    date_cible: dt.date | None,
    date_reference: dt.date,
) -> Decimal:
    """Convertit un objectif date en besoin mensuel moyen."""
    if cible <= 0 or date_cible is None:
        return Decimal("0.00")
    jours = (date_cible - date_reference).days
    if jours <= 0:
        return cible.quantize(CAD)
    mois = Decimal(jours) / MOIS_MOYEN_JOURS
    return _q(cible / mois)


def besoin_net_mensuel(parametres: ParametresScenario, date_reference: dt.date) -> Decimal:
    """Calcule le besoin net mensuel cash-flow, hors ecritures corporatives."""
    celiapp_restant = max(
        Decimal("0"),
        parametres.celiapp_cible_annuelle - parametres.celiapp_deja_cotise,
    )
    total = (
        parametres.depenses_mensuelles
        + parametres.marge_mensuelle
        + parametres.epargne_urgence_mensuelle
        + mensualite_objectif(parametres.mariage_cible, parametres.mariage_date, date_reference)
        + mensualite_objectif(parametres.maison_cible, parametres.maison_date, date_reference)
        + celiapp_restant / Decimal("12")
        + parametres.reer_cible_annuelle / Decimal("12")
    )
    return _q(total)


def construire_courbe_salaire(
    ledger_path: Path,
    *,
    annee: int = 2026,
    maximum: Decimal = Decimal("250000"),
    pas: Decimal = Decimal("1000"),
) -> list[LigneCourbeSalaire]:
    """Construit une courbe annuelle avec le moteur de paie existant."""
    courbe: list[LigneCourbeSalaire] = []
    salaire = Decimal("0")
    while salaire <= maximum:
        resultat = _calculer_paie_annuelle(salaire, ledger_path, annee)
        courbe.append(_ligne_depuis_resultat(resultat, salaire))
        salaire += pas
    return courbe


def estimer_salaire_pour_net(
    net_annuel_requis: Decimal,
    ledger_path: Path,
    *,
    annee: int = 2026,
    maximum: Decimal = Decimal("300000"),
) -> LigneCourbeSalaire:
    """Trouve le salaire brut annuel minimal donnant le net annuel requis."""
    bas = Decimal("0")
    haut = maximum
    meilleur: LigneCourbeSalaire | None = None

    for _ in range(24):
        milieu = ((bas + haut) / Decimal("2")).quantize(CAD)
        ligne = _ligne_depuis_resultat(
            _calculer_paie_annuelle(milieu, ledger_path, annee),
            milieu,
        )
        if ligne.net_annuel >= net_annuel_requis:
            meilleur = ligne
            haut = milieu
        else:
            bas = milieu

    if meilleur is None:
        meilleur = _ligne_depuis_resultat(
            _calculer_paie_annuelle(maximum, ledger_path, annee),
            maximum,
        )
    return meilleur


def analyser_scenario(
    parametres: ParametresScenario,
    ledger_path: Path,
    *,
    date_reference: dt.date,
    taux_impot_corporatif: Decimal = Decimal("0.21"),
    reserve_ledger: ReserveLedger | None = None,
) -> ResultatScenario:
    """Analyse un scenario de remuneration a des fins de planification."""
    net_mensuel = besoin_net_mensuel(parametres, date_reference)
    net_annuel = _q(net_mensuel * Decimal("12"))
    salaire = estimer_salaire_pour_net(net_annuel, ledger_path)

    retenu_apres_impot = _q(salaire.cout_corporatif_annuel * (Decimal("1") - taux_impot_corporatif))
    cout_opportunite = retenu_apres_impot
    marge_reserve = None
    if reserve_ledger is not None:
        marge_reserve = _q(
            reserve_ledger.disponible_apres_taxes
            - parametres.reserve_corporative_cible
            - salaire.cout_corporatif_annuel
        )

    return ResultatScenario(
        nom=parametres.nom,
        net_mensuel_requis=net_mensuel,
        net_annuel_requis=net_annuel,
        salaire_brut_annuel_estime=salaire.salaire_brut_annuel,
        retenues_employe_annuelles=salaire.retenues_employe_annuelles,
        cotisations_employeur_annuelles=salaire.cotisations_employeur_annuelles,
        cout_corporatif_annuel=salaire.cout_corporatif_annuel,
        retenu_apres_impot_corporatif=retenu_apres_impot,
        cout_opportunite_retenu=cout_opportunite,
        marge_reserve_corporative=marge_reserve,
        avertissements=(
            "Planification seulement: le CPA doit confirmer le taux corporatif, "
            "la DPE, le traitement salaire/dividende et l'integration.",
            "Verifier tout tirage par pret actionnaire avant de l'utiliser comme "
            "remuneration personnelle recurrente.",
        ),
    )


def scenarios_defaut(
    depenses_mensuelles: Decimal,
    date_reference: dt.date,
) -> list[ParametresScenario]:
    """Scenarios preconfigures demandes pour la vue interactive."""
    del date_reference
    return [
        ParametresScenario("Baseline living only", depenses_mensuelles),
        ParametresScenario(
            "Baseline + breathing room",
            depenses_mensuelles,
            marge_mensuelle=Decimal("750"),
        ),
        ParametresScenario(
            "Wedding plan",
            depenses_mensuelles,
            marge_mensuelle=Decimal("500"),
            mariage_cible=Decimal("20000"),
            mariage_date=dt.date(2027, 8, 20),
        ),
        ParametresScenario(
            "House purchase plan",
            depenses_mensuelles,
            marge_mensuelle=Decimal("500"),
            maison_cible=Decimal("50000"),
            maison_date=dt.date(2027, 8, 1),
        ),
        ParametresScenario(
            "RRSP/FHSA maximization",
            depenses_mensuelles,
            marge_mensuelle=Decimal("500"),
            celiapp_cible_annuelle=Decimal("8000"),
            celiapp_deja_cotise=Decimal("8000"),
            reer_cible_annuelle=Decimal("12000"),
        ),
        ParametresScenario("Minimum-pay scenario", depenses_mensuelles),
        ParametresScenario(
            "Balanced retained-cash scenario",
            depenses_mensuelles,
            marge_mensuelle=Decimal("500"),
            epargne_urgence_mensuelle=Decimal("500"),
            mariage_cible=Decimal("20000"),
            mariage_date=dt.date(2027, 8, 20),
            reserve_corporative_cible=Decimal("50000"),
        ),
    ]


def bracket_actif(revenu: Decimal, brackets: list[dict]) -> dict:
    """Retourne la tranche applicable pour un revenu annuel."""
    for bracket in brackets:
        maximum = bracket["max"]
        if maximum is None or revenu <= maximum:
            return bracket
    return brackets[-1]


def reserves_depuis_ledger(entries: list[object]) -> ReserveLedger:
    """Estime l'encaisse et le coussin TPS/TVQ net depuis les soldes du ledger."""
    soldes = calculer_soldes(entries)
    encaisse = sum(
        (montant for compte, montant in soldes.items() if compte.startswith("Actifs:Banque")),
        Decimal("0"),
    )
    tps_tvq_percue = abs(soldes.get("Passifs:TPS-Percue", Decimal("0"))) + abs(
        soldes.get("Passifs:TVQ-Percue", Decimal("0"))
    )
    tps_tvq_payee = soldes.get("Actifs:TPS-Payee", Decimal("0")) + soldes.get(
        "Actifs:TVQ-Payee", Decimal("0")
    )
    taxes_net = _q(max(Decimal("0"), tps_tvq_percue - tps_tvq_payee))
    return ReserveLedger(
        encaisse_corporative=_q(encaisse),
        taxes_tps_tvq_net=taxes_net,
        disponible_apres_taxes=_q(encaisse - taxes_net),
    )


def data_brackets_json() -> dict[str, list[dict[str, object]]]:
    """Version serialisable des tranches officielles 2026 demandees."""
    return {
        "federal": [_bracket_json(b) for b in FEDERAL_2026_BRACKETS],
        "quebec": [_bracket_json(b) for b in QUEBEC_2026_BRACKETS],
    }


def _calculer_paie_annuelle(salaire_annuel: Decimal, ledger_path: Path, annee: int) -> ResultatPaie:
    return calculer_paie(
        brut=_q(salaire_annuel / Decimal("26")),
        numero_periode=1,
        chemin_ledger=str(ledger_path),
        annee=annee,
        nb_periodes=26,
    )


def _ligne_depuis_resultat(resultat: ResultatPaie, salaire_annuel: Decimal) -> LigneCourbeSalaire:
    return LigneCourbeSalaire(
        salaire_brut_annuel=_q(salaire_annuel),
        net_annuel=_q(resultat.net * Decimal(resultat.nb_periodes)),
        retenues_employe_annuelles=_q(resultat.total_retenues * Decimal(resultat.nb_periodes)),
        cotisations_employeur_annuelles=_q(
            resultat.total_cotisations_employeur * Decimal(resultat.nb_periodes)
        ),
    )


def _bracket_json(bracket: dict) -> dict[str, object]:
    return {
        "label": bracket["label"],
        "min": float(bracket["min"]),
        "max": None if bracket["max"] is None else float(bracket["max"]),
        "rate": float(bracket["rate"]),
    }


def _q(montant: Decimal) -> Decimal:
    return montant.quantize(CAD, rounding=ROUND_HALF_UP)
