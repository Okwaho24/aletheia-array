#!/usr/bin/env python3
import json
from pathlib import Path

def main():
    input_json = Path("dist_registry/master_mainnets_hall_of_records.json")
    if not input_json.exists():
        print("[!] Master mainnets JSON not found.")
        return
        
    records = json.loads(input_json.read_text(encoding="utf-8"))
    print(f"\n==================================================")
    print(f" THEIA-ARRAY: COMPLETE MASTER MAINNET LIST ({len(records)} Networks)")
    print(f"==================================================\n")
    
    for idx, r in enumerate(records, start=1):
        name = r.get("name", "Unknown")
        family = r.get("family", "unknown").upper()
        chain_id = r.get("chain_id", "N/A")
        symbol = r.get("currency_symbol", "N/A")
        print(f"[{idx:4d}] {name:<35} | Family: {family:<10} | ChainID: {chain_id:<15} | Currency: {symbol}")

    print(f"\n==================================================")
    print(f" END OF MASTER HALL OF RECORDS — {len(records)} NETWORKS LISTED")
    print(f"==================================================\n")

if __name__ == "__main__":
    main()
