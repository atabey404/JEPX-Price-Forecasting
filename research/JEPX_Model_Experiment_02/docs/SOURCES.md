# Official sources and interpretation

- Price snapshot: https://www.jepx.jp/_download.php — POST form dir=spot_summary, file=spot_summary_2026.csv. Exact retained bytes and retrieval time: new_price_receipt.json.
- Market rules index: https://www.jepx.jp/electricpower/outline/ . Downloaded trading rules dated 2026-08-31 state the auction deadline is 10:00 JST on the preceding day. The retained source-document hashes identify the copies inspected.
- Official price-format document: https://www.jepx.jp/electricpower/market-data/spot/pdf/kakaku_kannoudo.pdf . Its system-price schema lists 0.01–999.00 JPY/kWh. Experiment 02 uses 0.01 as a research output/data-contract safeguard, consistent with all retained area observations. This older schema alone does not establish a complete current legal validation rule for area prices or orders. No upper clipping is applied.
- The full external rulebooks are not bundled. The URLs and inspection hashes are retained for provenance.

These materials support source interpretation. They do not demonstrate predictive performance.
