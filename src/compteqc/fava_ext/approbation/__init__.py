"""Extension Fava: File d'approbation des transactions.

Affiche les transactions #pending avec badges de confiance et
permet l'approbation/rejet par lots via formulaire HTML.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from flask import request
from werkzeug.utils import redirect

from fava.core import FavaLedger
from fava.ext import FavaExtensionBase, extension_endpoint

from compteqc.mcp.services import lister_pending


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def niveau_confiance(confiance: float | str) -> str:
    """Retourne le niveau de confiance: 'elevee', 'moderee', ou 'revision'.

    Args:
        confiance: Score de confiance (float ou string convertible).

    Returns:
        'elevee' si >= 0.95, 'moderee' si >= 0.80, 'revision' sinon.
    """
    try:
        val = float(confiance)
    except (ValueError, TypeError):
        return "revision"
    if val >= 0.95:
        return "elevee"
    if val >= 0.80:
        return "moderee"
    return "revision"


def est_gros_montant(montant: Decimal) -> bool:
    """Retourne True si le montant depasse le seuil de 2000 $."""
    return montant > Decimal("2000")


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------

class ApprobationExtension(FavaExtensionBase):
    """File d'approbation pour les transactions classees par IA."""

    report_title = "File d'approbation"

    def __init__(self, ledger: FavaLedger, config: str | None = None) -> None:
        super().__init__(ledger, config)
        self._pending: list[dict] = []

    def after_load_file(self) -> None:
        """Recharge la liste des transactions pending apres chargement du ledger."""
        self._charger_pending()

    def _charger_pending(self) -> None:
        """Charge les transactions #pending depuis les entrees du ledger."""
        self._pending = lister_pending(self.ledger.all_entries)
        # Enrichir avec le niveau de confiance et le flag gros montant
        for txn in self._pending:
            txn["niveau"] = niveau_confiance(txn["confiance"])
            txn["gros_montant"] = est_gros_montant(txn["montant"])

    def pending_transactions(self) -> list[dict]:
        """Retourne la liste des transactions en attente."""
        return self._pending

    @extension_endpoint("approuver", ["POST"])
    def approuver(self) -> str:
        """Endpoint POST pour approuver des transactions par lots."""
        from compteqc.categorisation.pending import approuver_transactions

        ids = request.form.getlist("ids")
        confirmer_gros = request.form.get("confirmer_gros_montants") == "on"

        indices = [int(i) for i in ids if i.isdigit()]

        # Guardrail: verifier les gros montants
        if not confirmer_gros:
            for idx in indices:
                if idx < len(self._pending) and self._pending[idx].get("gros_montant"):
                    # Retourner une page d'erreur simple
                    return (
                        '<html><body>'
                        '<h2>Confirmation requise</h2>'
                        '<p>Des transactions de plus de 2 000 $ sont selectionnees. '
                        'Veuillez cocher la case de confirmation.</p>'
                        '<a href="javascript:history.back()">Retour</a>'
                        '</body></html>'
                    )

        # Determiner les chemins
        ledger_path = Path(self.ledger.beancount_file_path)
        chemin_main = ledger_path
        chemin_pending = ledger_path.parent / "pending.beancount"

        approuver_transactions(chemin_pending, chemin_main, indices)

        # Recharger le ledger pour rafraichir
        self.ledger.load_file()

        # Redirect vers la page de l'extension
        return redirect(request.referrer or request.url)

    @extension_endpoint("rejeter", ["POST"])
    def rejeter(self) -> str:
        """Endpoint POST pour rejeter une transaction."""
        from compteqc.categorisation.pending import rejeter_transactions

        id_str = request.form.get("id", "")
        if not id_str.isdigit():
            return redirect(request.referrer or request.url)

        idx = int(id_str)
        ledger_path = Path(self.ledger.beancount_file_path)
        chemin_pending = ledger_path.parent / "pending.beancount"

        rejeter_transactions(chemin_pending, [idx])

        # Recharger le ledger pour rafraichir
        self.ledger.load_file()

        return redirect(request.referrer or request.url)
