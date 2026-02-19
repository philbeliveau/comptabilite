"""Calcul de la DPA (deduction pour amortissement) par pool.

Implements:
- Declining balance CCA per class at official rates
- Half-year rule on positive net additions (first year 50% of net addition)
- Recapture when UCC goes negative after dispositions
- Terminal loss when class is empty with positive UCC remaining
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from compteqc.quebec.dpa.classes import CLASSES_DPA
from compteqc.quebec.dpa.registre import Actif

TWO_PLACES = Decimal("0.01")


@dataclass
class PoolDPA:
    """Represent un pool DPA pour une classe donnee dans une annee fiscale."""

    classe: int
    taux: Decimal
    ucc_ouverture: Decimal  # FNACC d'ouverture (UCC debut d'annee)
    acquisitions: Decimal  # Acquisitions de l'annee
    dispositions: Decimal  # Dispositions de l'annee (moindre du cout ou produit)

    @property
    def additions_nettes(self) -> Decimal:
        """Additions nettes = acquisitions - dispositions."""
        return self.acquisitions - self.dispositions

    def calculer_dpa(self) -> Decimal:
        """Calcule la DPA avec la regle du demi-taux sur les additions nettes positives.

        Si additions_nettes > 0:
            base = ucc_ouverture + (additions_nettes * 0.5)
        Sinon:
            base = ucc_ouverture + additions_nettes

        DPA = base * taux (arrondi a 2 decimales)

        La DPA ne peut pas depasser la FNACC ajustee (ne peut pas etre negative).
        """
        if self.additions_nettes > 0:
            base = self.ucc_ouverture + (self.additions_nettes * Decimal("0.5"))
        else:
            base = self.ucc_ouverture + self.additions_nettes

        # La base ne peut pas etre negative pour le calcul de la DPA
        if base <= 0:
            return Decimal("0.00")

        dpa = (base * self.taux).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return dpa

    @property
    def ucc_fermeture(self) -> Decimal:
        """FNACC de fermeture = ouverture + additions_nettes - DPA."""
        return self.ucc_ouverture + self.additions_nettes - self.calculer_dpa()

    @property
    def recapture(self) -> Decimal:
        """Recapture si la FNACC apres dispositions est negative.

        Si ucc_ouverture + additions_nettes < 0 (dispositions > UCC + acquisitions),
        la portion negative est une recapture ajoutee au revenu.
        """
        ucc_apres_dispositions = self.ucc_ouverture + self.additions_nettes
        if ucc_apres_dispositions < 0:
            return abs(ucc_apres_dispositions)
        return Decimal("0.00")

    def perte_finale(self, nb_actifs_restants: int) -> Decimal:
        """Perte finale si la classe est vide et la FNACC est positive.

        Applicable seulement quand il ne reste aucun actif dans la classe
        et que la FNACC de fermeture est positive.
        """
        if nb_actifs_restants == 0 and self.ucc_fermeture > 0:
            return self.ucc_fermeture
        return Decimal("0.00")


def construire_pools(
    actifs: list[Actif],
    ucc_precedent: dict[int, Decimal],
    annee: int,
) -> dict[int, PoolDPA]:
    """Construit les pools DPA pour l'annee a partir du registre d'actifs.

    Args:
        actifs: Liste de tous les actifs du registre
        ucc_precedent: FNACC d'ouverture par classe (provient de l'annee precedente)
        annee: Annee fiscale pour le calcul

    Returns:
        Dictionnaire classe -> PoolDPA
    """
    pools: dict[int, PoolDPA] = {}

    # Grouper les actifs par classe
    par_classe: dict[int, list[Actif]] = {}
    for actif in actifs:
        if actif.date_acquisition.year > annee:
            continue
        if actif.classe not in par_classe:
            par_classe[actif.classe] = []
        par_classe[actif.classe].append(actif)

    # Toutes les classes avec des actifs ou des UCC precedents
    toutes_classes = set(par_classe.keys()) | set(ucc_precedent.keys())

    for classe in toutes_classes:
        if classe not in CLASSES_DPA:
            continue

        actifs_classe = par_classe.get(classe, [])
        ucc_ouv = ucc_precedent.get(classe, Decimal("0.00"))

        # Calculer acquisitions de l'annee
        acquisitions = Decimal("0.00")
        for actif in actifs_classe:
            if actif.date_acquisition.year == annee:
                acquisitions += actif.cout

        # Calculer dispositions de l'annee
        # Montant de disposition = min(cout_original, produit_disposition) par les regles de l'ARC
        dispositions = Decimal("0.00")
        for actif in actifs_classe:
            if actif.date_disposition and actif.date_disposition.year == annee:
                produit = actif.produit_disposition or Decimal("0.00")
                dispositions += min(actif.cout, produit)

        pools[classe] = PoolDPA(
            classe=classe,
            taux=CLASSES_DPA[classe]["taux"],
            ucc_ouverture=ucc_ouv,
            acquisitions=acquisitions,
            dispositions=dispositions,
        )

    return pools
