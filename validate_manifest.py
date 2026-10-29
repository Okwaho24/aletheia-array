#!/usr/bin/env python3
import os
import sys
import json
import csv
import urllib.request
from pathlib import Path

def get_canonical_evm_chains():
    print("[*] Fetching global EVM chain registry...")
    chain_map = {}
    try:
        url = "https://chainid.network/chains.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Termux-Validator/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            for item in data:
                if 'chainId' in item and item['chainId'] is not None:
                    chain_map[str(item['chainId']).strip()] = item['name']
    except Exception as e:
        print(f"[!] Warning: Could not reach Chainlist API ({e}). Skipping remote ID validation.")
    return chain_map

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "identity_manifest.csv"
    manifest_file = Path(csv_path)
    
    if not manifest_file.exists():
        print(f"[!] Critical: Target CSV file does not exist at '{csv_path}'")
        sys.exit(1)

    workspace_root = manifest_file.parent
    chain_map = get_canonical_evm_chains()
    failures = []
    
    print(f"[*] Auditing manifest configurations from '{csv_path}'...")
    
    with open(manifest_file, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for line_num, row in enumerate(reader, start=1):
            if not row or len(row) < 4:
                continue
                
            joined_row = "".join(row).lower()
            if line_num == 1 or "chainname" in joined_row or "configpath" in joined_row:
                continue

            config_path_raw = ""
            chain_name = "UNKNOWN"
            chain_id_raw = ""
            family = ""

            for col in row:
                col_str = col.strip()
                if "mesh-nodes" in col_str or col_str.endswith(".json"):
                    config_path_raw = col_str
                elif col_str.isdigit() or (col_str.startswith("0x") and len(col_str) < 10):
                    if not chain_id_raw:
                        chain_id_raw = col_str

            if not config_path_raw and len(row) > 8:
                config_path_raw = row[8].strip()
            if len(row) > 2:
                chain_name = row[2].strip() if row[2].strip() else "UNKNOWN"
            if len(row) > 1:
                family = row[1].strip().lower()

            if not config_path_raw:
                failures.append((line_num, chain_name, "Missing ConfigPath entry"))
                continue

            config_file = Path(config_path_raw)
            if not config_file.is_absolute():
                config_file = workspace_root / config_path_raw

            if not config_file.is_file():
                failures.append((line_num, chain_name, f"Config path non-existent on disk: {config_path_raw}"))
            else:
                try:
                    with open(config_file, 'r', encoding='utf-8') as jf:
                        json.load(jf)
                except Exception as e:
                    failures.append((line_num, chain_name, f"Malformed JSON structure: {config_path_raw}"))

            if family == "evm" and chain_id_raw.isdigit():
                if chain_id_raw in chain_map:
                    expected_name = chain_map[chain_id_raw]
                    if (expected_name.lower() not in chain_name.lower()) and (chain_name.lower() not in expected_name.lower()):
                        failures.append((line_num, chain_name, f"ChainID {chain_id_raw} globally maps to '{expected_name}'"))

    print("\n--- ALETHEIA MANIFEST AUDIT SUMMARY (TERMUX) ---")
    if not failures:
        print("[✓] All records validated successfully with zero errors.")
    else:
        print(f"[X] Identified {len(failures)} discrepancy/discrepancies:\n")
        print(f"{'Line':<6} | {'Chain Name':<25} | Error")
        print("-" * 65)
        for line, chain, err in failures:
            print(f"{line:<6} | {chain[:25]:<25} | {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
