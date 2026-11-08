#!/usr/bin/env python3
"""Alētheia Array(TM) register verifier (stdlib only, read-only).

Reproduces the headline counts of a catalogue CSV and flags mainnet-labelled
rows whose names look like test/dev networks. Fails closed: exit 1 on duplicate
DeviceIDs, unknown Network values, missing columns, or a mismatch with --expect.

Usage:
  python3 verify_register.py CATALOGUE.csv [--expect total,mainnet,testnet,review,families]
                                          [--suspects-csv OUT.csv]
Exit codes: 0 ok, 1 verification failure, 2 usage/input error.
"""
import argparse, csv, collections, re, sys

REQUIRED = ["DeviceID", "Family", "ChainName", "ChainId", "Network"]
VALID_NETWORKS = {"mainnet", "testnet", "review"}
# Heuristic only: name-based review aid, never a classification.
STRONG = re.compile(
    r"testnet|tesnet|devnet|sepolia|goerli|holesky|hoodi|kiln|zhejiang|mekong|"
    r"stage\d|sparknet|kopli|lasna|sketchpad|blueberry|raspberry|katla|jolnir|"
    r"eldfell|grimsvotn|dusknet|passethub|westend|shasta|\bnile\b|amoy|mumbai|"
    r"fuji|chapel|alfajores|staging", re.I)
WEAK = re.compile(r"\bbeta\b|canary|mainnetdev|\bdev\b", re.I)


def load(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("missing columns: " + ", ".join(missing))
        return list(reader)


def analyse(rows):
    ids = [r["DeviceID"] for r in rows]
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    nets = collections.Counter(r["Network"] for r in rows)
    bad_net = sorted(set(nets) - VALID_NETWORKS)
    main = [r for r in rows if r["Network"] == "mainnet"]
    suspects = []
    for r in main:
        n = r["ChainName"]
        if STRONG.search(n):
            suspects.append(("STRONG", r))
        elif WEAK.search(n):
            suspects.append(("WEAK", r))
    return {
        "total": len(rows), "unique_ids": len(set(ids)), "duplicates": dup,
        "mainnet": nets.get("mainnet", 0), "testnet": nets.get("testnet", 0),
        "review": nets.get("review", 0), "invalid_networks": bad_net,
        "families": len({r["Family"] for r in rows}),
        "mainnet_distinct_names": len({r["ChainName"] for r in main}),
        "mainnet_distinct_chain_ids": len({r["ChainId"] for r in main}),
        "empty_device_ids": sum(1 for i in ids if not i.strip()),
        "suspects": suspects,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("catalogue")
    p.add_argument("--expect", help="total,mainnet,testnet,review,families")
    p.add_argument("--suspects-csv")
    a = p.parse_args(argv)
    try:
        res = analyse(load(a.catalogue))
    except (OSError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    ok = True
    print(f"rows={res['total']} unique_ids={res['unique_ids']} families={res['families']}")
    print(f"mainnet={res['mainnet']} testnet={res['testnet']} review={res['review']}")
    print(f"mainnet distinct names={res['mainnet_distinct_names']} "
          f"distinct chain ids={res['mainnet_distinct_chain_ids']}")
    strong = [r for t, r in res["suspects"] if t == "STRONG"]
    weak = [r for t, r in res["suspects"] if t == "WEAK"]
    print(f"mainnet-labelled rows with test/dev-style names: strong={len(strong)} weak={len(weak)} (heuristic)")
    if res["duplicates"] or res["empty_device_ids"]:
        print(f"FAIL: duplicate DeviceIDs={len(res['duplicates'])} empty={res['empty_device_ids']}")
        ok = False
    if res["invalid_networks"]:
        print(f"FAIL: unknown Network values: {res['invalid_networks']}")
        ok = False
    if a.expect:
        try:
            exp = [int(x) for x in a.expect.split(",")]
            if len(exp) != 5:
                raise ValueError
        except ValueError:
            print("ERROR: --expect needs 5 integers", file=sys.stderr)
            return 2
        got = [res["total"], res["mainnet"], res["testnet"], res["review"], res["families"]]
        if got != exp:
            print(f"FAIL: expected {exp} got {got}")
            ok = False
        else:
            print("MATCH: counts equal --expect")
    if a.suspects_csv:
        with open(a.suspects_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Tier", "DeviceID", "Family", "ChainName", "ChainId", "LabelledNetwork"])
            for t, r in res["suspects"]:
                w.writerow([t, r["DeviceID"], r["Family"], r["ChainName"], r["ChainId"], r["Network"]])
        print(f"wrote {a.suspects_csv}")
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
