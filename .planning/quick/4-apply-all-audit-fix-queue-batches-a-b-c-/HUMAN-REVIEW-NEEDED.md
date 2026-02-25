# Human Review Needed -- Audit Fix Queue Items D2-D6

These items from the audit fix queue require human judgment and cannot be applied mechanically.

## D2: Amazon $31.68 purchase (CSV line 115)
- **Transaction:** 2026-01-28 AMZN Mktp CA*YC8609TW3 -$31.68
- **Current classification:** Depenses:Bureau:Abonnements-Logiciels
- **Action needed:** Determine what was purchased. If personal item, reclassify to Passifs:Pret-Actionnaire. If office supply/equipment, reclassify to appropriate expense account.

## D3: 7 restaurant/bar transactions
- **Transactions:** Stash Cafe ($87.74), Le Phillips ($31.91), LS Philemon Bar ($42.50), Pasta Bella ($4.25), LS Bar Caffettiera ($10.48), McKibbin's ($10.48), LS Lord William Pub ($12.50)
- **Current classification:** Depenses:Repas-Representation
- **Action needed:** Document business purpose for each (client meeting, team lunch, etc.). Meals without business purpose should be reclassified to Passifs:Pret-Actionnaire. CRA requires documentation of business purpose, attendees, and business discussed for meals and entertainment deductions.

## D4: Belair insurance -- confirm type
- **Transactions:** 3 sets of Belair payments ($38.69 + $89.09 each period)
- **Current classification:** Mix of Depenses:Assurances:Autres and Depenses:Vehicule:Assurance
- **Action needed:** Confirm whether each Belair payment is auto insurance (Depenses:Vehicule:Assurance) or home insurance (Depenses:Assurances:Autres or Passifs:Pret-Actionnaire if personal). Apply consistent classification.

## D5: Fizz telecom -- personal vs business
- **Transactions:** 2 Fizz payments ($25.93 and $49.44)
- **Current classification:** Depenses:Bureau:Internet-Telecom
- **Action needed:** Determine personal vs business usage percentage. If personal phone, the full amount should go to Passifs:Pret-Actionnaire. If mixed use, document the business percentage and split accordingly.

## D6: Payroll journal entries
- **Transactions:** 5 DEPOT DE PAIE entries (various amounts)
- **Current classification:** Passifs:Salaires-A-Payer (net deposit)
- **Action needed:** Create full payroll journal entries for each pay period with:
  - Gross salary (Depenses:Salaires:Brut)
  - Employee deductions (QPP, EI, RQAP, federal tax, Quebec tax)
  - Employer contributions (QPP, EI, RQAP, FSS, CNESST, normes du travail)
  - Net pay (Passifs:Salaires-A-Payer -> Actifs:Banque:RBC:Cheques)
  - Requires actual pay stub details for each period.
