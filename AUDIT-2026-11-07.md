# Alētheia Array™ — Data Ingestion Devices: AUDITED CATALOGUE
**Audit date:** 2026-11-07 · **Auditor:** Okwaho (foreperson), on the order of Neil Scott Archer
**Status of this document:** the audited register of record. Figures here supersede any count published elsewhere.

## Sources audited (the register itself)
| File | Rows | SHA-256 |
|---|---|---|
| manifests/manifest_with_network_2_mkzx.csv | 1695 | 01621f25c0523c25fe1134421cbf36856c248a32efcf548170098ace7c20b304 |
| manifests/aletheia_master_manifest_FINAL.csv | 1695 | c4956547197ea439c272f0af14622a837951e30876a464101e9dc1433b12f0db |

Method: both files parsed in full; every row counted; DeviceID sets compared exactly; splits taken from the manifest's own Network column; chain names and chain IDs (registration numbers) counted distinctly. No sampling, no name heuristics, no external sources.

## Headline results — verified
| Measure | Count |
|---|---|
| Total device configurations (rows) | **1695** |
| Mainnet | **1598** |
| Testnet | **93** |
| Under review (canary/beta) | **4** |
| Chain families | **23** |
| Duplicate DeviceIDs | 0 |
| DeviceID sets identical across both manifests | YES |
| Distinct mainnet networks (by chain name) | 1586 |
| Distinct mainnet chain IDs | 1569 |

The headline figure is **1,598 mainnet listener configurations**. The distinct-network figure is 1,586: twelve networks are registered under two families each (dual registrations, each with its own DeviceID and configuration) — Acala Network, Algorand Mainnet, Aptos Mainnet, Bitcoin Mainnet, Cosmos Hub, Eclipse Mainnet, Hedera Mainnet, NEAR Mainnet, Phala Network, Sui Mainnet, Tron Mainnet, Xahau Network. A deduplicated name+chain-ID pair count of the mainnet set is 1,589; that is a deduplication statistic, not the device count.

## Under review (4)
| Chain | Chain ID | DeviceID | Family |
|---|---|---|---|
| BEVM Canary | 1501 | evm__BEVM_Canary | evm |
| Opulent-X BETA | 41500 | evm__Opulent-X_BETA | evm |
| Songbird Canary-Network | 19 | evm__Songbird_Canary-Network | evm |
| Vulture EVM Beta | 3102 | evm__Vulture_EVM_Beta | evm |

## Family breakdown (all networks)
| Family | Devices |
|---|---|
| evm | 1638 |
| cosmos_sdk | 12 |
| utxo | 8 |
| substrate | 6 |
| solana_svm | 4 |
| directed_acyclic_graph | 3 |
| move_vm | 3 |
| algorand | 2 |
| algorand_ecosystem | 2 |
| solana | 2 |
| xrpl | 2 |
| xrpl_ecosystem | 2 |
| aptos | 1 |
| bitcoin | 1 |
| cardano | 1 |
| cosmos | 1 |
| elrond_multiversx | 1 |
| near | 1 |
| near_ecosystem | 1 |
| starknet_ecosystem | 1 |
| sui | 1 |
| ton_ecosystem | 1 |
| tron | 1 |

## Other numbers in circulation — what they actually refer to
- **1,691** = packaged listener module instances found in the build tree (2026-10-31 finding: template instances, since remediated by the binding factory). A build artefact count, not the register.
- **1,589** = deduplicated (chain name, chain ID) pairs in the mainnet set — the figure a 2026-11-05 parallel-session audit produced from a deduplicated export. A statistic, not the device count.
- Any other headline count for this register should be treated as unverified unless it traces to the two files above.

## Binding / deliverability status at audit date
- UNIT-001 (Ethereum Mainnet) and SET-001 (BSC, Polygon, Arbitrum One, OP Mainnet, Avalanche C-Chain): bound via factory/bind_units.py and live-benched; SKUs ACA-ALETHEIA-UNIT / ACA-ALETHEIA-PACK5 ready_to_list ($2,500 / $9,997).
- UNIT-007 (Solana Mainnet Beta): genesis-hash-bound, live-benched; no SKU or price adopted.
- All other configurations bind per-allocation on sale (ledger-enforced: one allocation per DeviceID, ever).

## Honest limits of this audit
- This audit verifies the REGISTER (the manifests). It is not a live probe of 1,695 networks.
- The register's Explorer and PublicRPC columns are empty (0 / 0 filled): endpoints are resolved at binding time by the factory's failover logic, not stored in the manifest. Any document claiming the manifest itself carries verified endpoints is wrong.
- Full device-by-device catalogue: catalogue-2026-11-07.csv (1,695 rows, generated from the register in this audit).
