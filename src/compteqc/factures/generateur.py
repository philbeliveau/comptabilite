"""Generateur de PDF pour les factures.

Utilise Jinja2 pour le template HTML et WeasyPrint pour la conversion en PDF.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from compteqc.factures.modeles import ConfigFacturation, Facture


TEMPLATES_DIR = Path(__file__).parent / "templates"


def generer_pdf(
    facture: Facture,
    config: ConfigFacturation,
    output_dir: Path,
) -> Path:
    """Genere un PDF de la facture et retourne le chemin du fichier."""
    import weasyprint

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("facture.html")

    # Lire le CSS
    css_path = TEMPLATES_DIR / "css" / "facture.css"
    css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    # Injecter la couleur primaire dans le CSS
    css_content = css_content.replace("VAR_COULEUR_PRIMAIRE", config.couleur_primaire)

    html = template.render(
        facture=facture,
        config=config,
        css=css_content,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{facture.numero}.pdf"

    weasyprint.HTML(string=html).write_pdf(str(output_path))
    return output_path
