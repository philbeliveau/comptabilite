"""Classe de base pour la generation de rapports financiers (CSV + PDF).

Fournit l'infrastructure Jinja2 + WeasyPrint pour produire des rapports
en double format (CSV machine-readable et PDF professionnel).
"""

from __future__ import annotations

import csv
import datetime
from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, PackageLoader


class BaseReport(ABC):
    """Classe de base abstraite pour les rapports financiers.

    Les sous-classes doivent implementer:
        - extract_data() -> dict : extraction des donnees du ledger
        - csv_headers() -> list[str] : en-tetes CSV
        - csv_rows() -> list[list] : lignes de donnees CSV
    """

    report_name: str = "rapport"
    template_name: str = "base_report.html"

    def __init__(self, entries: list, annee: int, entreprise: str = "") -> None:
        self.entries = entries
        self.annee = annee
        self.entreprise = entreprise
        self._data: dict | None = None
        self._env = Environment(
            loader=PackageLoader("compteqc.rapports", "templates"),
            autoescape=True,
        )

    @property
    def data(self) -> dict:
        """Donnees extraites du ledger (cache apres premier appel)."""
        if self._data is None:
            self._data = self.extract_data()
        return self._data

    @abstractmethod
    def extract_data(self) -> dict:
        """Extrait les donnees du ledger pour le rapport."""

    @abstractmethod
    def csv_headers(self) -> list[str]:
        """Retourne les en-tetes CSV."""

    @abstractmethod
    def csv_rows(self) -> list[list]:
        """Retourne les lignes de donnees CSV."""

    @staticmethod
    def _q(montant: Decimal) -> Decimal:
        """Quantize un montant a 2 decimales."""
        return montant.quantize(Decimal("0.01"))

    def to_csv(self, output_path: Path) -> Path:
        """Genere le rapport en format CSV.

        Args:
            output_path: Chemin du fichier CSV de sortie.

        Returns:
            Chemin du fichier CSV cree.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.csv_headers())
            for row in self.csv_rows():
                writer.writerow(row)
        return output_path

    def to_pdf(self, output_path: Path) -> Path:
        """Genere le rapport en format PDF via WeasyPrint.

        Args:
            output_path: Chemin du fichier PDF de sortie.

        Returns:
            Chemin du fichier PDF cree.
        """
        from weasyprint import HTML

        output_path.parent.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template(self.template_name)
        css_path = Path(__file__).parent / "templates" / "css" / "report.css"

        context = {
            "entreprise": self.entreprise,
            "annee": self.annee,
            "date_generation": datetime.date.today().isoformat(),
            "report_name": self.report_name,
            **self.data,
        }
        html_str = template.render(**context)
        HTML(string=html_str).write_pdf(str(output_path), stylesheets=[str(css_path)])
        return output_path

    def generate(self, output_dir: Path) -> dict[str, Path]:
        """Genere les deux formats (CSV + PDF) dans le repertoire specifie.

        Args:
            output_dir: Repertoire de sortie.

        Returns:
            Dictionnaire {"csv": Path, "pdf": Path}.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.to_csv(output_dir / f"{self.report_name}.csv")
        pdf_path = self.to_pdf(output_dir / f"{self.report_name}.pdf")
        return {"csv": csv_path, "pdf": pdf_path}
