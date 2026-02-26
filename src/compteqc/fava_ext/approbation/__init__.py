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
        self._enrichir_rapprochements()

    def _enrichir_rapprochements(self) -> None:
        """Enrichir les transactions pending avec des suggestions AR/AP."""
        try:
            from compteqc.rapprochement import (
                suggerer_rapprochement_ar,
                suggerer_rapprochement_ap,
            )
            from compteqc.models.transaction import TransactionNormalisee
        except ImportError:
            # Phase 13 rapprochement module not yet available
            return

        # Load AR invoices
        factures_ar: list = []
        try:
            from compteqc.factures.registre import RegistreFactures
            from compteqc.factures.modeles import InvoiceStatus
            registre_ar = RegistreFactures()
            factures_ar = [
                f for f in registre_ar.lister()
                if f.statut != InvoiceStatus.PAID
            ]
        except (ImportError, Exception):
            pass

        # Load AP bills
        factures_ap: list = []
        try:
            from compteqc.fournisseurs.registre import RegistreFournisseurs
            registre_ap = RegistreFournisseurs()
            factures_ap = registre_ap.lister_impayees()
        except (ImportError, Exception):
            pass

        if not factures_ar and not factures_ap:
            return

        import datetime as _dt

        for txn in self._pending:
            # Convert pending dict to TransactionNormalisee for matching
            try:
                txn_norm = TransactionNormalisee(
                    date=_dt.date.fromisoformat(str(txn["date"])),
                    montant=txn["montant"],
                    devise="CAD",
                    beneficiaire=txn.get("payee", ""),
                    description=txn.get("narration", ""),
                    source="pending",
                )
            except Exception:
                continue

            # Find best AR match (for deposits)
            best_match = None
            if factures_ar and txn["montant"] > 0:
                suggestions = suggerer_rapprochement_ar(txn_norm, factures_ar)
                if suggestions:
                    best_match = suggestions[0]  # Highest confidence

            # Find best AP match (for withdrawals)
            if not best_match and factures_ap and txn["montant"] < 0:
                suggestions = suggerer_rapprochement_ap(txn_norm, factures_ap)
                if suggestions:
                    best_match = suggestions[0]

            if best_match:
                txn["match_apar"] = {
                    "type": best_match.type_match,
                    "numero": best_match.reference,
                    "nom": best_match.nom,
                    "montant": float(best_match.montant_attendu),
                    "confiance": round(best_match.confiance * 100),
                }

    def pending_transactions(self) -> list[dict]:
        """Retourne la liste des transactions en attente."""
        return self._pending

    def account_names(self) -> list[str]:
        """Retourne la liste triee des comptes ouverts du ledger."""
        from beancount.core import getters
        accounts = getters.get_account_open_close(self.ledger.all_entries)
        return sorted(accounts.keys())

    @extension_endpoint("count", ["GET"])
    def pending_count(self):
        """Retourne le nombre de transactions en attente (JSON)."""
        from flask import jsonify
        return jsonify({"count": len(self._pending)})

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

    @extension_endpoint("lier_apar", ["POST"])
    def lier_apar(self) -> str:
        """POST /lier_apar -- lie une transaction pending a une facture AR/AP."""
        txn_index = request.form.get("txn_index", "")
        numero = request.form.get("numero", "")
        match_type = request.form.get("type", "")  # "ar" or "ap"

        if not txn_index.isdigit() or not numero or match_type not in ("ar", "ap"):
            return (
                "<html><body>"
                "<h2>Erreur</h2>"
                "<p>Parametres manquants ou invalides.</p>"
                '<a href="javascript:history.back()">Retour</a>'
                "</body></html>"
            )

        try:
            if match_type == "ar":
                self._lier_ar(numero)
            else:
                self._lier_ap(numero)
        except Exception as e:
            return (
                "<html><body>"
                "<h2>Erreur</h2>"
                "<p>" + str(e) + "</p>"
                '<a href="javascript:history.back()">Retour</a>'
                "</body></html>"
            )

        # Reload ledger and redirect back
        self.ledger.load_file()
        return redirect(request.referrer or request.url)

    def _lier_ar(self, numero: str) -> None:
        """Record AR payment for the given invoice number."""
        from compteqc.factures.registre import RegistreFactures
        from compteqc.factures.modeles import InvoiceStatus
        from compteqc.factures.journal import generer_ecriture_paiement

        registre = RegistreFactures()
        facture = registre.obtenir(numero)
        if facture is None:
            raise ValueError(f"Facture {numero} introuvable.")

        # Generate payment Beancount entry
        ecriture = generer_ecriture_paiement(facture)

        # Append to ledger
        main_beancount = Path(self.ledger.beancount_file_path)
        with open(main_beancount, "a") as f:
            f.write("\n" + ecriture + "\n")

        # Update invoice status
        registre.mettre_a_jour_statut(numero, InvoiceStatus.PAID)

    def _lier_ap(self, numero: str) -> None:
        """Record AP payment for the given bill number."""
        try:
            from compteqc.fournisseurs.registre import RegistreFournisseurs
            from compteqc.fournisseurs.modeles import BillStatus
            from compteqc.fournisseurs.journal import generer_ecriture_paiement_fournisseur
        except ImportError:
            raise ValueError("Module fournisseurs non disponible.")

        registre = RegistreFournisseurs()
        facture = registre.obtenir(numero)
        if facture is None:
            raise ValueError(f"Facture fournisseur {numero} introuvable.")

        # Generate payment Beancount entry
        ecriture = generer_ecriture_paiement_fournisseur(facture)

        # Append to ledger
        main_beancount = Path(self.ledger.beancount_file_path)
        with open(main_beancount, "a") as f:
            f.write("\n" + ecriture + "\n")

        # Update bill status
        registre.mettre_a_jour_statut(numero, BillStatus.PAID)

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
