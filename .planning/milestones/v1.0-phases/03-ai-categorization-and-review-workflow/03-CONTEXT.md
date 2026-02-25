# Phase 3: AI Categorization and Review Workflow - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Transactions that the rule engine cannot categorize are handled by ML prediction and LLM classification with confidence scoring. All AI-categorized transactions go through a human review workflow before reaching the official ledger. The rule engine itself is Phase 1; payroll/GST/QST/CCA logic is Phase 2; MCP and web UI are Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Pipeline tiers & handoff
- Categorization runs at import time — every transaction goes through the full pipeline during import, not as a separate step
- Pipeline order: rules first, ML (smart_importer) second, LLM (Claude) third — each tier only processes what the previous couldn't handle
- Skip ML tier if untrained — during cold start, uncategorized transactions go directly from rules to LLM; smart_importer activates once sufficient corrected data accumulates
- LLM receives rich context: the transaction itself, chart of accounts with descriptions, recent similar categorized transactions, and vendor history — accuracy over token cost (volume is low)
- LLM proposes account classification only (expense/revenue account, CAPEX vs OPEX flag) — GST/QST legs are calculated deterministically by the Phase 2 tax module, never by the LLM

### Confidence & flagging
- Rule-engine results are implicitly 100% confident — no score needed, auto-posted directly
- Three-tier confidence thresholds for ML/LLM results:
  - Below 80%: mandatory human review
  - 80-95%: posted to pending queue, review optional (can sample or focus on higher-risk items)
  - Above 95%: auto-approved and posted directly, visible in audit logs for later inspection
- Tier disagreement (ML says account A, LLM says account B) forces mandatory review regardless of individual confidence scores — both suggestions shown side by side
- CAPEX detection uses amount + vendor/description patterns:
  - Configurable amount threshold (default $500)
  - Known vendor patterns (Apple, Dell, B&H, etc.) flag potential assets even below threshold
  - Always overridable (expense vs CAPEX)
  - Suggests CCA class when flagging

### Approval workflow
- Batch review mode: table/list of pending transactions, select multiple to approve, reject, or recategorize
- Each row shows: proposed account + confidence score, source tier (rule/ml/llm), vendor history (last categorizations), CAPEX/flag indicators
- Approved transactions move directly to monthly ledger files (e.g. 2026-01.beancount), no intermediate staging
- Corrections accept optional notes (prompted but skippable) — useful for later analysis

### Claude's Discretion
- Pending queue filtering approach (by vendor, confidence range, date, etc.)
- LLM drift monitoring strategy (store prompt/response pairs, alerting approach)
- Exact batch review table layout and column ordering
- How to surface the 80-95% "optional review" items distinctly from <80% mandatory items

### Feedback & learning
- Auto-generate rules silently after 2 identical corrections (same vendor → same account twice = new rule created automatically)
- Smart_importer ML retraining is manual only — user runs `cqc retrain` when they decide; no auto-retrain
- LLM prompt/response pairs stored for debugging and drift detection

</decisions>

<specifics>
## Specific Ideas

- "Tax math must be exact and reproducible; the LLM is for semantic classification, not for computing the tax split"
- "Conflicts between tiers are exactly the kind of cases where I don't want silent automation"
- Cold-start awareness: at the beginning most things will be <95% confidence, progressively less manual review as the system learns
- User wants to see both ML and LLM suggestions side-by-side when they disagree

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-ai-categorization-and-review-workflow*
*Context gathered: 2026-02-19*
