# Alētheia Array™ EVM unit: what exists, what it does, what it does not

| Piece | File | Status |
|---|---|---|
| Unit runtime (stdlib Python) | `unit/aletheia_unit.py` | Implemented; 15 tests with a mock chain; run live on 6 mainnets (see `BENCH-2026-11-08.md`) |
| Binder + allocation ledger | `factory/bind_units.py` | Implemented; 6 tests. One allocation per DeviceID enforced by a SQLite PRIMARY KEY |
| Live chain check (Gate-4-lite) | `scripts/gate4_lite_evm.py` | Implemented; 10 tests; run live |
| Register verifier | `scripts/verify_register.py` | Implemented; 10 tests |

## Flow
1. `scripts/gate4_lite_evm.py catalogue.csv --out results.csv` checks EVM chains live and records endpoint, height and time.
2. `factory/bind_units.py --device <DeviceID> --buyer-ref <order id> --catalogue … --gate4 results.csv --ledger allocations.sqlite --out packages [--chains-file chains.json]` builds `packages/<DeviceID>/` (runtime, `unit-config.json`, `README.txt`, `SHA256SUMS`) and records the allocation. It refuses non-mainnet, non-EVM, non-PASS (PARTIAL only with `--allow-partial`) and already-allocated devices.
3. The buyer runs `python3 aletheia_unit.py --config unit-config.json`; `--verify records.jsonl` re-checks the record chain.

## Unit behaviour
- Uses an endpoint only after `eth_chainId` equals the configured chain ID; a wrong-network endpoint is banned; if none remain the unit exits 1.
- Files one JSON record per block at least `finality_depth` (default 12) behind the head, with `prev_record_hash` / `record_hash` (SHA-256).
- Halts (exit 1) on a parent-hash break between consecutive filed blocks; files nothing further.
- Restart-safe: atomic state file; recovers from a crash between append and state write; refuses on state/output disagreement.
- Optional `watch` addresses: transactions from or to them are recorded in `matches`.

## NOT implemented (do not claim)
- AcerbE™ signatures (needs the AcerbE service; records carry a hash chain only, which proves tampering after the fact, not who wrote them).
- Non-EVM families (57 of the 1,695 register rows): ROADMAP.
- Websocket subscriptions; pre-start history backfill beyond `start_block`.
- Protection from a dishonest RPC provider: each block comes from one endpoint.
- Full Gate-4 explorer comparison: Gate-4-lite compares two independent public RPCs instead.
- LexForge™ per-order documents and RaPaX™ delivery: not part of this repo.
