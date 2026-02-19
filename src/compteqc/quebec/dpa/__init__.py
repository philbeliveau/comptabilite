# compteqc.quebec.dpa - Deduction pour amortissement (CCA / Capital Cost Allowance)
#
# Modules:
#   classes.py  - Definitions des classes DPA (taux, descriptions)
#   registre.py - Registre d'actifs immobilises (persistence YAML)
#   calcul.py   - Calcul DPA par pool (declining balance, half-year rule)
#   journal.py  - Generation de transactions Beancount pour la DPA

from compteqc.quebec.dpa.calcul import PoolDPA, construire_pools
from compteqc.quebec.dpa.classes import CLASSES_DPA
from compteqc.quebec.dpa.journal import generer_transactions_dpa
from compteqc.quebec.dpa.registre import Actif, RegistreActifs

__all__ = [
    "CLASSES_DPA",
    "Actif",
    "RegistreActifs",
    "PoolDPA",
    "construire_pools",
    "generer_transactions_dpa",
]
