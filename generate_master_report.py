#!/usr/bin/env python3
import json
from pathlib import Path

def main():
    input_json = Path("dist_registry/master_mainnets_hall_of_records.json")
    output_report = Path("dist_registry/master_verified_mainnets_report.md")
    if not input_json.exists():
        return
    with open(input_json, "r", encoding="utf-8") as f:
        records = json.load(f)
    report_lines = [
        "# THEIA-ARRAY: MASTER VERIFIED MAINNET REGISTRY",
        "**Hall of Records — Immutable Production Mainnet Catalog**",
        f"**Total Verified Networks:** {len(records)}",
        "",
        "| Index | Network Name | Family | ChainID / ID | Currency | Explorer |",
        "| :---: | :--- | :--- | :--- | :---: | :--- |"
    ]
    for idx, r in enumerate(records, start=1):
        name = r.get("name", "Unknown")
        family = r.get("family", "unknown").upper()
        chain_id = r.get("chain_id", "N/A")
        symbol = r.get("currency_symbol", "N/A")
        explorer = r.get("explorer_url", "")
        explorer_markdown = f"[Link]({explorer})" if explorer else "N/A"
        report_lines.append(f"| {idx} | **{name}** | {family} | `{chain_id}` | {symbol} | {explorer_markdown} |")
    output_report.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Report generated: {output_report}")

if __name__ == "__main__":
    main()
