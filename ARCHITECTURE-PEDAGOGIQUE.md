# Architecture CompteQC : Guide complet du flux de donnees

> De l'importation bancaire jusqu'au package CPA, comment chaque dollar traverse le systeme.

---

## Table des matieres

1. [Vue d'ensemble : Le parcours d'un dollar](#1-vue-densemble)
2. [Couche 1 : Ingestion des donnees](#2-ingestion)
3. [Couche 2 : Pipeline de categorisation (IA)](#3-categorisation)
4. [Couche 3 : Le grand livre (Beancount)](#4-grand-livre)
5. [Couche 4 : Modules financiers du Quebec](#5-modules-quebec)
   - 5a. Paie et retenues a la source
   - 5b. TPS/TVQ
   - 5c. DPA (amortissement)
   - 5d. Pret actionnaire et s.15(2)
   - 5e. Echeances fiscales
   - 5f. Recus et pieces justificatives
6. [Couche 5 : Rapports et etats financiers](#6-rapports)
7. [Couche 6 : Interfaces utilisateur](#7-interfaces)
   - 7a. Serveur MCP (Claude)
   - 7b. CLI (ligne de commande)
   - 7c. Fava (interface web)
8. [Couche 7 : Package CPA](#8-package-cpa)
9. [Diagramme des dependances entre modules](#9-dependances)
10. [Glossaire](#10-glossaire)

---

## 1. Vue d'ensemble : Le parcours d'un dollar {#1-vue-densemble}

Imagine qu'un paiement de 150,00 $ apparait sur ton releve bancaire RBC. Voici son parcours complet a travers CompteQC :

```
 RELEVE BANCAIRE (CSV/OFX)
         |
         v
 [1] INGESTION -----> Normalisation (date, montant Decimal, beneficiaire)
         |                + Deduplication (FITID ou cle composite)
         v
 [1.5] SOURCE TYPE? --> Personnel (--source-type personal)
         |                --> TOUT va dans Passifs:Pret-Actionnaire
         |                --> Flag "*", confiance 1.0, pipeline saute
         | (corporatif, defaut)
         v
 [2] CATEGORISATION --> Regles YAML (confiance 1.0)
         |               --> ML sklearn (confiance variable)
         |               --> LLM Claude (confiance variable)
         |               --> Detecteur CAPEX (>500$ ou vendeur connu)
         v
 [3] ROUTAGE ---------> Auto-approuve (>95%, <=2000$, pas CAPEX)
         |               --> En attente (#pending, revision humaine)
         v
 [4] GRAND LIVRE -----> ledger/2026/02.beancount (transactions approuvees)
         |               ledger/pending.beancount (en attente)
         v
 [5] CALCULS ---------> Paie (retenues + cotisations employeur)
     FINANCIERS          TPS/TVQ (CTI/RTI, remise nette)
                         DPA (amortissement par classe)
                         Pret actionnaire (suivi s.15(2))
         v
 [6] RAPPORTS --------> Balance de verification
                         Bilan
                         Etat des resultats
                         Sommaires (paie, taxes, DPA, pret)
         v
 [7] INTERFACES ------> CLI (Typer)
                         MCP (Claude)
                         Fava (navigateur web)
         v
 [8] PACKAGE CPA -----> ZIP (CSV + PDF + GIFI)
                         Pret pour le comptable
```

**Principe fondamental** : Chaque module ne fait qu'UNE chose. Les modules se parlent via des structures de donnees bien definies (dataclasses, Pydantic models). Le grand livre Beancount est la **source unique de verite**.

---

## 2. Couche 1 : Ingestion des donnees {#2-ingestion}

### Ou ca se trouve

```
src/compteqc/ingestion/
    rbc_cheques.py     # CSV compte cheques RBC
    rbc_carte.py       # CSV carte de credit RBC
    rbc_ofx.py         # Fichiers OFX/QFX (format bancaire standard)
    normalisation.py   # Utilitaires partages
```

### Ce que ca fait

L'ingestion transforme des fichiers bancaires bruts en transactions Beancount normalisees.

### Distinction compte personnel vs corporatif (`--source-type`)

Avant meme la categorisation, le systeme doit savoir si le CSV provient d'un **compte personnel** ou d'un **compte corporatif**. C'est le flag `--source-type` (ou `-s`) de la commande d'importation qui le determine.

**Pourquoi c'est important?**

Quand le CSV vient de ton **compte personnel** (ex: ton compte RBC personnel) :
- Chaque transaction est soit une depense personnelle (irrelevante pour la corp), soit un mouvement de pret actionnaire (virement entre tes comptes personnels et corporatifs)
- Le pipeline de categorisation (regles, ML, LLM) **ne s'execute pas du tout**
- Tout est route directement vers `Passifs:Pret-Actionnaire`

Quand le CSV vient de ton **compte corporatif** (comportement par defaut) :
- Le pipeline normal s'applique (regles --> ML --> LLM)
- Les depenses personnelles sur la carte corp --> `Passifs:Pret-Actionnaire`
- Les depenses d'affaires --> `Depenses:*`

```
CSV personnel (--source-type personal)         CSV corporatif (defaut)
        |                                              |
        v                                              v
  TOUT --> Passifs:Pret-Actionnaire            Pipeline normal
  Flag "*" (auto-approuve)                     (regles/ML/LLM/CAPEX)
  Pas de pending, pas de ML, pas de LLM        Routage selon confiance
  Pipeline JAMAIS cree                         Pending si < 95%
```

**Details techniques** :
- Le flag `--source-type personal` court-circuite la fonction `_appliquer_pipeline_et_router` dans `cli/importer.py`
- Le posting `Depenses:Non-Classe` est remplace par `Passifs:Pret-Actionnaire`
- Les metadonnees `source_type: "personal"` et `categorisation: "personal"` sont ajoutees
- Le `ResultatPipeline` retourne avec `source="personal"` et `confiance=1.0`
- La creation du pipeline (ML, LLM) est entierement evitee dans `_importer_avec` --> pas de cout d'initialisation

### Le modele de donnees central

Chaque transaction importee devient un `TransactionNormalisee` :

```python
# src/compteqc/models/transaction.py

class TransactionNormalisee(BaseModel):
    date: datetime.date           # 2026-02-15
    montant: MontantDecimal       # Decimal("150.00") -- JAMAIS de float
    devise: str = "CAD"
    beneficiaire: str             # "Amazon Seattle"
    description: str              # "AMAZON.CA  SEATTLE WA"
    memo: str | None
    source: str                   # "rbc-cheques-csv" ou "rbc-ofx"
    numero_reference: str | None  # FITID pour OFX
```

**Regle d'or** : Tous les montants utilisent `Decimal`, jamais `float`. Un validateur Pydantic rejette tout float a la validation.

### Comment l'importation fonctionne

#### Etape 1 : Detection du format

Chaque importeur herite de `beangulp.Importer` et implemente trois methodes :

| Methode | Role |
|---------|------|
| `identify(filepath)` | "Est-ce que ce fichier est pour moi ?" |
| `account(filepath)` | "Quel compte Beancount cibler ?" |
| `extract(filepath, existing)` | "Extraire les transactions" |

**Exemple concret** -- le CSV RBC :

```
Type de compte;Date de l'operation;Description 1;Description 2;CAD;USD
Cheques;2/15/2026;AMAZON.CA;SEATTLE WA;-150.00;
```

L'importeur `RBCChequesImporter` :
1. Detecte l'encodage (UTF-8, Latin-1 ou Windows-1252)
2. Cherche la colonne "Type de compte" pour confirmer le format
3. Filtre les lignes ou `Type` commence par "Ch" (Cheques)
4. Convertit la date `M/D/YYYY` en `datetime.date`
5. Parse le montant comme `Decimal`
6. Nettoie le beneficiaire (`AMAZON.CA  SEATTLE WA REF87654` --> `Amazon.Ca Seattle Wa`)

#### Etape 2 : Deduplication

Deux strategies selon la source :

| Source | Strategie | Exemple de cle |
|--------|-----------|----------------|
| OFX/QFX | FITID (identifiant unique bancaire) | `"20260215001234"` |
| CSV | Cle composite | `"2026-02-15\|150.00\|AMAZON.CA SEATTLE"` |

La cle composite CSV utilise : `date|montant|narration[:20]`

#### Etape 3 : Creation de la transaction Beancount

Chaque transaction importee ressemble a ceci dans le fichier :

```beancount
2026-02-15 ! "Amazon.Ca Seattle Wa" "AMAZON.CA SEATTLE WA"
  source: "rbc-cheques-csv"
  categorisation: "non-classe"
  fichier_source: "rbc_2026_02.csv"
  ligne: 42
  Actifs:Banque:RBC:Cheques    -150.00 CAD
  Depenses:Non-Classe           150.00 CAD
```

**A noter** :
- Le `!` signifie "non verifie" (par opposition a `*` = verifie)
- `categorisation: "non-classe"` = pas encore categorise
- La deuxieme ecriture va dans `Depenses:Non-Classe` par defaut --> c'est le pipeline de categorisation qui va la corriger

### Convention de signe pour la carte de credit

```
CSV positif  = achat     --> credit sur le compte carte (augmente la dette)
CSV negatif  = paiement  --> debit sur le compte carte (diminue la dette)
```

Le compte cible est `Passifs:CartesCredit:RBC` (un passif, donc normalement crediteur).

---

## 3. Couche 2 : Pipeline de categorisation (IA) {#3-categorisation}

### Ou ca se trouve

```
src/compteqc/categorisation/
    pipeline.py       # Orchestrateur principal
    moteur.py         # Tier 1 : Moteur de regles YAML
    ml.py             # Tier 2 : Classificateur ML (sklearn SVC)
    llm.py            # Tier 3 : Classificateur LLM (Claude via OpenRouter)
    capex.py          # Detecteur d'immobilisations
    pending.py        # Gestion du fichier pending.beancount
    feedback.py       # Apprentissage des corrections humaines
```

### Architecture en cascade (3 niveaux)

Le pipeline essaie chaque niveau dans l'ordre. Des qu'un niveau repond avec assez de confiance, on s'arrete :

```
Transaction (beneficiaire, narration, montant, source_type)
    |
    v
[SOURCE] source_type == "personal" ?
    |  OUI --> Passifs:Pret-Actionnaire, confiance 1.0, source = "personal"
    |          Flag "*", pas de pending, pipeline JAMAIS cree
    |
    |  NON (corporatif, defaut)
    v
[Tier 1] REGLES YAML -------> Confiance = 1.0, source = "regle"
    |  (pas de match?)
    v
[Tier 2] ML (sklearn SVC) --> Confiance variable, source = "ml"
    |  (pas entraine ou confiance basse?)
    v
[Tier 3] LLM (Claude) ------> Confiance variable, source = "llm"
    |
    v
[CAPEX] Detecteur -----------> est_capex? classe_dpa?
    |
    v
[ROUTAGE] ------------------> "direct" | "pending" | "revue"
```

### Tier 1 : Moteur de regles

**Fichier de regles** : `rules/categorisation.yaml`

```yaml
regles:
  - nom: loyer-bureau-mensuel
    condition:
      payee: "Proprio Bureau.*"    # regex
      montant_min: 1000
      montant_max: 2000
    compte: Depenses:Bureau:Loyer
    confiance: 1.0

  - nom: iga-epicerie-personnel
    condition:
      payee: "(?i)iga|metro|provigo|maxi|super c"
    compte: Passifs:Pret-Actionnaire
    confiance: 0.95
```

**Comment ca marche** :
1. Les regles sont evaluees **dans l'ordre** (premiere qui matche gagne)
2. Les patterns `payee` et `narration` sont des **regex** compilees a l'initialisation
3. Les comptes cibles sont valides contre la liste des comptes ouverts dans le ledger
4. Confiance = 1.0 pour les regles (certitude absolue)

**Modele de resultat** :

```python
@dataclass(frozen=True)
class ResultatCategorisation:
    compte: str            # "Depenses:Bureau:Loyer"
    confiance: float       # 1.0
    regle: str | None      # "loyer-bureau-mensuel"
    source: str            # "regle"
```

### Tier 2 : Classificateur ML

**Algorithme** : `sklearn.svm.SVC` avec noyau lineaire + `probability=True` (Platt scaling)

**Features** : Texte combine `narration + " " + beneficiaire`, vectorise par `CountVectorizer(ngram_range=(1,2))`

**Entrainement** :
- Minimum 20 transactions deja categorisees dans le ledger
- Minimum 2 comptes distincts
- Se fait a partir des transactions existantes non-`Non-Classe`

**Prediction** :
```python
resultat = predicteur_ml.predire("Amazon", "AMAZON.CA SEATTLE", Decimal("150"))
# ResultatML(compte="Depenses:Bureau:Fournitures", confiance=0.87)
```

### Tier 3 : Classificateur LLM

**API** : OpenRouter (compatible OpenAI SDK), modele `anthropic/claude-sonnet-4`

**Prompt systeme** (resume) :
- Contexte : consultant TI solo au Quebec, ~230 000 $/an
- **Regle critique** : depenses personnelles --> `Passifs:Pret-Actionnaire` (conformite s.15(2) LIR)
- Liste complete des comptes valides avec exemples
- Corrections connues (ex: "Adelard Belanger" = epicerie, pas fournitures)
- Instruction : confiance basse si incertain, ne jamais utiliser Non-Classe si evitable

**Sortie structuree** (JSON contraint) :

```json
{
  "compte": "Passifs:Pret-Actionnaire",
  "confiance": 0.92,
  "raisonnement": "Amazon Seattle est probablement un achat personnel...",
  "est_capex": false
}
```

**Journalisation** : Chaque appel LLM est enregistre dans `data/llm_log/categorisations.jsonl` avec un hash SHA-256 du prompt (detection de derive).

### Detecteur CAPEX (immobilisations)

Deux criteres de detection :

| Critere | Seuil | Exemple |
|---------|-------|---------|
| Montant | >= 500 $ | Achat de 1 299,99 $ |
| Vendeur | Nom dans la liste | Apple, Dell, Lenovo, Samsung... |

**Suggestion de classe DPA** :

| Mots-cles | Classe | Taux |
|-----------|--------|------|
| ordinateur, laptop, macbook, moniteur | 50 | 55% |
| telephone, iphone | 50 | 55% |
| meuble, bureau, chaise | 8 | 20% |
| vehicule, auto, camion | 10 | 30% |
| logiciel, software, licence | 12 | 100% |

### Resolution des conflits ML vs LLM

Quand les deux niveaux repondent avec des comptes differents :

```
ML dit: "Depenses:Bureau:Fournitures" (confiance 0.82)
LLM dit: "Passifs:Pret-Actionnaire" (confiance 0.88)

--> revue_obligatoire = True
--> suggestions = {"ml": ("Fournitures", 0.82), "llm": ("Pret-Actionnaire", 0.88)}
--> L'humain doit trancher
```

### Routage final

| Condition | Destination | Action |
|-----------|-------------|--------|
| confiance > 0.95 ET montant <= 2 000 $ ET pas CAPEX | `"direct"` | Ecrit directement au ledger |
| confiance entre 0.80 et 0.95 | `"pending"` | Mis en attente pour revision |
| confiance < 0.80 OU revue_obligatoire | `"revue"` | Revision humaine obligatoire |
| CAPEX detecte | `"pending"` | En attente (classe d'actif a confirmer) |

### Boucle de retroaction (apprentissage)

Quand un humain corrige une categorisation :

```
Correction #1 : "MOLLO CAFE" --> Passifs:Pret-Actionnaire
Correction #2 : "MOLLO CAFE" --> Passifs:Pret-Actionnaire

--> REGLE AUTOMATIQUE GENEREE! (apres 2 corrections identiques)
    Ajoutee a rules/categorisation.yaml avec confiance 0.95
```

**Seuil** : 2 corrections identiques (meme vendeur --> meme compte) = creation automatique d'une regle.

---

## 4. Couche 3 : Le grand livre (Beancount) {#4-grand-livre}

### Structure des fichiers

```
ledger/
    main.beancount           # Point d'entree (inclut tout)
    comptes.beancount        # Plan comptable (directives Open + codes GIFI)
    pending.beancount        # Zone de transit (#pending)
    2026/
        01.beancount         # Janvier 2026
        02.beancount         # Fevrier 2026
        ...
```

### Le plan comptable (adapte Quebec, consultant TI)

#### Actifs (GIFI 1000-1999)

| Compte | GIFI | Description |
|--------|------|-------------|
| `Actifs:Banque:RBC:Cheques` | 1001 | Compte cheques |
| `Actifs:Banque:RBC:Epargne` | 1001 | Compte epargne |
| `Actifs:ComptesClients` | 1060 | Comptes clients |
| `Actifs:TPS-Payee` | 1300 | CTI (credits de taxe intrants) |
| `Actifs:TVQ-Payee` | 1300 | RTI (remboursement taxe intrants) |
| `Actifs:Immobilisations:Informatique` | 1740 | Equipement informatique (cout) |
| `Actifs:Immobilisations:Mobilier` | 1740 | Mobilier de bureau |
| `Actifs:Immobilisations:Amortissement-Cumule` | 1742 | Amortissement cumule |

#### Passifs (GIFI 2000-2999)

| Compte | GIFI | Description |
|--------|------|-------------|
| `Passifs:CartesCredit:RBC` | 2700 | Carte de credit |
| `Passifs:TPS-Percue` | 2620 | TPS percue (a remettre) |
| `Passifs:TVQ-Percue` | 2620 | TVQ percue (a remettre) |
| `Passifs:Retenues:QPP-Base` | 2620 | Retenue RRQ employe |
| `Passifs:Retenues:QPP-Supp1` | 2620 | Retenue RRQ suppl. 1 |
| `Passifs:Retenues:QPP-Supp2` | 2620 | Retenue RRQ suppl. 2 |
| `Passifs:Retenues:RQAP` | 2620 | Retenue RQAP employe |
| `Passifs:Retenues:AE` | 2620 | Retenue assurance-emploi |
| `Passifs:Retenues:Impot-Federal` | 2620 | Retenue impot federal |
| `Passifs:Retenues:Impot-Quebec` | 2620 | Retenue impot Quebec |
| `Passifs:Cotisations-Employeur:QPP` | 2620 | Part employeur RRQ |
| `Passifs:Cotisations-Employeur:RQAP` | 2620 | Part employeur RQAP |
| `Passifs:Cotisations-Employeur:AE` | 2620 | Part employeur AE |
| `Passifs:Cotisations-Employeur:FSS` | 2620 | Fonds services sante |
| `Passifs:Cotisations-Employeur:CNESST` | 2620 | CNESST |
| `Passifs:Pret-Actionnaire` | 2480 | **Pret actionnaire (suivi s.15(2))** |

#### Capitaux propres (GIFI 3000-3999)

| Compte | GIFI | Description |
|--------|------|-------------|
| `Capital:Actions-Ordinaires` | 3500 | Actions ordinaires |
| `Capital:Benefices-Non-Repartis` | 3600 | Benefices non repartis |
| `Capital:Dividendes-Declares` | 3701 | Dividendes declares |

#### Revenus (GIFI 8000+)

| Compte | GIFI | Description |
|--------|------|-------------|
| `Revenus:Consultation` | 8000 | Consultation TI |
| `Revenus:Produit-Logiciel` | 8000 | Revenus Enact |
| `Revenus:Interets` | 8090 | Interets bancaires |

#### Depenses (GIFI 8100+)

| Compte | Description |
|--------|-------------|
| `Depenses:Bureau:Loyer` | Loyer du bureau |
| `Depenses:Bureau:Internet-Telecom` | Internet, telephone |
| `Depenses:Bureau:Abonnements-Logiciels` | SaaS, cloud |
| `Depenses:Bureau:Fournitures` | Fournitures de bureau |
| `Depenses:Salaires:Brut` | Salaire brut verse |
| `Depenses:Repas-Representation` | Repas d'affaires |
| `Depenses:Formation` | Formation, livres |
| `Depenses:Honoraires-Professionnels:Comptable` | Honoraires CPA |
| `Depenses:Non-Classe` | **Placeholder initial** |

### Le flux pending --> approuve

```
                      IMPORT
                        |
                        v
              pending.beancount
              (flag "!", tag #pending)
                        |
           +------------+------------+
           |                         |
      APPROUVER                   REJETER
           |                         |
           v                         v
   ledger/2026/02.beancount     (supprime)
   (flag "*", pas de #pending)
```

**Processus d'approbation** :
1. Lire les transactions `#pending`
2. L'utilisateur selectionne celles a approuver
3. Pour chaque approuvee :
   - Changer le flag de `!` a `*` (verifie)
   - Retirer le tag `#pending`
   - Ecrire dans le fichier mensuel (`ledger/YYYY/MM.beancount`)
   - Ajouter `include "YYYY/MM.beancount"` dans `main.beancount` si absent
4. **Validation** : executer `bean-check` sur tout le ledger
   - Si erreur --> **ROLLBACK** complet (annuler toutes les ecritures)
   - Si OK --> mettre a jour `pending.beancount` (retirer les approuvees)
5. Commit Git automatique

### Convention comptable de Beancount

**Equation fondamentale** : `Actifs + Passifs + Capital + Revenus + Depenses = 0`

| Type de compte | Signe normal | Pour afficher en positif |
|----------------|-------------|--------------------------|
| Actifs | Positif (debit) | Tel quel |
| Passifs | Negatif (credit) | Inverser le signe |
| Capital | Negatif (credit) | Inverser le signe |
| Revenus | Negatif (credit) | Inverser le signe |
| Depenses | Positif (debit) | Tel quel |

C'est pourquoi dans les rapports, on voit souvent `-solde` pour les revenus et les passifs : on les convertit en valeur absolue pour l'affichage.

---

## 5. Couche 4 : Modules financiers du Quebec {#5-modules-quebec}

### 5a. Paie et retenues a la source

#### Ou ca se trouve

```
src/compteqc/quebec/paie/
    moteur.py          # Orchestrateur de calcul de paie
    cotisations.py     # QPP, RQAP, AE, FSS, CNESST, Normes
    impot_federal.py   # Calcul d'impot federal par periode
    impot_quebec.py    # Calcul d'impot Quebec par periode
    ytd.py             # Cumuls annuels (year-to-date)
    journal.py         # Generation des ecritures Beancount

src/compteqc/quebec/rates.py  # Tous les taux et seuils 2026
```

#### Les taux 2026 (source unique de verite)

**RRQ/QPP** :

| Parametre | Valeur |
|-----------|--------|
| Taux base employe | 5,30 % |
| Taux supplementaire 1 | 1,00 % |
| Taux supplementaire 2 | 4,00 % |
| Exemption de base | 3 500 $ |
| MGA (maximum gains admissibles) | 74 600 $ |
| MGAP (MGA supplementaire) | 85 000 $ |
| Maximum annuel base | 3 768,30 $ |
| Maximum annuel supp. 1 | 711,00 $ |
| Maximum annuel supp. 2 | 416,00 $ |

**RQAP** :

| Parametre | Employe | Employeur |
|-----------|---------|-----------|
| Taux | 0,430 % | 0,602 % |
| MRA | 103 000 $ | 103 000 $ |
| Maximum annuel | 442,90 $ | 620,06 $ |

**AE (taux Quebec)** :

| Parametre | Employe | Employeur |
|-----------|---------|-----------|
| Taux | 1,30 % | 1,82 % (1,4x) |
| MRA | 68 900 $ | 68 900 $ |
| Maximum annuel | 895,70 $ | 1 253,98 $ |

**Autres cotisations employeur** :

| Cotisation | Taux | Base |
|------------|------|------|
| FSS (Fonds services sante) | 1,65 % | Masse salariale annuelle estimee |
| CNESST | 0,80 % | Salaire brut (sans plafond) |
| Normes du travail | 0,06 % | Jusqu'a 103 000 $ |

**Impot federal** (5 paliers) :

| Palier | Taux | Seuil |
|--------|------|-------|
| 1 | 14,0 % | 0 - 57 375 $ |
| 2 | 20,5 % | 57 375 - 114 750 $ |
| 3 | 26,0 % | 114 750 - 158 468 $ |
| 4 | 29,0 % | 158 468 - 223 210 $ |
| 5 | 33,0 % | 223 210 $+ |

Montant personnel de base : 16 452 $ | Abattement Quebec : 16,5 %

**Impot Quebec** (4 paliers) :

| Palier | Taux | Seuil |
|--------|------|-------|
| 1 | 14,0 % | 0 - 53 255 $ |
| 2 | 19,0 % | 53 255 - 106 495 $ |
| 3 | 24,0 % | 106 495 - 129 590 $ |
| 4 | 25,75 % | 129 590 $+ |

Montant personnel de base : 18 952 $ | Deduction travailleur : 6 % (max 1 450 $)

#### Flux de calcul d'une paie

```
calculer_paie(brut=5000$, periode=1, nb_periodes=26)
    |
    +---> obtenir_cumuls_annuels(ledger)
    |     # Lit toutes les transactions "paie" de l'annee
    |     # Retourne: {qpp_base: 0$, ae: 0$, impot_fed: 0$, ...}
    |
    +---> RETENUES EMPLOYE
    |     |
    |     +---> calculer_qpp_base_employe()
    |     |     # gains = min(brut, MGA/26) - exemption/26
    |     |     # = min(5000, 2869.23) - 134.62
    |     |     # = 2734.62 * 5.30% = 144.93$
    |     |     # Plafonner: max(3768.30 - cumul_ytd, 0)
    |     |
    |     +---> calculer_qpp_supp1_employe()
    |     |     # Meme base que QPP, SANS exemption
    |     |     # = 2869.23 * 1.00% = 28.69$
    |     |
    |     +---> calculer_qpp_supp2_employe()
    |     |     # UNIQUEMENT sur gains entre MGA et MGAP
    |     |     # = min(5000, 85000/26) - 74600/26
    |     |     # = min(5000, 3269.23) - 2869.23
    |     |     # = 400.00 * 4.00% = 16.00$
    |     |
    |     +---> calculer_rqap_employe()
    |     |     # = min(5000, 103000/26) * 0.430% = 21.50$
    |     |
    |     +---> calculer_ae_employe()
    |     |     # = min(5000, 68900/26) * 1.30% = 34.46$
    |     |
    |     +---> calculer_impot_federal_periode()
    |     |     # 1. Annualiser: 5000 * 26 = 130,000$
    |     |     # 2. Trouver palier: 26% sur 114,750-158,468
    |     |     # 3. Credits: K1 (personnel) + K2Q (cotisations) + K4 (emploi)
    |     |     # 4. Impot annuel brut - credits
    |     |     # 5. Appliquer abattement Quebec 16.5%
    |     |     # 6. Diviser par 26 periodes
    |     |
    |     +---> calculer_impot_quebec_periode()
    |           # 1. Annualiser: 130,000$
    |           # 2. Deduction travailleur: min(130000*6%, 1450) = 1450$
    |           # 3. Revenu imposable: 128,550$
    |           # 4. Trouver palier: 24% sur 106,495-129,590
    |           # 5. Credits: K1 + E (QPP total + RQAP)
    |           # 6. Diviser par 26
    |
    +---> COTISATIONS EMPLOYEUR
    |     |
    |     +---> QPP employeur (miroir de l'employe, avec plafonds separes)
    |     +---> RQAP employeur (taux 0.602% vs 0.430%)
    |     +---> AE employeur (taux 1.82% vs 1.30%, soit 1.4x)
    |     +---> FSS: masse_salariale_estimee * 1.65% / 26
    |     +---> CNESST: 5000 * 0.80% = 40.00$
    |     +---> Normes: min(5000, (103000 - cumul)/26) * 0.06%
    |
    +---> RESULTAT
          {
            brut: 5000.00,
            retenues: {qpp_base: 144.93, qpp_supp1: 28.69, ...},
            total_retenues: ~1100$,
            cotisations: {qpp_emp: 144.93, rqap_emp: 30.10, ...},
            total_cotisations: ~350$,
            net: ~3900$ (brut - total_retenues)
          }
```

#### Ecriture comptable generee (~20 lignes)

```beancount
2026-02-15 * "Paie - Periode 1" "" #paie
  type: "paie"
  periode: 1
  brut: "5000.00"

  ; --- Salaire brut (depense) ---
  Depenses:Salaires:Brut                     5,000.00 CAD

  ; --- Retenues employe (vers les passifs) ---
  Passifs:Retenues:QPP-Base                   -144.93 CAD
  Passifs:Retenues:QPP-Supp1                   -28.69 CAD
  Passifs:Retenues:QPP-Supp2                   -16.00 CAD
  Passifs:Retenues:RQAP                        -21.50 CAD
  Passifs:Retenues:AE                          -34.46 CAD
  Passifs:Retenues:Impot-Federal              -XXX.XX CAD
  Passifs:Retenues:Impot-Quebec               -XXX.XX CAD

  ; --- Salaire net verse (sort de la banque) ---
  Actifs:Banque:RBC:Cheques                -3,9XX.XX CAD

  ; --- Cotisations employeur (depenses) ---
  Depenses:Salaires:RRQ-Employeur              189.62 CAD
  Depenses:Salaires:RQAP-Employeur              30.10 CAD
  Depenses:Salaires:AE-Employeur                48.25 CAD
  Depenses:Salaires:FSS                         XX.XX CAD
  Depenses:Salaires:CNESST                      40.00 CAD
  Depenses:Salaires:Normes-Travail               1.XX CAD

  ; --- Cotisations employeur (vers les passifs) ---
  Passifs:Cotisations-Employeur:QPP           -189.62 CAD
  Passifs:Cotisations-Employeur:RQAP           -30.10 CAD
  Passifs:Cotisations-Employeur:AE             -48.25 CAD
  Passifs:Cotisations-Employeur:FSS            -XX.XX CAD
  Passifs:Cotisations-Employeur:CNESST         -40.00 CAD
  Passifs:Cotisations-Employeur:Normes-Travail  -1.XX CAD
```

**Pourquoi autant de lignes?** Chaque retenue et cotisation doit :
1. Apparaitre comme **depense** (pour l'etat des resultats)
2. Etre comptabilisee dans un **passif** (jusqu'a la remise au gouvernement)
3. Etre tracable individuellement pour les **cumuls YTD** et les **maximums annuels**

#### Cumuls YTD (annee a date)

Le module `ytd.py` lit le ledger et accumule les montants de chaque compte de retenue/cotisation. Ceci est **essentiel** car :

- Chaque deduction a un **maximum annuel** (ex: QPP base = 3 768,30 $/an)
- Le calcul de la periode courante doit savoir combien a **deja ete retenu**
- Formule : `retenue_periode = min(calcul_brut, maximum_annuel - cumul_ytd)`

#### Exemple complet de bout en bout : lancer une paie et la voir dans Fava

Cette section montre le parcours complet d'une paie, du moment ou tu tapes la commande jusqu'a ce que tu la voies dans Fava.

##### Etape 1 : Tu decides ton salaire brut

```bash
cqc paie lancer 5000
```

**Pourquoi tu dois choisir le montant toi-meme?** Parce que le montant du salaire est une **decision de strategie fiscale**, pas un calcul automatique. Le systeme de categorisation IA classe tes *depenses* (ce cafe est-il personnel ou d'affaires?), mais le montant de ton salaire est un choix delibere que tu fais avec ton CPA :

| Ce que le systeme decide (automatique) | Ce que TU decides (strategie) |
|---------------------------------------|------------------------------|
| Combien de QPP retenir sur 5 000 $ | Combien te payer en salaire |
| Combien d'impot federal retenir | Salaire vs dividendes |
| Combien de RQAP, AE, etc. | Quand verser la paie |
| Les cotisations employeur exactes | Combien compenser le pret actionnaire |

Ton CPA pourrait dire : "Paie-toi 110 000 $/an" --> ca donne ~4 230,77 $ par periode bi-hebdomadaire :

```bash
cqc paie lancer 4230.77
```

**Options disponibles** :

```bash
# Simulation sans ecrire au ledger (apercu)
cqc paie lancer 5000 --dry-run

# Specifier le numero de periode manuellement
cqc paie lancer 5000 --periode 3

# Compenser une partie du salaire contre le pret actionnaire
cqc paie lancer 5000 --salary-offset 500

# Changer le nombre de periodes par annee
cqc paie lancer 5000 --nb-periodes 24
```

##### Etape 2 : `moteur.py` orchestre tous les calculs

Une fois que tu as dit "5 000 $ brut", voici ce qui se passe dans le code :

```
calculer_paie(brut=5000, periode=1, nb_periodes=26)
    |
    +---> 1. Lire les cumuls YTD depuis le ledger
    |        (combien a DEJA ete retenu cette annee?)
    |
    +---> 2. RETENUES EMPLOYE (ce qu'on enleve de TON cheque) :
    |        |
    |        +-- QPP Base :  min(5000, 74600/26) - 3500/26
    |        |               = 2734.62 * 5.30%
    |        |               = 144.93 $
    |        |
    |        +-- QPP Supp1 : min(5000, 74600/26) * 1.00%
    |        |               = 28.69 $
    |        |
    |        +-- QPP Supp2 : gains entre MGA et MGAP * 4.00%
    |        |               = 16.00 $
    |        |
    |        +-- RQAP :      min(5000, 103000/26) * 0.430%
    |        |               = 21.50 $
    |        |
    |        +-- AE :        min(5000, 68900/26) * 1.30%
    |        |               = 34.46 $
    |        |
    |        +-- Impot federal : annualiser 5000*26 = 130 000 $
    |        |                   trouver palier (26%)
    |        |                   appliquer credits (K1, K2Q, K4)
    |        |                   abattement Quebec 16.5%
    |        |                   diviser par 26
    |        |
    |        +-- Impot Quebec :  annualiser 130 000 $
    |                            deduction travailleur (min(6%, 1450$))
    |                            trouver palier (24%)
    |                            appliquer credits (K1, QPP, RQAP)
    |                            diviser par 26
    |
    +---> 3. COTISATIONS EMPLOYEUR (cout supplementaire pour la corp) :
    |        |
    |        +-- QPP employeur : miroir de l'employe
    |        +-- RQAP employeur : 0.602% (plus que l'employe)
    |        +-- AE employeur : 1.82% (1.4x le taux employe)
    |        +-- FSS : masse salariale estimee * 1.65% / 26
    |        +-- CNESST : 5000 * 0.80% = 40.00 $
    |        +-- Normes : min(5000, restant jusqu'a 103000) * 0.06%
    |
    +---> 4. RESULTAT :
             Brut :                    5 000,00 $
             Total retenues employe :  ~1 100 $
             Salaire net (ton depot) : ~3 900 $
             Cotisations employeur :   ~350 $
             Cout total pour la corp : ~5 350 $
```

**Chaine d'appel dans le code** :

```
src/compteqc/cli/paie.py          --> commande CLI "cqc paie lancer"
    |
    v
src/compteqc/quebec/paie/moteur.py --> calculer_paie() orchestre tout
    |
    +-- src/compteqc/quebec/paie/cotisations.py  --> 10 fonctions pures de calcul
    +-- src/compteqc/quebec/paie/impot_federal.py --> calcul impot federal
    +-- src/compteqc/quebec/paie/impot_quebec.py  --> calcul impot Quebec
    +-- src/compteqc/quebec/paie/ytd.py           --> cumuls depuis le ledger
    +-- src/compteqc/quebec/rates.py              --> taux et seuils 2026
    |
    v
    Retourne: ResultatPaie (dataclass avec tous les montants)
```

##### Etape 3 : `journal.py` ecrit au ledger

Le `ResultatPaie` est converti en transaction Beancount (~20 lignes) et ecrit dans le fichier mensuel :

```
src/compteqc/quebec/paie/journal.py --> generer_transaction_paie()
    |
    v
ledger/2026/02.beancount            --> transaction ajoutee a la fin du fichier
    |
    v
ledger/main.beancount               --> include "2026/02.beancount" ajoute si absent
```

La transaction generee ressemble a ceci (voir la section "Ecriture comptable generee" ci-dessus).

##### Etape 4 : Fava recharge et affiche le tableau de bord

Apres l'ecriture au ledger :

1. Fava detecte que le fichier a change et **recharge automatiquement**
2. L'extension `PaieQCExtension` (`src/compteqc/fava_ext/paie_qc/`) recalcule ses donnees
3. Le tableau de bord se met a jour :

```
+----------------------------+----------------------------+----------------------------+
|  SALAIRE BRUT YTD          |  RETENUES EMPLOYE          |  COTISATIONS EMPLOYEUR     |
|  5 000,00 $                |  ~1 100 $ (rouge)          |  ~350 $ (orange)           |
+----------------------------+----------------------------+----------------------------+
|  SALAIRE NET YTD           |
|  ~3 900 $ (vert)           |
+----------------------------+

COTISATIONS :
+--------------------+-------------+---------------+----------------+------------------+
| Cotisation         | Employe YTD | Employeur YTD | Maximum annuel | Statut           |
+--------------------+-------------+---------------+----------------+------------------+
| RRQ/QPP base       |   144,93 $  |    144,93 $   |  3 768,30 $    | [====] 3 623 $ restant |
| QPP supp. 1        |    28,69 $  |     28,69 $   |    711,00 $    | [==] 682 $ restant     |
| RQAP               |    21,50 $  |     30,10 $   |    442,90 $    | [==] 421 $ restant     |
| AE                 |    34,46 $  |     48,25 $   |    895,70 $    | [==] 861 $ restant     |
| FSS                |      - $    |     XX,XX $   |       -        |    -                   |
| CNESST             |      - $    |     40,00 $   |       -        |    -                   |
| Normes du travail  |      - $    |      1,XX $   |       -        |    -                   |
+--------------------+-------------+---------------+----------------+------------------+

RETENUES D'IMPOT :
+----------+-------------------+
| Palier   | Impot retenu YTD  |
+----------+-------------------+
| Federal  |    XXX,XX $       |
| Quebec   |    XXX,XX $       |
+----------+-------------------+
```

Les barres de progression se remplissent au fil des periodes de paie. Quand une cotisation atteint son maximum annuel (ex: QPP base = 3 768,30 $), le statut passe a "Maximum atteint" et le systeme arrete de retenir pour cette cotisation.

##### Etape 5 (optionnel) : Compensation du pret actionnaire

Si tu as utilise la carte de la corp pour des achats personnels (Mollo Cafe, epicerie, etc.), ces montants sont dans `Passifs:Pret-Actionnaire`. Tu peux compenser une partie de ton salaire net pour rembourser ce pret :

```bash
cqc paie lancer 5000 --salary-offset 500
```

Cela genere une ecriture supplementaire :

```beancount
  ; --- Compensation pret actionnaire ---
  Passifs:Pret-Actionnaire              -500.00 CAD   ; rembourse le pret
  ; Le depot bancaire net sera: 3 900 - 500 = 3 400 $
```

C'est important pour eviter les problemes de la section 15(2) de la Loi de l'impot sur le revenu (voir la section 5d ci-dessous).

##### Resume : de la commande a Fava

```
toi: "cqc paie lancer 5000"
  |
  v
CLI (paie.py) --> moteur.py --> cotisations.py + impots --> ResultatPaie
  |
  v
journal.py --> ecrit dans ledger/2026/02.beancount
  |
  v
Fava recharge --> PaieQCExtension recalcule --> tableau de bord mis a jour
  |
  v
Tu vois : http://localhost:5001/.../extension/PaieQCExtension/
  Brut: 5 000 $ | Retenues: ~1 100 $ | Net: ~3 900 $ | Cotisations: ~350 $
```

### 5b. TPS/TVQ (taxes de vente)

#### Ou ca se trouve

```
src/compteqc/quebec/taxes/
    calcul.py         # Extraction et application des taxes
    traitement.py     # Regles de traitement fiscal
    sommaire.py       # Generation des sommaires periodiques
```

#### Comment les taxes sont calculees

**Extraction a partir d'un montant TTC** (taxes incluses) :

```python
extraire_taxes(total_ttc=114.98)
# tps = round(114.98 * 5 / 114.975, 2) = 5.00$
# tvq = round(114.98 * 9.975 / 114.975, 2) = 9.98$
# avant_taxes = 114.98 - 5.00 - 9.98 = 100.00$  (valeur "plug")
```

**Regle importante** : Le montant avant taxes est calcule comme "plug value" (`total - tps - tvq`) pour garantir que la somme est exacte. Jamais de multiplication combinee a 14,975 %.

#### Traitement fiscal par categorie

Chaque depense n'est pas forcement taxable. Le systeme determine le traitement fiscal :

| Traitement | TPS | TVQ | Exemples |
|------------|-----|-----|----------|
| `taxable` | Oui | Oui | Fournitures, loyer, repas |
| `exempt` | Non | Non | Frais bancaires, assurances, salaires |
| `zero` | 0% | 0% | Formation (detaxe) |
| `tps_seulement` | Oui | Non | Fournisseurs hors-Quebec (AWS) |

**Priorite de resolution** : Vendeur (plus specifique) --> Categorie --> Defaut global (taxable)

#### Comptes de suivi

```
DEPENSE avec taxes:
  Depenses:Bureau:Fournitures     100.00 CAD  (montant HT)
  Actifs:TPS-Payee                  5.00 CAD  (CTI a reclamer)
  Actifs:TVQ-Payee                  9.98 CAD  (RTI a reclamer)
  Actifs:Banque:RBC:Cheques      -114.98 CAD  (montant TTC paye)

REVENU avec taxes:
  Actifs:ComptesClients           114.98 CAD  (montant TTC recu)
  Revenus:Consultation           -100.00 CAD  (revenu HT)
  Passifs:TPS-Percue               -5.00 CAD  (TPS a remettre)
  Passifs:TVQ-Percue               -9.98 CAD  (TVQ a remettre)
```

#### Sommaire de remise

```
Remise nette TPS = TPS percue - CTI (TPS payee)
                 = Passifs:TPS-Percue - Actifs:TPS-Payee

Remise nette TVQ = TVQ percue - RTI (TVQ payee)
                 = Passifs:TVQ-Percue - Actifs:TVQ-Payee

Si positif --> montant a remettre au gouvernement
Si negatif --> remboursement a recevoir
```

#### Exemple complet de bout en bout : comment la TPS/TVQ arrive dans Fava

Cette section montre un cas reel du ledger pour illustrer le parcours d'une transaction de taxes.

##### La transaction reelle (trouvee dans le ledger)

Dans `ledger/pending.beancount`, on retrouve cette transaction :

```beancount
2026-01-05 ! "Tps Canada" "TPS CANADA" #pending
  source: "rbc-cheques-csv"
  categorisation: "llm"
  fichier_source: "csv4883.csv"
  ligne: "34"
  confiance: "0.95"
  source_ia: "llm"
  compte_propose: "Depenses:TPS-Remise"
  Actifs:Banque:RBC:Cheques   89.56 CAD
  Actifs:TPS-Payee           -89.56 CAD
```

##### Ce que ca veut dire

C'est un **remboursement de TPS du gouvernement**. Le 5 janvier 2026, l'ARC t'a envoye 89,56 $ — un remboursement de TPS que tu avais payee sur tes achats d'affaires (tes credits de taxe sur intrants / CTI).

Le parcours de cette transaction :

```
1. Tu achetes des trucs et tu paies la TPS dessus
   (accumulee dans Actifs:TPS-Payee au fil des achats)

2. Tu remplis ta declaration de TPS et tu reclames tes CTI

3. L'ARC te rembourse 89,56 $ le 2026-01-05

4. Le systeme enregistre :
   Actifs:Banque:RBC:Cheques   +89.56 CAD   ← argent entre dans ton compte
   Actifs:TPS-Payee            -89.56 CAD   ← credit CTI utilise (reduit)
```

##### Comment cette transaction a ete categorisee

```
1. IMPORTATION : le CSV RBC contenait une ligne "TPS CANADA  89.56"

2. CATEGORISATION : le pipeline IA a traite la transaction :
   - Tier 1 (regles YAML) : pas de match
   - Tier 2 (ML) : pas assez de donnees d'entrainement
   - Tier 3 (LLM Claude) : a reconnu "TPS CANADA" comme un remboursement de TPS
     - compte propose : "Depenses:TPS-Remise" (le LLM a hesite)
     - confiance : 0.95
     - source : "llm"

3. ROUTAGE : confiance 0.95 mais < 1.0 --> mis dans #pending (en attente)

4. ECRITURE : place dans ledger/pending.beancount avec flag "!" (non verifie)
```

##### Ce que Fava affiche dans TaxesQCExtension

L'extension TPS/TVQ lit les soldes directement depuis le ledger :

```
Actifs:TPS-Payee   = -89.56 $   (le remboursement a reduit le solde a negatif)
Passifs:TPS-Percue =   0.00 $   (aucune facture de consultation envoyee encore)
Passifs:TVQ-Percue =   0.00 $
Actifs:TVQ-Payee   =   0.00 $
```

Le calcul de la remise nette :

```
Remise nette TPS = TPS percue - CTI
                 = 0.00 - (-89.56)
                 = 89.56 $
```

Ce qui donne le tableau de bord :

```
+----------------------------+----------------------------+----------------------------+
|  REMISE NETTE TPS          |  REMISE NETTE TVQ          |  TRANSACTIONS              |
|  89.56 $ (rouge)           |  0.00 $                    |  1                         |
+----------------------------+----------------------------+----------------------------+

+---------------------+------------+------------+----------+----------+-----------+-----------+------+
| Periode             | TPS percue | TVQ percue | CTI(TPS) | RTI(TVQ) | Remise TPS| Remise TVQ| Txns |
+---------------------+------------+------------+----------+----------+-----------+-----------+------+
| 2026-01-01 au       |            |            |          |          |           |           |      |
|   2026-12-31        |   0.00 $   |   0.00 $   | -89.56 $ |  0.00 $  |  89.56 $  |   0.00 $  |  1   |
+---------------------+------------+------------+----------+----------+-----------+-----------+------+
| Total annuel        |   0.00 $   |   0.00 $   | -89.56 $ |  0.00 $  |  89.56 $  |   0.00 $  |  1   |
+---------------------+------------+------------+----------+----------+-----------+-----------+------+

Note : Remise nette positive = montant du au gouvernement.
       Negative = remboursement a recevoir.
```

##### Ce qui va changer quand tu factureras des clients

Quand tu enverras ta premiere facture de consultation (ex: 10 000 $ + taxes) :

```beancount
2026-03-15 * "Client XYZ" "Consultation TI - Mars 2026"
  Actifs:ComptesClients          11 497.50 CAD   ; montant TTC
  Revenus:Consultation          -10 000.00 CAD   ; revenu HT
  Passifs:TPS-Percue               -500.00 CAD   ; TPS 5% a remettre
  Passifs:TVQ-Percue               -997.50 CAD   ; TVQ 9.975% a remettre
```

Le tableau de bord deviendrait :

```
Remise nette TPS = 500.00 - (-89.56) = 589.56 $   ← a remettre au gouvernement
Remise nette TVQ = 997.50 - 0.00     = 997.50 $   ← a remettre au gouvernement
```

##### Chaine de donnees complete : du CSV a Fava

```
csv4883.csv (releve RBC)
  |  "TPS CANADA  89.56"
  v
ingestion/rbc_cheques.py --> normalise la transaction
  v
categorisation/pipeline.py --> Tier 3 (LLM) reconnait "TPS CANADA"
  v
pending.beancount --> en attente de revision humaine (#pending)
  v
[toi: tu approuves ou corriges]
  v
ledger/2026/01.beancount --> transaction verifiee (flag "*")
  v
Fava recharge --> TaxesQCExtension lit Actifs:TPS-Payee et Passifs:TPS-Percue
  v
Tableau de bord : Remise nette TPS = 89.56 $
```

**Note importante** : Cette transaction est encore `#pending` (flag `!`). Elle a ete categorisee par le LLM avec confiance 0.95 et attend ton approbation. Meme en attente, elle apparait dans les totaux du tableau de bord TPS/TVQ car le fichier `pending.beancount` est inclus dans le ledger.

### 5c. DPA (Deduction pour amortissement / CCA)

#### Ou ca se trouve

```
src/compteqc/quebec/dpa/
    classes.py    # Definition des classes (8, 10, 12, 50, 54)
    registre.py   # Registre YAML des actifs
    calcul.py     # Calcul DPA avec regle du demi-taux
    journal.py    # Generation des ecritures d'amortissement
```

#### Les classes supportees

| Classe | Taux | Description | Exemples |
|--------|------|-------------|----------|
| 8 | 20 % | Mobilier et equipement | Bureau, chaise |
| 10 | 30 % | Vehicules | Auto, camion |
| 12 | 100 % | Logiciels et outils < 500 $ | Licences, petits outils |
| 50 | 55 % | Materiel informatique | Mac Studio, moniteurs |
| 54 | 30 % | Vehicules zero emission | Tesla, etc. |

#### Registre des actifs

Les actifs sont stockes dans `data/actifs.yaml` :

```yaml
actifs:
  - id: "mac-studio-2026"
    description: "Mac Studio M4 Ultra"
    classe: 50
    cout: "15000.00"
    date_acquisition: "2026-01-15"
```

#### Calcul de la DPA (regle du demi-taux)

Pour chaque classe d'actifs :

```
1. FNACC d'ouverture (solde d'amortissement non amorti)
   + Acquisitions de l'annee
   - Dispositions de l'annee (moindre du cout ou produit)
   = Base avant demi-taux

2. Si acquisitions nettes > 0 :
     Base DPA = FNACC ouverture + (acquisitions nettes * 50%)
                                   ^^^ REGLE DU DEMI-TAUX

3. DPA = Base DPA * taux de la classe

4. FNACC de fermeture = FNACC ouverture + acquisitions - dispositions - DPA
```

**Exemple concret** (classe 50, taux 55 %) :

```
FNACC ouverture:     0 $
Acquisition:    15 000 $  (Mac Studio)
Demi-taux:       7 500 $  (15000 * 50%)

Base DPA = 0 + 7 500 = 7 500 $
DPA = 7 500 * 55% = 4 125 $

FNACC fermeture = 0 + 15 000 - 4 125 = 10 875 $
```

**Attention** : La DPA est **discretionnaire** (le CPA decide combien reclamer). C'est pourquoi les ecritures utilisent le flag `!` (a verifier).

### 5d. Pret actionnaire et section 15(2)

#### Ou ca se trouve

```
src/compteqc/quebec/pret_actionnaire/
    suivi.py       # Suivi du solde et des mouvements
    alertes.py     # Calcul des dates s.15(2) et alertes
    detection.py   # Detection de circularite s.15(2.6)
```

#### Pourquoi c'est critique

Si tu es actionnaire de ta corporation et que tu utilises la carte de la compagnie pour des achats personnels, tu crees un **pret de l'actionnaire**. La **section 15(2) de la Loi de l'impot sur le revenu** dit :

> Si ce pret n'est pas rembourse avant la fin de l'exercice fiscal suivant, le montant est **inclus dans ton revenu personnel** comme avantage imposable.

**Exemple** :
- Avance personnelle le 15 juin 2026
- Fin de l'exercice fiscal : 31 decembre 2026
- **Date limite de remboursement** : 31 decembre 2027
- Si non rembourse --> le montant est ajoute a ton T1/TP-1 comme revenu

#### Suivi des mouvements (FIFO)

Les remboursements sont appliques aux avances les plus anciennes en premier (FIFO) :

```
Avance #1: 2026-03-15, 500$
Avance #2: 2026-06-20, 300$
Remboursement: 2026-09-01, -400$

Apres FIFO:
  Avance #1: solde restant = 100$ (500 - 400)
  Avance #2: solde restant = 300$ (pas touche)
```

#### Systeme d'alertes

| Niveau | Delai | Action suggeree |
|--------|-------|-----------------|
| `11_mois` | 11 mois avant date limite | Planifier le remboursement |
| `9_mois` | 9 mois avant | Prioriser le remboursement |
| `30_jours` | 30 jours avant | **URGENT** - rembourser immediatement |
| `depasse` | Date limite passee | **CRITIQUE** - inclusion au revenu |

#### Detection de circularite (s.15(2.6))

Le systeme detecte les schemas d'evitement :

```
Remboursement de 5 000$ le 15 decembre 2027 (juste avant la date limite)
Nouvelle avance de 4 800$ le 5 janvier 2028

--> ALERTE: remboursement suivi d'une avance de montant similaire (±20%)
    dans une fenetre de 30 jours = possible circularite s.15(2.6)
```

### 5e. Echeances fiscales

#### Ou ca se trouve

```
src/compteqc/echeances/
    calendrier.py    # Calendrier des obligations
    remises.py       # Suivi des remises de paie
    verification.py  # Verifications de fin d'exercice
```

#### Calendrier des obligations

| Type | Date limite | Frequence |
|------|-------------|-----------|
| T4/Releve 1 | 28 fevrier (annee suivante) | Annuel |
| T2 (federal) | 6 mois apres fin exercice | Annuel |
| CO-17 (Quebec) | Meme date que T2 | Annuel |
| TPS/TVQ | Fin trimestre + 1 mois | Trimestriel |
| Remise paie | 15 du mois suivant | Mensuel |
| Pret actionnaire | Fin exercice + 1 an | Par avance |

**Ajustement jours ouvrables** : Si la date tombe un samedi ou dimanche, elle est reportee au lundi suivant (regle standard de l'ARC).

#### Niveaux d'urgence

| Niveau | Jours restants | Couleur CSS |
|--------|---------------|-------------|
| `critique` | <= 7 jours | Rouge |
| `urgent` | <= 14 jours | Orange |
| `normal` | <= 30 jours | Jaune |
| `info` | <= 90 jours | Bleu |

### 5f. Recus et pieces justificatives (piste de verification)

#### Ou ca se trouve

```
src/compteqc/documents/
    upload.py           # Stockage fichier + redimensionnement image
    extraction.py       # OCR via Claude Vision API (aucune librairie OCR)
    matching.py         # Correspondance recu <-> transaction par montant+date
    beancount_link.py   # Ecrit la directive Beancount "document"
    __init__.py         # API publique du pipeline

src/compteqc/fava_ext/recus/
    __init__.py         # Extension Fava (endpoint upload + page)
    templates/RecusExtension.html  # Interface drag-and-drop

src/compteqc/cli/receipt.py        # Commandes CLI (telecharger/lister/lier)

ledger/documents/                  # Stockage physique des fichiers
    2026/02/2026-02-19.recu.pdf    # Exemple de recu stocke
```

#### Le role des recus dans le systeme

Les recus NE CREENT PAS de transactions. Ils servent de **preuve documentaire** pour des transactions qui existent deja dans le grand livre (importees du releve bancaire/carte de credit).

```
Releve bancaire (CSV) --> Categorisation IA --> Transaction au ledger
                                                      |
Recu (photo/PDF) --> Claude Vision OCR --> Correspondance montant+date
                                                      |
                                                      v
                                        Directive "document" lie les deux
                                        = piste de verification pour l'ARC
```

#### Le flux complet (CLI)

```bash
# Etape 1 : Telecharger un recu
cqc recu telecharger facture-bureau-en-gros.jpg
```

Ce qui se passe en coulisses :

```
1. VALIDATION
   Extension acceptee ? (.jpg, .jpeg, .png, .pdf)
   -> Oui : continuer
   -> Non : ValueError

2. STOCKAGE
   Image > 1568px ? -> Redimensionner (Pillow LANCZOS)
   Copier vers : ledger/documents/2026/02/2026-02-19.recu.jpg

3. EXTRACTION (Claude Vision API)
   Envoyer l'image a claude-sonnet-4-5 en mode tool_use
   Le modele retourne un JSON structure :

   {
     "fournisseur": "Bureau en Gros",
     "date": "2026-02-19",
     "sous_total": 45.00,
     "montant_tps": 2.25,       # TPS 5%
     "montant_tvq": 4.49,       # TVQ 9.975%
     "total": 51.74,
     "description": "Fournitures de bureau",
     "confiance": 0.92
   }

4. RENOMMAGE
   2026-02-19.recu.jpg  -->  2026-02-19.bureau-en-gros.jpg
   (slug du fournisseur extrait par Claude)

5. CORRESPONDANCE (matching.py)
   Cherche dans le ledger une transaction qui ressemble :

   score = 0.6 * score_montant + 0.4 * score_date

   score_montant : 1.0 si diff <= 0.05$, decroit a 0.0 a 5.00$ de diff
   score_date    : 1.0 meme jour, 0.8 a +/-1 jour, 0.0 a 7+ jours
   seuil minimum : 0.5

   Affiche les 5 meilleures correspondances :
   ┌───┬────────────┬────────────────────┬──────────┬───────┐
   │ # │ Date       │ Payee              │ Montant  │ Score │
   ├───┼────────────┼────────────────────┼──────────┼───────┤
   │ 1 │ 2026-02-19 │ Bureau en Gros     │ -51.74 $ │ 0.97* │
   │ 2 │ 2026-02-20 │ Staples            │ -49.99 $ │ 0.62  │
   └───┴────────────┴────────────────────┴──────────┴───────┘
   (* = score >= 0.8, correspondance forte)

6. LIAISON (interactif)
   L'utilisateur choisit la transaction #1
   -> Ecrit la directive dans ledger/2026/02.beancount :

   2026-02-19 document Depenses:Bureau:Fournitures "documents/2026/02/2026-02-19.bureau-en-gros.jpg"

   Maintenant Fava sait que cette depense a un document justificatif.
```

#### Commandes CLI completes

```bash
# Telecharger et traiter un recu (extraction + correspondance + liaison)
cqc recu telecharger facture.jpg

# Lister les recus deja stockes
cqc recu lister

# Lier manuellement un recu a une transaction
cqc recu lier <chemin-recu> <compte> <date>
```

#### Via l'interface Fava (web)

L'extension Fava offre un **glisser-deposer** :

1. Naviguer vers `http://localhost:5001/.../extension/RecusExtension/`
2. Glisser un fichier sur la zone de depot (ou cliquer pour parcourir)
3. Le fichier est stocke + extrait par Claude Vision
4. La table des 10 recus les plus recents se met a jour

**Limitation actuelle** : l'interface web fait seulement le stockage + extraction. L'etape de correspondance et liaison est disponible uniquement via le CLI. Pour lier un recu a une transaction apres l'avoir telecharge via Fava, utiliser :

```bash
cqc recu lier ledger/documents/2026/02/2026-02-19.bureau-en-gros.jpg Depenses:Bureau:Fournitures 2026-02-19
```

#### Pourquoi c'est important

Lors d'un controle fiscal de l'ARC ou de Revenu Quebec, chaque depense deduite doit etre justifiee par un document original. La directive `document` de Beancount cree cette piste de verification directement dans le grand livre :

```beancount
# La transaction (importee du releve bancaire)
2026-02-19 * "Bureau en Gros" "Fournitures de bureau"
  Depenses:Bureau:Fournitures   45.00 CAD
  Actifs:TPS-Payee               2.25 CAD
  Actifs:TVQ-Payee               4.49 CAD
  Passifs:CartesCredit:RBC     -51.74 CAD

# La piece justificative (liee au meme compte, meme date)
2026-02-19 document Depenses:Bureau:Fournitures "documents/2026/02/2026-02-19.bureau-en-gros.jpg"
```

Le CPA peut ainsi voir, pour chaque depense, le recu correspondant.

---

## 6. Couche 5 : Rapports et etats financiers {#6-rapports}

### Ou ca se trouve

```
src/compteqc/rapports/
    base.py                    # Classe abstraite BaseReport
    balance_verification.py    # Balance de verification (trial balance)
    bilan.py                   # Bilan (balance sheet)
    etat_resultats.py          # Etat des resultats (income statement)
    sommaire_paie.py           # Detail de la paie
    sommaire_taxes.py          # Sommaire TPS/TVQ
    sommaire_dpa.py            # Cedule d'amortissement
    sommaire_pret.py           # Pret actionnaire
    gifi_export.py             # Export GIFI pour TaxCycle
    cpa_package.py             # Orchestrateur du package ZIP
    templates/                 # Gabarits Jinja2 pour HTML/PDF
```

### Architecture des rapports

Chaque rapport suit le meme patron :

```python
class MonRapport(BaseReport):
    def extract_data(self) -> dict:
        """Extraire les donnees du ledger"""

    def csv_headers(self) -> list[str]:
        """En-tetes CSV"""

    def csv_rows(self) -> list[list]:
        """Lignes de donnees CSV"""
```

La classe `BaseReport` fournit :
- Environnement Jinja2 (charge les templates de `templates/`)
- Generateur CSV
- Generateur PDF via WeasyPrint (HTML --> CSS --> PDF)
- Methode `generate()` qui retourne `{"csv": Path, "pdf": Path}`

### Les 7 rapports

#### 1. Balance de verification

**But** : Verifier que total debits = total credits (le ledger est en equilibre)

**Donnees** : `calculer_soldes()` groupe par categorie (Actifs, Passifs, Capital, Revenus, Depenses)

**Colonnes** : Compte | GIFI | Debit | Credit

**Verification** : `equilibre = (total_debits == total_credits)`

#### 2. Bilan (balance sheet)

**But** : Photo financiere a un moment donne

**Calcul** :

```
ACTIFS (affiches positifs)
  = Somme des comptes "Actifs:*" (deja positifs dans Beancount)

PASSIFS (affiches positifs)
  = -Somme des comptes "Passifs:*" (negatifs dans Beancount, inverses)

CAPITAUX PROPRES
  = -Somme des comptes "Capital:*"
  + Resultat net de l'exercice

RESULTAT NET
  = -(Somme Revenus + Somme Depenses)
  = -(credits + debits)  --> positif si profitable
```

**Equation verifiee** : `Actifs == Passifs + Capitaux propres`

#### 3. Etat des resultats (income statement)

**But** : Performance financiere sur une periode

**Calcul** :

```
REVENUS
  = -Somme des comptes "Revenus:*" (inverses pour afficher positif)

DEPENSES
  = Somme des comptes "Depenses:*" (deja positifs)

RESULTAT NET = Revenus - Depenses
```

**Filtre optionnel** par date de debut/fin

#### 4. Sommaire de paie

**Source** : Transactions avec tag `#paie` dans le ledger

**Par periode** : Brut | Retenues detaillees | Net | Cotisations employeur detaillees

**Totaux** : Somme de toutes les periodes de l'annee

#### 5. Sommaire TPS/TVQ

**Source** : `generer_sommaires_annuels(entries, annee, frequence)`

**Par periode** (annuelle ou trimestrielle) :

| Colonne | Source |
|---------|--------|
| TPS percue | `Passifs:TPS-Percue` (inverser signe) |
| CTI (TPS payee) | `Actifs:TPS-Payee` |
| TPS nette | Percue - Payee |
| TVQ percue | `Passifs:TVQ-Percue` (inverser signe) |
| RTI (TVQ payee) | `Actifs:TVQ-Payee` |
| TVQ nette | Percue - Payee |

#### 6. Cedule DPA

**Source** : `RegistreActifs` (YAML) + `construire_pools()`

**Par classe** : FNACC ouverture | Acquisitions | Dispositions | Demi-taux | DPA reclamee | FNACC fermeture

**Sous-tableaux** : Detail des actifs par classe

#### 7. Sommaire du pret actionnaire

**Source** : `obtenir_etat_pret(entries, fin_exercice)`

**Sections** :
1. Tableau de continuite (mouvements)
2. Echeances s.15(2) avec jours restants et statut d'alerte
3. Detection de circularite (le cas echeant)

### Export GIFI

Les codes GIFI (General Index of Financial Information) sont attaches aux comptes dans `comptes.beancount` :

```beancount
2024-01-01 open Actifs:Banque:RBC:Cheques CAD
  gifi: "1001"
```

L'export genere deux fichiers CSV :
- **S100** : Bilan (schedules 100-199)
- **S125** : Etat des resultats (schedules 125-199)

Format : `CODE_GIFI | MONTANT | SCHEDULE`

---

## 7. Couche 6 : Interfaces utilisateur {#7-interfaces}

### Comment les 3 interfaces se parlent

```
                    +--------------------+
                    |  GRAND LIVRE       |
                    |  (Beancount files) |
                    +--------------------+
                      ^    ^    ^
                      |    |    |
            +---------+    |    +----------+
            |              |               |
     +------+------+  +---+----+  +-------+-------+
     |  CLI (Typer) |  |  MCP   |  | Fava (Flask)  |
     |              |  | Server |  |               |
     | compteqc ... |  | (Claude|  | localhost:5000|
     +--------------+  | tools) |  +---------------+
                       +--------+
```

Les trois interfaces utilisent les **memes modules** sous le capot. Il n'y a pas de duplication de logique.

### 7a. Serveur MCP (pour Claude)

**Fichier principal** : `src/compteqc/mcp/server.py`

**Framework** : FastMCP (transport stdio)

**AppContext** : Charge le ledger au demarrage, maintient les entries en memoire, `reload()` apres chaque mutation.

**13 outils exposes** :

| Categorie | Outil | Lecture/Ecriture |
|-----------|-------|------------------|
| Ledger | `soldes_comptes(filtre)` | Lecture |
| Ledger | `balance_verification()` | Lecture |
| Ledger | `etat_resultats(date_debut, date_fin)` | Lecture |
| Ledger | `bilan()` | Lecture |
| Quebec | `sommaire_tps_tvq(periode)` | Lecture |
| Quebec | `etat_dpa(annee)` | Lecture |
| Quebec | `etat_pret_actionnaire()` | Lecture |
| Categorisation | `proposer_categorie(payee, narration, montant)` | Lecture |
| Approbation | `lister_pending_tool()` | Lecture |
| Approbation | `approuver_lot(ids, confirmer_gros_montants)` | **Ecriture** |
| Approbation | `rejeter(id, compte_corrige, raison)` | **Ecriture** |
| Paie | `calculer_paie_tool(salaire_brut, nb_periodes)` | Lecture |
| Paie | `lancer_paie(salaire_brut, nb_periodes, offset_pret, confirmer)` | **Ecriture** |

**Garde-fous** :
- Transactions > 2 000 $ exigent `confirmer_gros_montants=True`
- Mode lecture seule disponible via variable d'environnement
- Maximum 50 resultats par requete (flag `tronque` si depasse)
- Toutes les reponses en francais

### 7b. CLI (ligne de commande)

**Framework** : Typer

**Commandes principales** :

```bash
# Importation
compteqc importer <fichier> [--compte CHEQUES|CARTE|AUTO] [--source-type corporate|personal]

# Soldes
compteqc soldes [--compte FILTRE]

# Rapports
compteqc rapport balance
compteqc rapport resultats [--debut YYYY-MM-DD] [--fin YYYY-MM-DD]
compteqc rapport bilan

# Revision
compteqc reviser liste [--obligatoire]
compteqc reviser approuver <indices>
compteqc reviser rejeter <id> [--compte-corrige COMPTE]

# Paie
compteqc paie lancer <montant> [--dry-run] [--salary-offset MONTANT]

# Echeances
compteqc echeances calendrier
compteqc echeances remises
compteqc echeances rappels

# CPA
compteqc cpa verifier --annee 2026
compteqc cpa export --annee 2026 [--sortie DOSSIER]

# Recus
compteqc recu telecharger <fichier>   # Upload + OCR + correspondance + liaison
compteqc recu lister                  # Lister les recus stockes
compteqc recu lier <recu> <compte> <date>  # Lier manuellement un recu

# Divers
compteqc revue         # Transactions non classees
compteqc retrain       # Re-entrainer le modele ML
```

### 7c. Fava (interface web)

**Framework** : Fava (interface web native pour Beancount) + extensions Flask

**8 extensions CompteQC** :

| Extension | URL dans Fava | Ce qu'elle affiche |
|-----------|---------------|-------------------|
| ThemeQC | (global) | Theme Quebec, couleurs, REPORT_INTROS, TOOLTIPS |
| Approbation | `/extension/ApprobationExtension/` | File d'attente + boutons approuver/rejeter |
| TaxesQC | `/extension/TaxesQCExtension/` | Sommaire TPS/TVQ par periode |
| PaieQC | `/extension/PaieQCExtension/` | Tableau de bord paie + cumuls YTD |
| PretActionnaire | `/extension/PretActionnaireExtension/` | Solde, mouvements, alertes s.15(2) |
| DpaQC | `/extension/DpaQCExtension/` | Cedule DPA par classe |
| Echeances | `/extension/EcheancesExtension/` | Calendrier fiscal + alertes |
| Recus | `/extension/RecusExtension/` | Glisser-deposer recus + OCR Claude Vision |

**Cycle de vie** :
1. Fava charge le ledger au demarrage
2. Chaque extension implemente `after_load_file()` : recalcule ses donnees
3. Les templates Jinja2 affichent les resultats
4. Quand l'utilisateur approuve/rejette une transaction, un `POST` Flask ecrit au ledger
5. Fava recharge le fichier --> toutes les extensions recalculent

**ThemeQCExtension.js** (le plus gros fichier JS) contient :
- `REPORT_INTROS` : 12 textes d'introduction pour chaque page de rapport
- `TOOLTIPS` : 64 info-bulles explicatives pour chaque element du tableau de bord
- `SIDEBAR_GROUPS` : Reorganisation de la barre laterale en groupes logiques
- Logique d'injection CSS pour le theme Quebec (#003DA5 bleu, blanc)

---

## 8. Couche 7 : Package CPA {#8-package-cpa}

### Le flux complet de fin d'annee

```
compteqc cpa export --annee 2026
    |
    v
[1] VERIFICATIONS DE FIN D'EXERCICE
    |  - Equation comptable : Actifs + Passifs + Capital + Revenus + Depenses = 0 ?
    |  - Pret actionnaire : solde != 0 ? (avertissement s.15(2))
    |  - Immobilisations : total negatif ? (erreur)
    |  - TPS/TVQ : concordance percue vs payee ?
    |  - Transactions non classees : combien dans Depenses:Non-Classe ?
    |  - Transactions en attente : combien avec flag "!" ?
    |
    |  Si ERREUR (equation desequilibree) --> ARRET
    |  Si AVERTISSEMENTS --> continuer avec avertissements
    |
    v
[2] GENERATION DES RAPPORTS (CSV + PDF)
    |
    +---> Balance de verification
    +---> Bilan
    +---> Etat des resultats
    +---> Sommaire de paie
    +---> Sommaire TPS/TVQ
    +---> Sommaire DPA
    +---> Sommaire pret actionnaire
    |
    v
[3] EXPORT GIFI
    |
    +---> S100 (bilan --> codes GIFI)
    +---> S125 (resultats --> codes GIFI)
    |
    v
[4] CREATION DU ZIP
    |
    cpa-package-2026.zip
    +-- rapports/
    |   +-- balance_verification.csv + .pdf
    |   +-- etat_resultats.csv + .pdf
    |   +-- bilan.csv + .pdf
    +-- annexes/
    |   +-- sommaire_paie.csv + .pdf
    |   +-- sommaire_dpa.csv + .pdf
    |   +-- sommaire_taxes.csv + .pdf
    |   +-- sommaire_pret.csv + .pdf
    +-- gifi/
        +-- gifi_s100.csv
        +-- gifi_s125.csv
```

**Objectif** : Le CPA recoit UN fichier ZIP, ouvre les PDF pour reviser, importe les CSV GIFI dans TaxCycle, et peut completer la declaration en moins d'une heure.

---

## 9. Diagramme des dependances entre modules {#9-dependances}

```
                         rates.py
                    (taux 2026: QPP, AE,
                     RQAP, FSS, impots)
                           |
              +------------+------------+
              |            |            |
         cotisations.py  impot_       impot_
         (QPP, RQAP,    federal.py   quebec.py
          AE, FSS,
          CNESST)
              |            |            |
              +-----+------+------+-----+
                    |             |
                 ytd.py       moteur.py
              (cumuls YTD    (orchestrateur
               du ledger)     de paie)
                    |             |
                    +------+------+
                           |
                      journal.py -----> BEANCOUNT LEDGER
                    (ecritures paie)         ^
                                             |
                                    +--------+--------+
                                    |        |        |
                               taxes/    dpa/    pret_actionnaire/
                              sommaire  calcul     suivi.py
                               .py      .py     + alertes.py
                                    |        |        |
                                    v        v        v
                                 RAPPORTS (sommaires)
                                         |
                                    cpa_package.py
                                         |
                                    ZIP --> CPA


     INGESTION -----> CATEGORISATION -----> PENDING -----> LEDGER
     (CSV/OFX)        (regles/ML/LLM)       (.beancount)   (mensuel)
                                                |
                                      APPROBATION (Fava/MCP/CLI)
```

### Qui depend de qui (resume)

| Module | Depend de | Utilise par |
|--------|-----------|-------------|
| `rates.py` | (aucun) | cotisations, impot_federal, impot_quebec |
| `cotisations.py` | rates | moteur (paie) |
| `impot_federal.py` | rates | moteur (paie) |
| `impot_quebec.py` | rates | moteur (paie) |
| `ytd.py` | ledger (beancount) | moteur (paie) |
| `moteur.py` (paie) | cotisations, impots, ytd, rates | journal, MCP, CLI |
| `journal.py` (paie) | moteur | ledger (ecriture) |
| `taxes/calcul.py` | rates | categorisation, rapports |
| `taxes/traitement.py` | rules YAML | calcul, sommaire |
| `taxes/sommaire.py` | calcul, ledger | rapports, MCP, Fava |
| `dpa/calcul.py` | registre, classes | rapports, MCP, Fava |
| `dpa/registre.py` | YAML (actifs) | calcul, rapports |
| `pret_actionnaire/suivi.py` | ledger | alertes, rapports, MCP |
| `pret_actionnaire/alertes.py` | suivi | echeances, rapports, Fava |
| `echeances/calendrier.py` | alertes (pret) | CLI, Fava |
| `rapports/*.py` | tous les modules ci-dessus | CPA package, CLI |
| `cpa_package.py` | rapports, gifi, verification | CLI |
| `mcp/services.py` | ledger | tous les outils MCP |
| `categorisation/pipeline.py` | moteur, ml, llm, capex | ingestion, MCP |

---

## 10. Glossaire {#10-glossaire}

| Terme | Definition |
|-------|-----------|
| **AE** | Assurance-emploi (taux Quebec different du federal) |
| **Beancount** | Logiciel de comptabilite en partie double, fichiers texte |
| **CAPEX** | Depense en immobilisation (actif, pas depense courante) |
| **CCA** | Capital Cost Allowance (terme anglais de DPA) |
| **CNESST** | Commission des normes, de l'equite, de la sante et de la securite du travail |
| **CTI** | Credit de taxe sur intrants (TPS payee recuperable) |
| **DPA** | Deduction pour amortissement (amortissement fiscal) |
| **FNACC** | Fraction non amortie du cout en capital |
| **FSS** | Fonds des services de sante (cotisation employeur Quebec) |
| **GIFI** | General Index of Financial Information (codes standard ARC) |
| **LIR** | Loi de l'impot sur le revenu (federal) |
| **MCP** | Model Context Protocol (interface IA) |
| **MGA** | Maximum des gains admissibles (QPP/RRQ) |
| **MGAP** | Maximum des gains admissibles supplementaire (QPP supp. 2) |
| **MRA** | Maximum de la remuneration assurable |
| **QPP/RRQ** | Quebec Pension Plan / Regime de rentes du Quebec |
| **RQAP** | Regime quebecois d'assurance parentale |
| **RTI** | Remboursement de taxe sur intrants (TVQ payee recuperable) |
| **s.15(2)** | Section 15(2) de la Loi de l'impot sur le revenu (pret actionnaire) |
| **TPS** | Taxe sur les produits et services (5 %, federal) |
| **TVQ** | Taxe de vente du Quebec (9,975 %) |
| **YTD** | Year-to-date (cumul depuis le debut de l'annee) |

---

> **Document genere le 2026-02-20**
> Source : Analyse complete du code de CompteQC (16 modules, 50+ fichiers Python, 7 extensions Fava)
