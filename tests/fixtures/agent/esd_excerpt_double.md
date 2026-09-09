<!-- TEST DOUBLE: this file is a hand-authored stand-in for Parallel Extract
output. It illustrates the SHAPE of the New York ESD quarterly Film Tax
Credit report's per-production "Credits Issued" chart. Every production
name and figure below is illustrative only, is NOT real government data,
and must NEVER be presented as a validation result (D-87, T-05-10). It
exists only to drive tests/test_agent_job1_offline.py's offline
extract-price-classify loop with zero network access and no API keys. -->

# ESD Film Production Tax Credit Program — Credits Issued (TEST DOUBLE, Q9 2099)

| Production | Qualified Costs | Credit Issued | Diversity Credit |
|---|---|---|---|
| Test Production Alpha | $10,000,000 | $2,500,000 | — |
| Test Production Beta | $20,000,000 | $5,003,000 | $3,000 |
| Test Production Gamma | $8,000,000 | $2,100,000 | — |
| Test Production Delta | 3.964.760,00 | 991.190,00 | — |
| Test Production Epsilon | n/a | $1,000,000 | — |

Row-by-row, this double is engineered to exercise every taxonomy bucket
and every numbers.py convention in one pass:

- **Alpha**: a clean exact match ($10,000,000 x 25% = $2,500,000 exactly).
- **Beta**: disclosed exceeds computed by exactly its own Diversity Credit
  column ($5,000,000 computed + $3,000 diversity = $5,003,000 disclosed) —
  `explained_variance` via the `diversity-credit-column` rule.
- **Gamma**: disclosed ($2,100,000) differs from computed ($2,000,000) by
  $100,000 with no diversity credit column to explain it — genuinely
  `unexplained`.
- **Delta**: European-convention figures (`.` grouping, `,` decimal) that
  still exact-match once parsed ($3,964,760.00 x 25% = $991,190.00).
- **Epsilon**: an unparseable qualified-spend figure (`n/a`) — an
  `ExtractionFailure`, never a fabricated or dropped row.
