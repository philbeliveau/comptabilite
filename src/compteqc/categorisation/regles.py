"""Modeles Pydantic pour les regles de categorisation."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ConditionRegle(BaseModel):
    """Conditions pour qu'une regle de categorisation s'applique."""

    payee: str | None = Field(default=None, description="Pattern regex sur payee/narration")
    narration: str | None = Field(default=None, description="Pattern regex sur narration")
    montant_min: Decimal | None = Field(default=None, description="Montant minimum (inclus)")
    montant_max: Decimal | None = Field(default=None, description="Montant maximum (inclus)")


class Regle(BaseModel):
    """Une regle de categorisation."""

    nom: str = Field(description="Nom unique de la regle")
    condition: ConditionRegle = Field(description="Conditions pour que la regle s'applique")
    compte: str = Field(description="Compte Beancount cible")
    confiance: float = Field(default=0.9, ge=0.0, le=1.0, description="Niveau de confiance")


class ConfigRegles(BaseModel):
    """Configuration des regles de categorisation."""

    regles: list[Regle] = Field(default_factory=list)


def charger_regles(chemin: Path) -> ConfigRegles:
    """Charge les regles de categorisation depuis un fichier YAML.

    Args:
        chemin: Chemin du fichier YAML.

    Returns:
        Configuration des regles validee par Pydantic.

    Raises:
        ValueError: Si le YAML est invalide ou ne respecte pas le schema.
        FileNotFoundError: Si le fichier n'existe pas.
    """
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier de regles introuvable: {chemin}")

    contenu = chemin.read_text(encoding="utf-8")
    donnees = yaml.safe_load(contenu)

    if donnees is None:
        return ConfigRegles()

    try:
        return ConfigRegles.model_validate(donnees)
    except Exception as e:
        raise ValueError(f"Fichier de regles invalide ({chemin}): {e}") from e
