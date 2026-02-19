"""Validation du ledger Beancount via bean-check et chargement des comptes."""

from __future__ import annotations

import subprocess
from pathlib import Path


def valider_ledger(chemin_main: Path) -> tuple[bool, list[str]]:
    """Valide le ledger Beancount avec bean-check.

    Args:
        chemin_main: Chemin vers le fichier main.beancount.

    Returns:
        Tuple (succes, messages_erreur).
        Si succes, messages_erreur est une liste vide.
    """
    try:
        result = subprocess.run(
            ["uv", "run", "bean-check", str(chemin_main)],
            capture_output=True,
            text=True,
            cwd=chemin_main.parent.parent,  # racine du projet
            timeout=30,
        )
        if result.returncode == 0:
            return (True, [])
        # bean-check ecrit les erreurs sur stderr
        erreurs = [
            line.strip()
            for line in (result.stderr + result.stdout).splitlines()
            if line.strip()
        ]
        return (False, erreurs)
    except subprocess.TimeoutExpired:
        return (False, ["bean-check timeout apres 30 secondes"])
    except FileNotFoundError:
        return (False, ["bean-check introuvable. Verifier que beancount est installe."])


def charger_comptes_existants(chemin_main: Path) -> set[str]:
    """Charge tous les noms de comptes ouverts dans le ledger.

    Args:
        chemin_main: Chemin vers le fichier main.beancount.

    Returns:
        Set de noms de comptes (ex: {"Depenses:Non-Classe", "Actifs:Banque:RBC:Cheques"}).
    """
    from beancount import loader

    entries, _errors, _options = loader.load_file(str(chemin_main))
    return {entry.account for entry in entries if hasattr(entry, "account")}
