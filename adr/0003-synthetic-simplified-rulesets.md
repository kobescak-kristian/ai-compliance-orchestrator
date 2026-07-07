# ADR 0003: Synthetic, Simplified Rule Sets

## Status
Accepted (2026-07-07, Phase 0)

## Date: 2026-07-07

## Context
The system's stated capability is multi-jurisdiction compliance checking
(MGA, UKGC, German GlüStV-style themes: bonus-term transparency,
responsible-gambling messaging, prohibited claims, geo eligibility). Real
regulatory text is long, jurisdiction-specific, subject to legal
interpretation, and changes independently of this project's timebox. A
domain-literate reviewer (compliance officer, legal counsel) would
reasonably ask whether the rule sets are the real thing, and an
unsupportable claim of legal accuracy would be the fastest way to lose
credibility with exactly the reader this project targets.

## Decision
All three jurisdiction rule sets are synthetic and deliberately
simplified: modeled on publicly known regulatory *themes*, not
transcribed or derived from real regulatory text, and not reviewed by
counsel. The README states this explicitly and unambiguously wherever
the system's output is shown. The project demonstrates the orchestration
architecture for compliance surveillance; it does not claim, and must
never be represented as, legal accuracy or a production compliance tool.

## Consequences
- The eval gate (precision/recall thresholds, BLUEPRINT §7) measures the
  system's ability to apply *a* rule set correctly and consistently — not
  the correctness of real-world regulatory content. This distinction must
  be stated wherever gate results are reported.
- Removes any need for legal review, licensing, or jurisdiction-expert
  sign-off before Phase 1 dataset authoring — the rule sets are authored
  the same way the eval dataset is (synthetic, ground-truth first,
  Kristian-approved before freeze).
- Trade-off: the system's demonstrated precision/recall says nothing
  about how it would perform against real regulatory text, and this must
  not be implied in any external-facing material (README, demo,
  positioning).
- BLUEPRINT §12 (out of scope) is the forward enforcement of this ADR:
  real regulatory text ingestion and legal-accuracy claims of any kind
  are explicitly excluded from this build.
