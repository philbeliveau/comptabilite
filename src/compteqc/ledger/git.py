"""Auto-commit git apres modification du ledger."""

from __future__ import annotations

import subprocess
from pathlib import Path

from compteqc.ledger.validation import valider_ledger


def auto_commit(repertoire: Path, message: str) -> bool:
    """Cree un commit git automatique apres validation du ledger.

    Valide le ledger AVANT de commiter. Ne commit jamais un ledger invalide.

    Args:
        repertoire: Racine du projet (parent de ledger/).
        message: Message de commit.

    Returns:
        True si un commit a ete cree, False sinon (pas de changements ou ledger invalide).

    Raises:
        ValueError: Si le ledger ne passe pas bean-check.
    """
    chemin_main = repertoire / "ledger" / "main.beancount"

    # Valider avant de commiter
    valide, erreurs = valider_ledger(chemin_main)
    if not valide:
        raise ValueError(
            "Ledger invalide, commit annule. Erreurs:\n" + "\n".join(erreurs)
        )

    # Stage les fichiers beancount, rules, et data/processed
    patterns = ["ledger/", "rules/", "data/processed/"]
    for pattern in patterns:
        chemin = repertoire / pattern
        if chemin.exists():
            subprocess.run(
                ["git", "add", pattern],
                cwd=str(repertoire),
                capture_output=True,
                text=True,
            )

    # Verifier s'il y a des changements stages
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(repertoire),
        capture_output=True,
    )
    if result.returncode == 0:
        # Pas de changements stages
        return False

    # Commiter
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(repertoire),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
