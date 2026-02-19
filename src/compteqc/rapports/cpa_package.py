"""Orchestrateur du package CPA: genere tous les rapports en un ZIP.

Combine les rapports financiers (balance, resultats, bilan), les annexes
(paie, DPA, taxes, pret actionnaire), la validation GIFI et le checklist
de fin d'exercice dans un ZIP organise pour le CPA.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from rich.console import Console
from rich.table import Table

from compteqc.echeances.verification import Severite, verifier_fin_exercice
from compteqc.mcp.services import calculer_soldes
from compteqc.rapports.balance_verification import BalanceVerification
from compteqc.rapports.bilan import Bilan
from compteqc.rapports.etat_resultats import EtatResultats
from compteqc.rapports.gifi_export import aggregate_by_gifi, export_gifi_csv, extract_gifi_map
from compteqc.rapports.sommaire_dpa import SommaireDPA
from compteqc.rapports.sommaire_paie import SommairePaie
from compteqc.rapports.sommaire_pret import SommairePret
from compteqc.rapports.sommaire_taxes import SommaireTaxes

console = Console()


class CpaPackageError(Exception):
    """Erreur fatale lors de la generation du package CPA."""


def afficher_checklist(resultats: list, console_out: Console | None = None) -> None:
    """Affiche les resultats du checklist en Rich table."""
    c = console_out or console
    table = Table(title="Verification de fin d'exercice")
    table.add_column("Verification", style="bold")
    table.add_column("Statut")
    table.add_column("Message")

    couleur_map = {
        Severite.INFO: "green",
        Severite.WARNING: "yellow",
        Severite.ERROR: "red",
    }
    statut_map = {
        Severite.INFO: "OK",
        Severite.WARNING: "AVERTISSEMENT",
        Severite.ERROR: "ERREUR",
    }

    for r in resultats:
        couleur = couleur_map.get(r.severite, "")
        statut = statut_map.get(r.severite, "?")
        table.add_row(
            r.nom,
            f"[{couleur}]{statut}[/{couleur}]",
            r.message,
        )

    c.print(table)


def generer_package_cpa(
    entries: list,
    annee: int,
    fin_exercice: object = None,
    output_dir: str | Path = ".",
    entreprise: str = "",
    chemin_actifs: str | Path = "data/actifs.yaml",
    console_out: Console | None = None,
) -> Path:
    """Genere le package CPA complet dans un ZIP.

    1. Execute le checklist de fin d'exercice
    2. Abort si erreur fatale (equation comptable)
    3. Genere tous les rapports dans des sous-repertoires
    4. ZIP le tout

    Args:
        entries: Liste d'entrees Beancount.
        annee: Annee fiscale.
        fin_exercice: Date de fin d'exercice (optionnel).
        output_dir: Repertoire de sortie.
        entreprise: Nom de l'entreprise pour les rapports.
        chemin_actifs: Chemin vers le registre d'actifs YAML.
        console_out: Console Rich pour l'affichage (optionnel).

    Returns:
        Chemin du fichier ZIP cree.

    Raises:
        CpaPackageError: Si l'equation comptable est desequilibree.
    """
    output_dir = Path(output_dir)

    # 1. Checklist
    resultats = verifier_fin_exercice(entries, annee, fin_exercice)
    afficher_checklist(resultats, console_out)

    # 2. Check fatals
    fatals = [r for r in resultats if r.severite == Severite.ERROR]
    if fatals:
        msg = "Erreurs fatales detectees: " + "; ".join(r.message for r in fatals)
        raise CpaPackageError(msg)

    # 3. Generate reports
    pkg_dir = output_dir / f"cpa-package-{annee}"
    rapports_dir = pkg_dir / "rapports"
    annexes_dir = pkg_dir / "annexes"
    gifi_dir = pkg_dir / "gifi"

    # Rapports principaux
    BalanceVerification(entries, annee, entreprise).generate(rapports_dir)
    EtatResultats(entries, annee, entreprise).generate(rapports_dir)
    Bilan(entries, annee, entreprise).generate(rapports_dir)

    # Annexes
    SommairePaie(entries, annee, entreprise).generate(annexes_dir)
    SommaireDPA(entries, annee, entreprise, chemin_actifs).generate(annexes_dir)
    SommaireTaxes(entries, annee, entreprise).generate(annexes_dir)
    SommairePret(entries, annee, entreprise).generate(annexes_dir)

    # GIFI export
    soldes = calculer_soldes(entries)
    gifi_map = extract_gifi_map(entries)
    gifi_balances = aggregate_by_gifi(soldes, gifi_map)

    # S100 = balance sheet items (Actifs, Passifs, Capital)
    gifi_s100 = {
        k: v for k, v in gifi_balances.items()
        if any(
            acct.startswith(("Actifs", "Passifs", "Capital"))
            for acct, code in gifi_map.items() if code == k
        )
    }
    # S125 = income statement items (Revenus, Depenses)
    gifi_s125 = {
        k: v for k, v in gifi_balances.items()
        if any(
            acct.startswith(("Revenus", "Depenses"))
            for acct, code in gifi_map.items() if code == k
        )
    }

    gifi_dir.mkdir(parents=True, exist_ok=True)
    if gifi_s100:
        export_gifi_csv(gifi_s100, gifi_dir / "gifi_s100.csv", schedule="S100")
    if gifi_s125:
        export_gifi_csv(gifi_s125, gifi_dir / "gifi_s125.csv", schedule="S125")

    # 4. ZIP
    zip_path = output_dir / f"cpa-package-{annee}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(pkg_dir.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(output_dir)
                zf.write(file_path, arcname)

    return zip_path
