"""Registre d'actifs immobilises pour le calcul de la DPA.

Persistence en YAML. Chaque actif est identifie par un ID unique
et associe a une classe DPA.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator


class Actif(BaseModel):
    """Un actif immobilise suivi pour la DPA."""

    id: str  # Identifiant unique (ex: "mac-studio-2026")
    description: str  # "Mac Studio M4 Ultra"
    classe: int  # Classe DPA (8, 10, 12, 50, 54)
    cout: Decimal  # Cout original
    date_acquisition: date  # Date d'achat
    date_disposition: date | None = None  # Date de vente/disposition
    produit_disposition: Decimal | None = None  # Produit de disposition

    @field_validator("cout", "produit_disposition", mode="before")
    @classmethod
    def rejeter_float(cls, v: object) -> object:
        if isinstance(v, float):
            msg = "Utiliser Decimal, pas float, pour les montants monetaires"
            raise ValueError(msg)
        return v

    model_config = {"arbitrary_types_allowed": True}


class RegistreActifs:
    """Gere le registre d'actifs persiste en YAML."""

    def __init__(self, chemin: str | Path = "data/actifs.yaml") -> None:
        self.chemin = Path(chemin)
        self._actifs: list[Actif] = []

    def charger(self) -> list[Actif]:
        """Charge les actifs depuis le fichier YAML."""
        if not self.chemin.exists():
            self._actifs = []
            return self._actifs

        with self.chemin.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or not data.get("actifs"):
            self._actifs = []
            return self._actifs

        self._actifs = []
        for item in data["actifs"]:
            # Convertir les montants en Decimal (YAML charge en str ou int)
            if "cout" in item:
                item["cout"] = Decimal(str(item["cout"]))
            if "produit_disposition" in item and item["produit_disposition"] is not None:
                item["produit_disposition"] = Decimal(str(item["produit_disposition"]))
            self._actifs.append(Actif(**item))

        return self._actifs

    def sauvegarder(self, actifs: list[Actif] | None = None) -> None:
        """Sauvegarde les actifs dans le fichier YAML."""
        if actifs is not None:
            self._actifs = actifs

        self.chemin.parent.mkdir(parents=True, exist_ok=True)

        data = {"actifs": []}
        for actif in self._actifs:
            item = {
                "id": actif.id,
                "description": actif.description,
                "classe": actif.classe,
                "cout": str(actif.cout),
                "date_acquisition": actif.date_acquisition.isoformat(),
            }
            if actif.date_disposition is not None:
                item["date_disposition"] = actif.date_disposition.isoformat()
            if actif.produit_disposition is not None:
                item["produit_disposition"] = str(actif.produit_disposition)
            data["actifs"].append(item)

        with self.chemin.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def ajouter(self, actif: Actif) -> None:
        """Ajoute un actif au registre."""
        # Verifier unicite de l'ID
        ids_existants = {a.id for a in self._actifs}
        if actif.id in ids_existants:
            msg = f"Actif avec ID '{actif.id}' existe deja"
            raise ValueError(msg)
        self._actifs.append(actif)

    def disposer(self, id_actif: str, date_disposition: date, produit: Decimal) -> None:
        """Enregistre la disposition d'un actif."""
        for actif in self._actifs:
            if actif.id == id_actif:
                if actif.date_disposition is not None:
                    msg = f"Actif '{id_actif}' deja dispose"
                    raise ValueError(msg)
                actif.date_disposition = date_disposition
                actif.produit_disposition = produit
                return
        msg = f"Actif '{id_actif}' non trouve"
        raise ValueError(msg)

    def actifs_par_classe(self, annee: int) -> dict[int, list[Actif]]:
        """Retourne les actifs groupes par classe DPA pour une annee donnee.

        Inclut les actifs acquis avant ou durant l'annee.
        Exclut les actifs disposes avant l'annee.
        """
        resultat: dict[int, list[Actif]] = {}
        for actif in self._actifs:
            if actif.date_acquisition.year > annee:
                continue
            if actif.date_disposition and actif.date_disposition.year < annee:
                continue
            if actif.classe not in resultat:
                resultat[actif.classe] = []
            resultat[actif.classe].append(actif)
        return resultat

    @property
    def actifs(self) -> list[Actif]:
        return list(self._actifs)
