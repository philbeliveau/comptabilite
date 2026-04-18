# TPS/TVQ filing note - 2026-03-03 to 2026-03-31

This note captures the facts and working treatment discussed on 2026-04-18 for
the first corporate TPS/TVQ reporting period of Conseil et Solution Enact Inc.
It is bookkeeping support, not tax/legal advice. CPA review remains final.

## Corporate identifiers

- Corporation: Conseil et Solution Enact Inc.
- NEQ: 1181862674
- Revenu Quebec identification number: 1233599588
- TVQ file: 1233599588 TQ0001
- TPS/GST account: 798484770 RT0001

## Government letters received

Source folder:

- `/Users/philippebeliveau/Desktop/Notebook/comptabilite/docs/Gouvernement-poste/IMG_2040.jpg`
- `/Users/philippebeliveau/Desktop/Notebook/comptabilite/docs/Gouvernement-poste/IMG_2041 2.jpg`

Interpretation:

- `IMG_2040.jpg` is addressed to Philippe Beliveau personally and should not be
  mixed into the corporation ledger without CPA confirmation.
- `IMG_2041 2.jpg` is addressed to Conseil et Solution Enact Inc. and is the
  relevant corporate letter.
- The corporate letter shows the TVQ and TPS/GST identifiers above.
- The first TVQ period shown by the corporate letter is 2026-03-03 to
  2026-03-31, due 2026-04-30.
- The letter indicated that TPS/GST information might not yet be available or
  matched with the TVQ file. This matched the portal behavior: the first TVQ
  return was available, while TPS/GST had to be filed separately.

## Original TVQ filing mistake

Original filed receipt:

- `/Users/philippebeliveau/Library/Mobile Documents/com~apple~CloudDocs/_Bureau_/Enact Conseils et Solutions Inc./cliqseq-tax-cheque-revenueqc/Declaration-tps-tvq/2026/march/Mauvais-declaration.pdf`
- Permanent repo copy: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/03/tps-tvq-filing/2026-03-tvq-declaration-initiale-erronee.pdf`

Filed on:

- 2026-04-18 at 08:52:57 HAE
- Reference number: 010700157015486
- Filing type: Declaration de la TVQ
- Period: 2026-03-03 to 2026-03-31
- Payment code: SC012 33599 58000 14004

Amounts originally filed for TVQ:

| Line | Description | Amount |
| --- | --- | ---: |
| 201 | Fournitures | 2,210.11 |
| 205 | TVQ exigible et redressements | 220.46 |
| 208 | RTI et redressements | 3.27 |
| 213 | TVQ a verser ou remboursement | 217.19 |
| Solde a verser | Total TVQ due | 217.19 |

## Ledger transactions included in original filing

Revenue and tax collected:

- BOI reimbursement, 2026-03-10:
  - Revenue: 210.11
  - TPS collected: 10.51
  - TVQ collected: 20.96
- CRL payment, 2026-03-11:
  - Revenue: 2,000.00
  - TPS collected: 100.00
  - TVQ collected: 199.50

Input tax credits/refunds included:

- Fizz internet allocation, 2026-03-04:
  - CTI/TPS: 1.08
  - RTI/TVQ: 2.14
- Fizz internet allocation, 2026-03-29:
  - CTI/TPS: 0.56
  - RTI/TVQ: 1.13

Original totals without Procom:

- Supplies: 2,210.11
- TPS collected: 110.51
- TVQ collected: 220.46
- CTI/TPS: 1.64
- RTI/TVQ: 3.27
- TPS payable: 108.87
- TVQ payable: 217.19
- Combined payable: 326.06

## Procom transaction omitted from the original TVQ filing

Support:

- `/Users/philippebeliveau/Downloads/Payment-PQI160679.csv`
- Procom transaction: PQI503215-P-1
- Payment number: PQI160679
- Worker order: 71254.1
- Timesheet: 3031182
- Client: Industrielle Alliance Assurance et Services Financiers
- Services period: 2026-03-09 to 2026-03-31
- Date de l'operation shown on Procom paystub: 2026-03-31
- Payment date/release date: 2026-04-10

Amounts:

- Supplies/revenue: 9,680.00
- TPS/GST: 484.00
- TVQ/QST: 965.58
- Total: 11,129.58

Working conclusion:

- Based on the Procom paystub showing `Date de l'operation: 31 mars 2026`, the
  Procom transaction belongs in the 2026-03-03 to 2026-03-31 TPS/TVQ return even
  though cash was received on 2026-04-10.

## Corrected TVQ return

Corrected TVQ amounts including Procom:

