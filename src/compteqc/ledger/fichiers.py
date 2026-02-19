"""Gestion des fichiers du ledger Beancount (fichiers mensuels, includes)."""

from __future__ import annotations

from pathlib import Path


def chemin_fichier_mensuel(annee: int, mois: int, base_dir: Path) -> Path:
    """Retourne le chemin vers le fichier mensuel et le cree si necessaire.

    Args:
        annee: Annee (ex: 2026).
        mois: Mois (1-12).
        base_dir: Repertoire de base du ledger (ex: /projet/ledger/).

    Returns:
        Chemin vers le fichier mensuel (ex: ledger/2026/03.beancount).
    """
    repertoire_annee = base_dir / str(annee)
    repertoire_annee.mkdir(parents=True, exist_ok=True)

    fichier = repertoire_annee / f"{mois:02d}.beancount"
    if not fichier.exists():
        # Beancount v3 requiert les options name_* dans chaque fichier inclus
        entete = (
            f'; Transactions {_nom_mois(mois)} {annee}\n'
            'option "name_assets" "Actifs"\n'
            'option "name_liabilities" "Passifs"\n'
            'option "name_equity" "Capital"\n'
            'option "name_income" "Revenus"\n'
            'option "name_expenses" "Depenses"\n'
        )
        fichier.write_text(entete, encoding="utf-8")

    return fichier


def ajouter_include(chemin_main: Path, chemin_relatif: str) -> bool:
    """Ajoute une directive include dans main.beancount si pas deja presente.

    Args:
        chemin_main: Chemin vers main.beancount.
        chemin_relatif: Chemin relatif a inclure (ex: "2026/03.beancount").

    Returns:
        True si l'include a ete ajoute, False si deja present.
    """
    contenu = chemin_main.read_text(encoding="utf-8")
    directive = f'include "{chemin_relatif}"'

    if directive in contenu:
        return False

    # Ajouter a la fin du fichier
    if not contenu.endswith("\n"):
        contenu += "\n"
    contenu += f"{directive}\n"
    chemin_main.write_text(contenu, encoding="utf-8")
    return True


def ecrire_transactions(chemin: Path, transactions_beancount: str) -> None:
    """Ajoute du texte Beancount (transactions formatees) a la fin du fichier.

    Args:
        chemin: Chemin vers le fichier .beancount cible.
        transactions_beancount: Texte Beancount a ajouter.
    """
    contenu_existant = chemin.read_text(encoding="utf-8") if chemin.exists() else ""
    if not contenu_existant.endswith("\n"):
        contenu_existant += "\n"
    contenu_existant += "\n" + transactions_beancount
    chemin.write_text(contenu_existant, encoding="utf-8")


def _nom_mois(mois: int) -> str:
    """Retourne le nom du mois en francais."""
    noms = {
        1: "janvier",
        2: "fevrier",
        3: "mars",
        4: "avril",
        5: "mai",
        6: "juin",
        7: "juillet",
        8: "aout",
        9: "septembre",
        10: "octobre",
        11: "novembre",
        12: "decembre",
    }
    return noms.get(mois, f"mois-{mois}")
