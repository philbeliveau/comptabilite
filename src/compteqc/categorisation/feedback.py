"""Suivi des corrections utilisateur et generation automatique de regles.

Lorsqu'un utilisateur recategorise une transaction, la correction est
enregistree. Apres SEUIL_AUTO_REGLE corrections identiques (meme vendeur
vers meme compte), une regle YAML est automatiquement generee.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

from compteqc.categorisation.regles import ConditionRegle, ConfigRegles, Regle

logger = logging.getLogger(__name__)

CHEMIN_HISTORIQUE_DEFAUT = Path("data/corrections/historique.json")
SEUIL_AUTO_REGLE = 2


def _normaliser_vendeur(vendeur: str) -> str:
    """Normalise le nom du vendeur pour le suivi des corrections."""
    return vendeur.upper().strip()


def _slugifier(nom: str) -> str:
    """Convertit un nom en slug pour le nom de regle."""
    # Retirer les accents
    nfkd = unicodedata.normalize("NFKD", nom)
    ascii_str = nfkd.encode("ASCII", "ignore").decode("ASCII")
    # Remplacer espaces et caracteres speciaux par des tirets
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_str).strip("-").lower()
    return slug[:20]


def charger_historique(chemin: Path) -> dict:
    """Charge l'historique des corrections depuis le fichier JSON.

    Args:
        chemin: Chemin vers le fichier JSON.

    Returns:
        Dictionnaire de l'historique. Dict vide si le fichier n'existe pas.
    """
    if not chemin.exists():
        return {}

    contenu = chemin.read_text(encoding="utf-8")
    if not contenu.strip():
        return {}

    return json.loads(contenu)


def _sauvegarder_historique(chemin: Path, historique: dict) -> None:
    """Sauvegarde l'historique de maniere atomique (ecriture tmp + rename)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text(json.dumps(historique, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(chemin)


def enregistrer_correction(
    chemin_historique: Path,
    vendeur: str,
    compte_corrige: str,
    compte_original: str | None = None,
    note: str | None = None,
) -> Regle | None:
    """Enregistre une correction utilisateur et genere une regle si le seuil est atteint.

    Args:
        chemin_historique: Chemin vers le fichier JSON de l'historique.
        vendeur: Nom du vendeur/payee.
        compte_corrige: Compte comptable corrige par l'utilisateur.
        compte_original: Compte propose par l'IA (optionnel).
        note: Note optionnelle de l'utilisateur.

    Returns:
        La Regle generee si le seuil est atteint, None sinon.
    """
    historique = charger_historique(chemin_historique)

    cle = _normaliser_vendeur(vendeur)
    if cle not in historique:
        historique[cle] = {"comptes": {}, "notes": []}

    entry = historique[cle]

    # Incrementer le compteur pour ce vendeur -> compte
    if compte_corrige not in entry["comptes"]:
        entry["comptes"][compte_corrige] = 0
    entry["comptes"][compte_corrige] += 1

    # Stocker le timestamp et la note
    entry["dernier_timestamp"] = datetime.now(tz=timezone.utc).isoformat()
    if note:
        entry["notes"].append(
            {
                "note": note,
                "compte_original": compte_original,
                "compte_corrige": compte_corrige,
                "timestamp": entry["dernier_timestamp"],
            }
        )

    _sauvegarder_historique(chemin_historique, historique)

    # Verifier le seuil pour auto-generation de regle
    count = entry["comptes"][compte_corrige]
    if count >= SEUIL_AUTO_REGLE:
        slug = _slugifier(cle)
        regle = Regle(
            nom=f"auto-{slug}",
            condition=ConditionRegle(payee=re.escape(vendeur)),
            compte=compte_corrige,
            confiance=0.95,
        )
        return regle

    return None


def ajouter_regle_auto(chemin_regles: Path, regle: Regle) -> None:
    """Ajoute une regle auto-generee au fichier YAML de regles.

    Verifie les doublons (meme pattern vendeur) avant d'ajouter.

    Args:
        chemin_regles: Chemin vers le fichier YAML de regles.
        regle: La regle a ajouter.
    """
    # Charger les regles existantes
    if chemin_regles.exists():
        contenu = chemin_regles.read_text(encoding="utf-8")
        donnees = yaml.safe_load(contenu)
        if donnees is None:
            donnees = {"regles": []}
    else:
        donnees = {"regles": []}

    # Verifier les doublons (meme pattern payee)
    for r in donnees.get("regles", []):
        condition = r.get("condition", {})
        if condition.get("payee") == regle.condition.payee:
            logger.info(
                "Regle deja existante pour le pattern '%s', skip.",
                regle.condition.payee,
            )
            return

    # Ajouter la nouvelle regle
    regle_dict = {
        "nom": regle.nom,
        "condition": {},
        "compte": regle.compte,
        "confiance": regle.confiance,
    }
    if regle.condition.payee:
        regle_dict["condition"]["payee"] = regle.condition.payee
    if regle.condition.narration:
        regle_dict["condition"]["narration"] = regle.condition.narration

    donnees["regles"].append(regle_dict)

    chemin_regles.parent.mkdir(parents=True, exist_ok=True)
    chemin_regles.write_text(
        yaml.dump(donnees, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    logger.info(
        "Nouvelle regle auto-generee: %s -> %s",
        regle.nom,
        regle.compte,
    )
