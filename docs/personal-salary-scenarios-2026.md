# 2026 Personal Salary Scenarios

Date: 2026-04-05

## Purpose

Estimate a few `2026` salary scenarios for personal planning, given:

- Quebec resident
- Corporation owner-operator
- Target compensation considered as `employment salary`
- Condo purchase goal in `2027`
- Max `FHSA` contribution assumed: `8,000 CAD`
- Max new `TFSA` contribution assumed: `7,000 CAD`

This note is for planning only. It is not tax, legal, or mortgage advice.

## Important Notes

- `TFSA` contributions do not reduce taxable income.
- `FHSA` contributions do reduce taxable income.
- `RRQ/QPP`, `RQAP`, and `EI` are based on salary, not on the FHSA deduction.
- These numbers are estimates using the repo's `2026` Quebec payroll logic and tax tables.
- Actual source deductions can differ from final tax owed depending on payroll setup, TD1/TP-1015 forms, and whether FHSA is reflected at source.
- Mortgage underwriting varies by lender. In practice, clean T4 income usually matters more than shaving a few thousand dollars of RRQ.

## Assumptions Used

- Filing profile: simple estimate, no spouse-specific adjustments modeled
- No other deductions or credits modeled besides the `8,000 CAD` FHSA deduction
- No RRSP deduction modeled
- Salary is annual gross salary
- Tax bracket shown is the marginal bracket after the FHSA deduction

## Scenario Table

| Annual salary | Taxable income after FHSA | Federal bracket | Quebec bracket | Federal income tax | Quebec income tax | Total income tax | RRQ/QPP | RQAP | EI | Total employee deductions | Net cash after payroll deductions | Net cash after FHSA + TFSA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `60,000` | `52,000` | `14.0%` | `14.0%` | `3,622.06` | `3,959.80` | `7,581.86` | `3,594.50` | `257.92` | `780.00` | `12,214.28` | `47,785.72` | `32,785.72` |
| `85,000` | `77,000` | `20.5%` | `19.0%` | `7,391.54` | `8,305.96` | `15,697.50` | `4,930.12` | `365.56` | `895.70` | `21,888.88` | `63,111.12` | `48,111.12` |
| `100,000` | `92,000` | `20.5%` | `19.0%` | `9,951.50` | `11,146.72` | `21,098.22` | `4,930.12` | `430.04` | `895.70` | `27,354.08` | `72,645.92` | `57,645.92` |
| `120,000` | `112,000` | `20.5%` | `24.0%` | `13,369.46` | `18,033.86` | `31,403.32` | `4,930.12` | `442.78` | `895.70` | `37,671.92` | `82,328.08` | `67,328.08` |
| `150,000` | `142,000` | `26.0%` | `25.75%` | `19,651.32` | `25,379.38` | `45,030.70` | `4,930.12` | `442.78` | `895.70` | `51,299.30` | `98,700.70` | `83,700.70` |
| `200,200` | `192,200` | `29.0%` | `25.75%` | `30,818.58` | `38,305.80` | `69,124.38` | `4,930.12` | `442.78` | `895.70` | `75,392.98` | `124,807.02` | `109,807.02` |

## What Changes And What Does Not

### Items that stop growing fairly quickly

- `RRQ/QPP` is effectively maxed by about `85,000` of salary in `2026`
- `EI` is already maxed by `85,000`
- `RQAP` is nearly maxed by `100,000` and fully maxed shortly after

This means that moving from `100,000` to `150,000` does not add much more payroll contribution cost. Most of the extra drag is income tax.

### Items that continue scaling

- Federal and Quebec income tax continue rising meaningfully
- Cash available personally rises too, but with lower after-tax efficiency
- Higher salary also means less retained capital left inside the corporation

## Reflection On The Main Scenarios

### `85,000`

Pros:

- You already max RRQ/QPP
- You already max EI
- Stronger personal income story than a low salary
- More tax-efficient than `100,000+`

Cons:

- Less personal cash flow than `100,000`
- Slightly tighter if you want to fund down payment, closing costs, FHSA, and TFSA comfortably from salary

### `100,000`

Pros:

- Likely the cleanest all-around balance for a `2027` condo goal
- Strong T4 income for lender conversations
- RRQ/QPP is already maxed, so you are not paying materially more pension contributions than at `85,000`
- Leaves meaningful room to retain corporate cash instead of paying out the full earnings

Cons:

- More income tax than `85,000`
- Still may be more salary than strictly necessary if the condo budget is modest

### `120,000`

Pros:

- More personal cash flow
- Stronger personal income profile for mortgage qualification

Cons:

- Quebec marginal rate steps up to `24.0%`
- Less compelling unless you know you need more personal cash outside the corporation

### `150,000+`

Pros:

- Maximum personal liquidity

Cons:

- You are now well into less efficient after-tax territory
- Much less reason to do this if you do not need the money personally before buying

## My Practical Lean

If the condo purchase in `2027` is real, the most defensible salary range is probably:

- `85,000` to `100,000`

If I had to pick one default planning number:

- `100,000`

Why:

- It gives you a clean, mortgage-friendly salary
- It already maxes RRQ/QPP, so there is no extra pension contribution penalty versus going much higher
- It still lets the corporation retain a meaningful amount of profit
- After payroll deductions, you still have about `72,645.92`
- After also funding `FHSA` and `TFSA`, you still have about `57,645.92` of net personal cash flow before living expenses

If you want to be slightly more tax-efficient and still look serious for a lender:

- `85,000` is the lower end I would consider

## Next Questions To Pressure-Test

- What condo price range are you targeting?
- How much down payment do you want available by spring/summer `2027`?
- How much of your current cash is already personally available versus trapped in the corporation?
- Do you expect a lender to focus mainly on T4 salary, or will they also underwrite corporate/dividend income well?
- Are you planning to use `RRSP + HBP`, or mostly `FHSA + cash`?

## Related Repo Context

The estimates above align with the payroll rates and Quebec payroll engine in:

- `src/compteqc/quebec/rates.py`
- `src/compteqc/quebec/paie/impot_federal.py`
- `src/compteqc/quebec/paie/impot_quebec.py`
- `src/compteqc/quebec/paie/cotisations.py`