| Line | Description | Declared | Revised |
| --- | --- | ---: | ---: |
| 201 | Fournitures | 2,210.11 | 11,890.11 |
| 205 | TVQ exigible et redressements | 220.46 | 1,186.04 |
| 208 | RTI et redressements | 3.27 | 3.27 |
| 210 | Acomptes provisionnels de TVQ | 0.00 | 0.00 |
| 211 | Autres remboursements de TVQ | 0.00 | 0.00 |
| 213 | TVQ a verser ou remboursement | 217.19 | 1,182.77 |
| 214 | Immeuble/unites emission | 0.00 | 0.00 |
| Remboursement demande |  | 0.00 | 0.00 |
| Solde a verser |  | 217.19 | 1,182.77 |

Additional TVQ to remit if the original 217.19 has already been paid:

- 965.58

TVQ amendment form:

- FPZ-2500, because the original filing was a TVQ return without annexes.
- Fill only the TVQ side unless there is a separate already-filed TPS/GST return
  requiring correction.
- Send by mail unless Mon dossier accepts the document as a voluntary upload.
- Permanent repo copy: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/03/tps-tvq-filing/2026-03-tvq-modification-fpz-2500.pdf`
- Official mail address used/preferred for Montreal:

```text
Revenu Quebec
C. P. 3000, succursale Place-Desjardins
Montreal (Quebec) H5B 1A4
```

Short justification text used:

```text
Correction de la declaration de TVQ 2026-03-03 au 2026-03-31. La declaration
initiale a omis la transaction Procom PQI503215-P-1 / PQI160679, dont la date de
l'operation est le 31 mars 2026. Ajout de fournitures de 9 680,00 $ et de TVQ
exigible de 965,58 $. RTI inchanges. TVQ nette revisee : 1 182,77 $ au lieu de
217,19 $.
```

TVQ payment:

- Payee at RBC: REVENU QUEBEC CODE DE PAIEMENT
- Payment code: SC012335995800014004
- Amount if nothing has been paid: 1,182.77
- Amount if original TVQ 217.19 was already paid: 965.58
- Permanent repo payment proof: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/03/tps-tvq-filing/2026-03-tvq-payment-rbc.pdf`

## TPS/GST filing

Submitted TPS/GST receipt:

- `/Users/philippebeliveau/Desktop/TPS-Declaration.pdf`
- Permanent repo copy: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/03/tps-tvq-filing/2026-03-tps-declaration.pdf`

Filed on:

- 2026-04-18 at 09:50:20 HAE
- Reference number: 010700157018507
- Filing type: Declaration de la TPS/TVH
- Period: 2026-03-03 to 2026-03-31
- Payment code: SC712 33599 58000 14900

Correct TPS/GST amounts filed:

| Line | Description | Amount |
| --- | --- | ---: |
| 90 | Taxable supplies in Canada | 11,890.11 |
| 91 | Exempt/zero-rated exports/other | 0.00 |
| 101 | Fournitures | 11,890.11 |
| 102 | Supplies by associates | 0.00 |
| 105 | TPS/TVH exigible et redressements | 594.51 |
| 108 | CTI et redressements | 1.64 |
| 109 | TPS/TVH nette | 592.87 |
| 110 | TPS/TVH payee/acompte | 0.00 |
| 111 | Remboursements | 0.00 |
| 112 | Autres credits | 0.00 |
| 114 | Immeuble/unites emission | 0.00 |
| 115 | Fournitures importees | 0.00 |
| Total | TPS/TVH a remettre | 592.87 |

TPS/GST payment:

- Payee at RBC: REVENU QUEBEC CODE DE PAIEMENT
- Payment code: SC712335995800014900
- Amount: 592.87
- Permanent repo payment proof: `/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/03/tps-tvq-filing/2026-03-tps-payment-rbc.pdf`

## Permanent proof folder

All March 2026 first-period TPS/TVQ proof files were moved from
`/Users/philippebeliveau/Desktop/Notebook/comptabilite/march` to:

```text
/Users/philippebeliveau/Desktop/Notebook/comptabilite/ledger/documents/2026/03/tps-tvq-filing/
```

Files:

- `2026-03-tps-declaration.pdf`
- `2026-03-tps-payment-rbc.pdf`
- `2026-03-tvq-declaration-initiale-erronee.pdf`
- `2026-03-tvq-modification-fpz-2500.pdf`
- `2026-03-tvq-payment-rbc.pdf`

## Combined cash impact

Correct total for the period after including Procom:

- TPS/GST payable: 592.87
- TVQ payable: 1,182.77
- Combined payable: 1,775.64

If original TVQ of 217.19 was already paid before the amendment:

- Remaining TPS/GST: 592.87
- Remaining additional TVQ: 965.58
- Remaining combined payment: 1,558.45

## Follow-up bookkeeping

The ledger currently records the Procom payment as a 2026-04-10 bank receipt in
`ledger/2026/04.beancount`. For tax-report consistency, consider adjusting the
ledger to recognize Procom revenue and collected TPS/TVQ on 2026-03-31, with
the 2026-04-10 bank deposit clearing accounts receivable.
