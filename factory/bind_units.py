#!/usr/bin/env python3
"""Binder: builds one customer unit package for one DeviceID and records the allocation.

  python3 factory/bind_units.py --device evm__Ethereum_Mainnet --buyer-ref ORDER-0001 \
      --catalogue catalogue-2026-11-07.csv --gate4 gate4_lite_evm_results.csv \
      --ledger allocations.sqlite --out packages [--watch 0xADDR ...] [--chains-file chains.json]

Refuses (exit 1) when: the device is not in the catalogue, is not a mainnet, is not an EVM-family
device (the unit runtime supports EVM only), has no PASS verdict in the Gate-4-lite results (PARTIAL
only with --allow-partial), or is already allocated. One allocation per DeviceID, ever: enforced by a
PRIMARY KEY in the SQLite ledger. The package is built first and the allocation is committed only if
the build succeeded. Exit codes: 0 ok, 1 refused/failed, 2 usage/input error.
"""
import argparse, csv, hashlib, json, os, shutil, sqlite3, sys, tempfile, urllib.parse
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent / "unit" / "aletheia_unit.py"
UNIT_VERSION = "1.0.0"
README = """Alētheia Array(TM) unit for {device_id} (chain id {chain_id}), unit runtime {ver}
Archer Chain Analytics

Run:     python3 aletheia_unit.py --config unit-config.json
Verify:  python3 aletheia_unit.py --verify records.jsonl
Integrity of this package: sha256sum -c SHA256SUMS
Requires Python 3.8+. No third-party packages. Needs outbound HTTPS to the endpoints in unit-config.json.

Behaviour: one hash-chained JSON record per finalized block; refuses to run on a wrong chain id;
halts on a parent-hash continuity break; resumes safely after a restart.
Not included: signatures (AcerbE signing is a separate service), non-EVM chains, protection against
a dishonest RPC provider. Edit "watch" in unit-config.json to add addresses (0x + 40 hex) to record.
"""


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def refuse(msg):
    print(f"REFUSED: {msg}", file=sys.stderr)
    return 1


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def extra_endpoints(chains_file, chain_id, have, limit=5):
    out = []
    if not chains_file:
        return out
    for c in json.load(open(chains_file, encoding="utf-8")):
        if c.get("chainId") == chain_id:
            for u in c.get("rpc", []):
                if isinstance(u, str) and u.startswith("https://") and "{" not in u and u not in have and u not in out:
                    out.append(u)
    return out[:limit]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for n in ("--device", "--buyer-ref", "--catalogue", "--gate4", "--ledger", "--out"):
        ap.add_argument(n, required=True)
    ap.add_argument("--watch", action="append", default=[])
    ap.add_argument("--chains-file")
    ap.add_argument("--finality-depth", type=int, default=12)
    ap.add_argument("--allow-partial", action="store_true")
    a = ap.parse_args(argv)
    try:
        cat = {r["DeviceID"]: r for r in read_csv(a.catalogue)}
        g4 = {r["DeviceID"]: r for r in read_csv(a.gate4)}
    except (OSError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    row = cat.get(a.device)
    if not row:
        return refuse(f"{a.device} is not in the catalogue")
    if row["Network"] != "mainnet":
        return refuse(f"{a.device} is labelled '{row['Network']}', not mainnet")
    if row["Family"] != "evm" or not row["ChainId"].isdigit():
        return refuse(f"family '{row['Family']}' is not supported by the unit runtime (EVM only; other families are ROADMAP)")
    v = g4.get(a.device)
    if not v:
        return refuse("no Gate-4-lite result for this device; run scripts/gate4_lite_evm.py first")
    ok = {"PASS"} | ({"PARTIAL"} if a.allow_partial else set())
    if v["Verdict"] not in ok:
        return refuse(f"Gate-4-lite verdict is {v['Verdict']}")
    chain_id = int(row["ChainId"])
    eps = [v["Endpoint"]] + extra_endpoints(a.chains_file, chain_id, {v["Endpoint"]})
    cfg = {"device_id": a.device, "chain_id": chain_id, "endpoints": eps, "watch": a.watch,
           "finality_depth": a.finality_depth, "poll_seconds": 6, "start_block": None,
           "output": "records.jsonl", "state": "state.json"}
    out = Path(a.out)
    final = out / a.device
    out.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(a.ledger, isolation_level=None)
    db.execute("CREATE TABLE IF NOT EXISTS allocations (device_id TEXT PRIMARY KEY, buyer_ref TEXT NOT NULL, "
               "allocated_utc TEXT NOT NULL, unit_version TEXT NOT NULL, package_sha256 TEXT NOT NULL)")
    tmp = Path(tempfile.mkdtemp(dir=out, prefix=".build-"))
    try:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM allocations WHERE device_id=?", (a.device,)).fetchone():
            db.execute("ROLLBACK")
            return refuse(f"{a.device} is already allocated (one allocation per DeviceID, ever)")
        if final.exists():
            db.execute("ROLLBACK")
            return refuse(f"{final} already exists but is not in the ledger; investigate before binding")
        shutil.copy2(RUNTIME, tmp / "aletheia_unit.py")
        (tmp / "unit-config.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        (tmp / "README.txt").write_text(README.format(device_id=a.device, chain_id=chain_id, ver=UNIT_VERSION), encoding="utf-8")
        sums = "".join(f"{sha_file(tmp / n)}  {n}\n" for n in ("README.txt", "aletheia_unit.py", "unit-config.json"))
        (tmp / "SHA256SUMS").write_text(sums, encoding="utf-8")
        pkg_sha = hashlib.sha256(sums.encode()).hexdigest()
        db.execute("INSERT INTO allocations VALUES (?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'),?,?)",
                   (a.device, a.buyer_ref, UNIT_VERSION, pkg_sha))
        os.rename(tmp, final)
        db.execute("COMMIT")
    except Exception as e:
        try:
            db.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        return refuse(f"build failed, nothing allocated: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"BOUND {a.device} -> {final} (package sha256 {pkg_sha})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
