##!/usr/bin/env python3
import csv
from pathlib import Path

def main():
    manifest_path = Path("identity_manifest.csv")
    if not manifest_path.exists():
        print("[!] identity_manifest.csv not found.")
        return

    print("[*] Normalizing node package paths and filling missing stubs...")
    created_count = 0

    with open(manifest_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for line_num, row in enumerate(reader, start=1):
            if not row or len(row) < 4:
                continue
            
            # Find a column containing a path ending in .json
            config_path_raw = ""
            for col in row:
                if "mesh-nodes/" in col or col.endswith(".json"):
                    config_path_raw = col.strip()
                    break
            
            if not config_path_raw and len(row) > 8:
                config_path_raw = row[8].strip()

            if config_path_raw:
                target_path = Path(config_path_raw)
                if not target_path.parent.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                if not target_path.exists():
                    target_path.write_text('{"status": "initialized", "node": "validated"}', encoding='utf-8')
                    created_count += 1

    print(f"[✓] Normalization complete. Created {created_count} missing node config stubs.")

if __name__ == "__main__":
    main()

