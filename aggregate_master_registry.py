#!/usr/bin/env python3
import os
import json
import csv
import urllib.request
from pathlib import Path

# Configuration & Output Paths
OUTPUT_DIR = Path("dist_registry")
MASTER_JSON = OUTPUT_DIR / "master_crypto_hall_of_records.json"
MASTER_CSV = OUTPUT_DIR / "master_crypto_hall_of_records.csv"

def fetch_evm_registry():
    print("[*] Fetching canonical EVM chains from chainid.network...")
    url = "https://chainid.network/chains.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Aletheia-Array-Harvester/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"[!] Warning: Failed to fetch EVM registry ({e})")
        return []

def get_static_non_evm_registry():
    """Defines baseline immutable entries for non-EVM sovereign architectures (BTC, Solana, XRPL, Stellar)"""
    return [
        {
            "name": "Bitcoin Mainnet",
            "chain": "bitcoin",
            "network": "mainnet",
            "family": "utxo",
            "chainId": "btc-mainnet",
            "nativeCurrency": {"name": "Bitcoin", "symbol": "BTC", "decimals": 8},
            "rpc": ["https://btc-node.internal.local"],
            "explorers": [{"name": "mempool.space", "url": "https://mempool.space"}]
        },
        {
            "name": "Solana Mainnet Beta",
            "chain": "solana",
            "network": "mainnet-beta",
            "family": "solana_svm",
            "chainId": "solana-mainnet",
            "nativeCurrency": {"name": "Solana", "symbol": "SOL", "decimals": 9},
            "rpc": ["https://api.mainnet-beta.solana.com"],
            "explorers": [{"name": "SolanaFM", "url": "https://solana.fm"}]
        },
        {
            "name": "XRP Ledger Mainnet",
            "chain": "xrpl",
            "network": "mainnet",
            "family": "xrpl",
            "chainId": "xrpl-mainnet",
            "nativeCurrency": {"name": "XRP", "symbol": "XRP", "decimals": 6},
            "rpc": ["https://s1.ripple.com:51234"],
            "explorers": [{"name": "XRPSCAN", "url": "https://xrpscan.com"}]
        },
        {
            "name": "Stellar Mainnet",
            "chain": "stellar",
            "network": "mainnet",
            "family": "stellar",
            "chainId": "stellar-mainnet",
            "nativeCurrency": {"name": "Lumens", "symbol": "XLM", "decimals": 7},
            "rpc": ["https://horizon.stellar.org"],
            "explorers": [{"name": "Stellar Expert", "url": "https://stellar.expert"}]
        }
    ]

def normalize_records(evm_data, non_evm_data):
    print("[*] Harmonizing and normalizing multi-chain records...")
    normalized_records = []

    # 1. Normalize EVM records
    for item in evm_data:
        record = {
            "canonical_id": f"evm-{item.get('chainId', 'unknown')}",
            "name": item.get("name", "Unknown EVM Chain"),
            "family": "evm",
            "chain_id": str(item.get("chainId", "")),
            "currency_name": item.get("nativeCurrency", {}).get("name", "Ether"),
            "currency_symbol": item.get("nativeCurrency", {}).get("symbol", "ETH"),
            "currency_decimals": item.get("nativeCurrency", {}).get("decimals", 18),
            "rpc_endpoints": json.dumps(item.get("rpc", [])),
            "explorer_url": item.get("explorers", [{}])[0].get("url", "") if item.get("explorers") else ""
        }
        normalized_records.append(record)

    # 2. Normalize Non-EVM records
    for item in non_evm_data:
        record = {
            "canonical_id": f"{item['family']}-{item['chainId']}",
            "name": item["name"],
            "family": item["family"],
            "chain_id": item["chainId"],
            "currency_name": item["nativeCurrency"]["name"],
            "currency_symbol": item["nativeCurrency"]["symbol"],
            "currency_decimals": item["nativeCurrency"]["decimals"],
            "rpc_endpoints": json.dumps(item["rpc"]),
            "explorer_url": item["explorers"][0]["url"]
        }
        normalized_records.append(record)

    return normalized_records

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    evm_raw = fetch_evm_registry()
    non_evm_raw = get_static_non_evm_registry()
    
    master_records = normalize_records(evm_raw, non_evm_raw)

    # Write Master JSON Catalog
    print(f"[*] Writing master catalog to {MASTER_JSON}...")
    with open(MASTER_JSON, 'w', encoding='utf-8') as f:
        json.dump(master_records, f, indent=2)

    # Write Master CSV Catalog
    print(f"[*] Writing flat records to {MASTER_CSV}...")
    fieldnames = ["canonical_id", "name", "family", "chain_id", "currency_name", "currency_symbol", "currency_decimals", "rpc_endpoints", "explorer_url"]
    with open(MASTER_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_records)

    print(f"[✓] Harmonization complete! Successfully cataloged {len(master_records)} total sovereign networks.")

if __name__ == "__main__":
    main()

