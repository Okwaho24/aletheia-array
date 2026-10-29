#!/usr/bin/env python3
import json
import csv
from pathlib import Path

def is_mainnet(item):
    name = str(item.get("name", "")).lower()
    canonical_id = str(item.get("canonical_id", "")).lower()
    
    exclusion_keywords = [
        "test", "testnet", "sepolia", "goerli", "holesky", "devnet", 
        "privnet", "staging", "stagenet", "canary", "previewnet", 
        "ropsten", "rinkeby", "kovan", "mumbai", "amoy", "hoodi", 
        "jalnir", "katla", "hekla", "eldfell", "grimsvotn", "kopli", 
        "lasna", "aventine", "palatine", "galileo", "sokol", "baobab",
        "kairos", "fuji", "donau", "artio", "bartio", "bepolia", "deprecated",
        "beta", "alpha", "localnet", "mock", "simulator"
    ]
    
    combined_text = f"{name} {canonical_id}"
    for kw in exclusion_keywords:
        if kw in combined_text:
            return False
    return True

def main():
    input_json = Path("dist_registry/master_crypto_hall_of_records.json")
    output_json = Path("dist_registry/master_mainnets_hall_of_records.json")
    output_csv = Path("dist_registry/master_mainnets_hall_of_records.csv")
    
    if not input_json.exists():
        print(f"[!] Error: {input_json} not found. Run aggregate_master_registry.py first.")
        return
        
    print("[*] Loading master crypto hall of records...")
    with open(input_json, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    print(f"[*] Total records before filtering: {len(records)}")
    
    mainnet_records = [r for r in records if is_mainnet(r)]
    print(f"[✓] Filtered down to {len(mainnet_records)} strict MAINNET records.")
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(mainnet_records, f, indent=2)
        
    if mainnet_records:
        fieldnames = list(mainnet_records[0].keys())
        with open(output_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(mainnet_records)
            
    print(f"[✓] Mainnet catalog successfully compiled and saved to:\n    - {output_json}\n    - {output_csv}")

if __name__ == "__main__":
    main()
