# Alētheia Array™ — Data Ingestion Devices

**Archer Chain Analytics · Register of Record**

![Audit](https://img.shields.io/badge/AUDIT-VERIFIED%202026--11--07-dcae3f?style=flat-square)
![Register](https://img.shields.io/badge/REGISTER-1%2C694%20DEVICES-161e29?style=flat-square)
![Mainnet](https://img.shields.io/badge/MAINNET-1%2C597-161e29?style=flat-square)
![Families](https://img.shields.io/badge/FAMILIES-23-161e29?style=flat-square)

This repository is the authoritative register for the Alētheia Array™ multi-chain data-ingestion device catalogue. The figures published here were audited on **2026-11-07** against the source manifests and supersede every count published anywhere else. If a document, page, or repository states a different figure for this register, this repository governs.

**Correction, 2026-11-11:** one register row (DeviceID `evm__`, a blank stub with no chain name and no chain identity in its config) was struck from the manifests and catalogue on the owner's word. Corrected figures: **1,694 total — 1,597 mainnet, 93 testnet, 4 under review; 1,585 distinct named mainnet networks.** See the correction section in AUDIT-2026-11-07.md.

**Live product page:** https://archerchainanalytics.com/aletheia-array.html

---

## Verified figures

| Measure | Count |
|---|---|
| Total device configurations | **1,694** |
| Mainnet listener configurations | **1,597** |
| Testnet | **93** |
| Under review (canary / beta) | **4** |
| Chain families | **23** |
| Distinct mainnet networks | 1,585 |
| Distinct mainnet chain IDs | 1,569 |
| Duplicate DeviceIDs | 0 |

The headline figure — **1,597** — counts mainnet listener *configurations*: twelve networks are registered under two families each (each registration carries its own DeviceID and configuration), which is why configurations (1,597) exceed distinct networks (1,585).

## Under review

| Chain | Chain ID | Family |
|---|---|---|
| BEVM Canary | 1501 | evm |
| Opulent-X BETA | 41500 | evm |
| Songbird Canary-Network | 19 | evm |
| Vulture EVM Beta | 3102 | evm |

## Family breakdown

| Family | Devices | | Family | Devices |
|---|---|---|---|---|
| evm | 1638 | | aptos | 1 |
| cosmos_sdk | 12 | | bitcoin | 1 |
| utxo | 8 | | cardano | 1 |
| substrate | 6 | | cosmos | 1 |
| solana_svm | 4 | | elrond_multiversx | 1 |
| directed_acyclic_graph | 3 | | near | 1 |
| move_vm | 3 | | near_ecosystem | 1 |
| algorand | 2 | | starknet_ecosystem | 1 |
| algorand_ecosystem | 2 | | sui | 1 |
| solana | 2 | | ton_ecosystem | 1 |
| xrpl | 2 | | tron | 1 |
| xrpl_ecosystem | 2 | | | |

## Repository contents

| File | Purpose |
|---|---|
| `AUDIT-2026-11-07.md` | The full audit: sources, method, results, and limits |
| `catalogue-2026-11-07.csv` | The audited catalogue — all 1,694 devices (DeviceID, family, chain, chain ID, network, status) |
| `identity_manifest.csv` | Register export (1,694 rows) |
| `validate_manifest.py` | Manifest validation script |
| `aletheia_production_factory.py` | Production factory (device configuration generation) |
| `ARCHITECTURE.md` | System architecture notes |

## How to verify this register

1. Open `catalogue-2026-11-07.csv` — it is generated from the audited manifests.
2. Count rows by the `Network` column: mainnet 1,597 · testnet 93 · review 4 · total 1,694.
3. Confirm there are no duplicate `DeviceID` values.
4. Cross-check against `identity_manifest.csv` (1,694 rows).

Anyone who performs this count lands on the same figures. That reproducibility is the authority.

## Commercial status

| SKU | Offering | Price (USD) | Status |
|---|---|---|---|
| ACA-ALETHEIA-UNIT | Mainnet listener — individual unit | $2,500 | Ready to list |
| ACA-ALETHEIA-PACK5 | 5-unit deployment pack | $9,997 | Ready to list |

Bound and live-benched at audit date: **UNIT-001** (Ethereum Mainnet) and **SET-001** (BSC, Polygon, Arbitrum One, OP Mainnet, Avalanche C-Chain), plus **UNIT-007** (Solana Mainnet Beta, no SKU adopted). All remaining configurations bind per-allocation on sale; the allocation ledger enforces one allocation per DeviceID, ever.

## Document control

- **Version:** 1.0 — audit of 2026-11-07
- **Auditor:** Okwaho, foreperson, on the order of Neil Scott Archer
- **Sources:** `manifest_with_network_2_mkzx.csv` (SHA-256 01621f25c0523c25…) and `aletheia_master_manifest_FINAL.csv` (SHA-256 c4956547197ea439…) — full hashes in `AUDIT-2026-11-07.md`
- **Change policy:** register figures change only by re-audit against the source manifests, recorded as a new dated audit. No other edit may restate them.

## Limits

This audit verifies the register. It is not a live probe of 1,694 networks. The manifest's Explorer and PublicRPC columns are empty by design — endpoints resolve at binding time through the factory's failover logic. Per-device live status is established at binding and bench, per allocation.
