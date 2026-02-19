"""Moteur de regles de traitement fiscal TPS/TVQ.

Determine le traitement fiscal (taxable, exempt, zero, tps_seulement) pour chaque
transaction en fonction de la categorie du compte, du beneficiaire/vendeur, et du client.

Priorite pour les depenses: vendeur > categorie > defaut global (taxable).
Priorite pour les revenus: client > type de produit > defaut global (tps_tvq).
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import yaml
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Modeles Pydantic pour la validation du YAML
# ---------------------------------------------------------------------------


class RegleVendeur(BaseModel):
    """Regle de traitement fiscal pour un vendeur identifie par regex."""

    payee_regex: str
    raison: str = ""


class RegleClient(BaseModel):
    """Regle de traitement fiscal pour un client identifie par regex."""

    client_regex: str


class CategoriesRegles(BaseModel):
    """Regles par categorie de compte (patrons glob)."""

    exempt: list[str] = []
    zero: list[str] = []


class VendeursRegles(BaseModel):
    """Regles par vendeur (regex)."""

    exempt: list[RegleVendeur] = []
    tps_seulement: list[RegleVendeur] = []


class ClientsRegles(BaseModel):
    """Regles par client (regex) pour les revenus."""

    tps_tvq: list[RegleClient] = []
    tps_seulement: list[RegleClient] = []
    aucune_taxe: list[RegleClient] = []


class ReglesTaxes(BaseModel):
    """Ensemble complet des regles de traitement fiscal TPS/TVQ."""

    defaut: str = "taxable"
    categories: CategoriesRegles = CategoriesRegles()
    vendeurs: VendeursRegles = VendeursRegles()
    clients: ClientsRegles = ClientsRegles()


# ---------------------------------------------------------------------------
# YAML par defaut integre (pour les tests et initialisation)
# ---------------------------------------------------------------------------

_REGLES_DEFAUT_YAML = """
defaut: taxable

categories:
  exempt:
    - "Depenses:Frais-Bancaires"
    - "Depenses:Interet:Bancaire"
    - "Depenses:Assurances:*"
    - "Depenses:Salaires:*"
  zero:
    - "Depenses:Formation"

vendeurs:
  exempt:
    - payee_regex: ".*BANQUE.*|.*RBC.*|.*DESJARDINS.*"
      raison: "Services financiers"
    - payee_regex: ".*ASSURANCE.*|.*INTACT.*"
      raison: "Primes d'assurance"
  tps_seulement:
    - payee_regex: ".*AMAZON.*WEB.*SERVICES.*"
      raison: "Fournisseur hors Quebec"

clients:
  tps_tvq:
    - client_regex: ".*PROCOM.*"
    - client_regex: ".*FORMATION.*"
  tps_seulement:
    - client_regex: ".*ACME-TORONTO.*"
  aucune_taxe:
    - client_regex: ".*INTERNATIONAL.*"
"""


# ---------------------------------------------------------------------------
# Chargement et logique
# ---------------------------------------------------------------------------


def charger_regles_taxes(
    chemin: str = "rules/taxes.yaml",
    *,
    _default_yaml: bool = False,
) -> ReglesTaxes:
    """Charge et valide les regles de traitement fiscal depuis un fichier YAML.

    Args:
        chemin: Chemin vers le fichier YAML de regles.
        _default_yaml: Si True, utilise les regles par defaut integrees
                       (utile pour les tests sans fichier sur disque).

    Returns:
        ReglesTaxes validees par Pydantic.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas et _default_yaml est False.
    """
    if _default_yaml:
        raw = yaml.safe_load(_REGLES_DEFAUT_YAML)
    else:
        path = Path(chemin)
        if not path.exists():
            raise FileNotFoundError(f"Fichier de regles introuvable: {chemin}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    return ReglesTaxes.model_validate(raw)


def _match_compte_categorie(compte: str, patrons: list[str]) -> bool:
    """Verifie si un compte correspond a un patron de categorie (glob-style).

    Supporte les patrons avec wildcard: 'Depenses:Assurances:*' match
    'Depenses:Assurances:Responsabilite'.
    """
    for patron in patrons:
        if fnmatch.fnmatch(compte, patron):
            return True
    return False


def _match_vendeur(
    beneficiaire: str,
    regles_vendeur: list[RegleVendeur],
) -> bool:
    """Verifie si un beneficiaire correspond a un patron regex de vendeur."""
    beneficiaire_upper = beneficiaire.upper()
    for regle in regles_vendeur:
        if re.match(regle.payee_regex, beneficiaire_upper, re.IGNORECASE):
            return True
    return False


def _match_client(
    client: str,
    regles_client: list[RegleClient],
) -> bool:
    """Verifie si un client correspond a un patron regex."""
    client_upper = client.upper()
    for regle in regles_client:
        if re.match(regle.client_regex, client_upper, re.IGNORECASE):
            return True
    return False


def determiner_traitement_depense(
    compte: str,
    beneficiaire: str,
    regles: ReglesTaxes,
) -> str:
    """Determine le traitement fiscal pour une depense.

    Priorite: vendeur override > categorie > defaut global ('taxable').

    Args:
        compte: Nom du compte de depense (ex: 'Depenses:Frais-Bancaires').
        beneficiaire: Nom du beneficiaire/vendeur.
        regles: Regles de traitement fiscal.

    Returns:
        Type de traitement: 'taxable', 'exempt', 'zero', 'tps_seulement'.
    """
    # 1. Vendeur override (priorite la plus haute)
    if _match_vendeur(beneficiaire, regles.vendeurs.tps_seulement):
        return "tps_seulement"
    if _match_vendeur(beneficiaire, regles.vendeurs.exempt):
        return "exempt"

    # 2. Categorie de compte
    if _match_compte_categorie(compte, regles.categories.exempt):
        return "exempt"
    if _match_compte_categorie(compte, regles.categories.zero):
        return "zero"

    # 3. Defaut global
    return regles.defaut


def determiner_traitement_revenu(
    client: str,
    type_produit: str,
    regles: ReglesTaxes,
) -> str:
    """Determine le traitement fiscal pour un revenu.

    Verifie les regles client d'abord, puis le type de produit (non implemente).

    Args:
        client: Nom du client.
        type_produit: Type de produit/service (reserve pour usage futur).
        regles: Regles de traitement fiscal.

    Returns:
        Type de traitement: 'tps_tvq', 'tps_seulement', 'aucune_taxe'.
    """
    # 1. Regles client (priorite la plus haute)
    if _match_client(client, regles.clients.aucune_taxe):
        return "aucune_taxe"
    if _match_client(client, regles.clients.tps_seulement):
        return "tps_seulement"
    if _match_client(client, regles.clients.tps_tvq):
        return "tps_tvq"

    # 2. Defaut pour revenus: TPS + TVQ (Quebec)
    return "tps_tvq"
