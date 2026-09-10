# data_analysis/ — Phase 10 (primary deliverable)

Dual-track (pandas + DuckDB) read-out of the SwiftBite Delivery **zone-hour incentive
experiment**. Unit of randomisation = the **zone-day** (~840, 420/arm, 12 zones), so
inference runs three ways — cluster-robust (by zone) SEs, randomization inference, and a
wild-cluster bootstrap — and every headline number is reported on all three.

- Orientation & method: [`00_START_HERE.md`](00_START_HERE.md)
- Run everything + confirm SQL/Python parity: `python parity/run_all.py`
- Standalone SQL track: `sql/*.sql` (`duckdb -c ".read data_analysis/sql/_prelude.sql"` first)
- Findings (one per analysis): [`findings/`](findings/)
- **Deliverables:** [`deliverables/board_summary.pdf`](deliverables/board_summary.pdf) /
  `.html` (decision-first) and [`deliverables/deep_dive.pdf`](deliverables/deep_dive.pdf) /
  `.html` (the exhaustive record), built by
  [`deliverables/build_deliverables.py`](deliverables/build_deliverables.py).

## Result in one line

The zone-hour incentive **works on liquidity** — fulfillment **+1.87 pp** (cluster CI
[+1.27, +2.46]; randomization-inference p = 3×10⁻⁴; wild-cluster bootstrap agrees), ETA
p90 **−6 min**, no-courier cancels **−0.36 pp**, concentrated in the supply-short and
balanced zones (interaction Wald p = 0.004), with only a small (~17%, not significant)
neighbour-zone drag — **but it does not pay for itself**: a flat R$ 4.5 bonus on every
treated-block delivery buys ~127 incremental orders at **~R$ 281 each** against a ~R$ 10
contribution margin. **Don't ship the flat bonus; restructure it to reward incremental
supply and cap it to the short + balanced zones.**
