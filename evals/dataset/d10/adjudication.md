# D10 adjudication

Step 6 of `evals/v2/SCENARIO_SPEC.md` §6: the human adjudicator rules on every cell
where the draft key and the blind labels disagree. D10 is public
development data; results on it are reported only and never gate.

## Blind labeling

- Labeler: GPT-6 (a different model family from the Claude authors),
  run with the blind packet only: the 10 pages, the 24
  signed v1.1 rule texts, the applicability semantics and an empty
  112-cell template. It never saw the briefs or the draft key.
- Returned file: kept privately outside Git; SHA-256
  `8adf07b8aaedc9c51d0f10bba9812fbad1e00c294a043a9e9c063ea2209446e8`.
  Valid: 112 cells, every verdict and reason filled in, no missing,
  duplicate or extra page or rule IDs, template order unchanged. Pages
  and rule texts unchanged since the packet was built.
- Agreement with the draft key (second pass, commit `9a9b7b0`), before
  any ruling: **110 of 112 cells (98.2%)**; 2 disagreements. The
  labeler agreed with all five draft cells marked UNSURE and with all
  16 required coverage cells.

## Rulings (2026-11-04)

| Cell | Draft | Blind label | Ruling |
|---|---|---|---|
| d03 GBR-PC-02 | COMPLIANT | NOT_APPLICABLE: "No gambling offer is presented for urgency-pressure rules." | NOT_APPLICABLE |
| d09 GBR-PC-02 | COMPLIANT | NOT_APPLICABLE: "No gambling promotional offer is presented." | NOT_APPLICABLE |

Reason (both cells): neither page presents a gambling offer governed by
GBR-PC-02. Under the written applicability semantics, absence of
governed content means NOT_APPLICABLE.

Neither cell is a page's primary decision or a required coverage cell.
`evals/dataset/d10/key.yaml` is final with these two rulings; no other
cell changed.
