#!/usr/bin/env python3
"""Gate-4-lite for EVM devices (stdlib only; makes live JSON-RPC calls).

Per catalogue row with Family=evm and the selected Network(s), using public https RPC
endpoints from chainid.network, checks:
  G1 handshake   eth_chainId equals the catalogue ChainId
  G2 height      eth_blockNumber parses; latest block timestamp is fresh (<= --max-age s)
  G3 tx parse    a recent block (latest..latest-N) contains a transaction with valid hash/from fields
  G4 cross-check a second, different-host endpoint reports a height within --tolerance blocks
This substitutes an independent second RPC for the "public explorer" comparison in the full Gate-4,
and makes no check for placeholder strings (that applies to generated source, not the register).
Verdicts: PASS (G1-G4) | PARTIAL (G1+G2 ok, G3 or G4 missing) | FAIL:<reason> | NO_ENDPOINT.
Result reflects this machine's network at run time; it is evidence, not a permanent status.
"""
import argparse, collections, concurrent.futures as cf, csv, datetime, http.client, json, re, sys, threading, time, urllib.error, urllib.parse, urllib.request

HEX = re.compile(r"^0x[0-9a-fA-F]+$")


def http_rpc(url, method, params, timeout=8):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "AletheiaGate4Lite/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as e:
        return None, f"{type(e).__name__}"
    if not isinstance(d, dict) or "result" not in d or d["result"] is None:
        return None, "rpc-error"
    return d["result"], None


def hexint(x):
    return int(x, 16) if isinstance(x, str) and HEX.match(x) else None


def probe(url, chain_id, rpc, now, max_age, lookback=8):
    """Return dict(ok_g1, ok_g2, g3, height, reason)."""
    res, err = rpc(url, "eth_chainId", [])
    cid = hexint(res)
    if cid is None:
        return {"g1": False, "reason": f"no-handshake:{err}"}
    if cid != chain_id:
        return {"g1": False, "reason": f"chainid-mismatch:{cid}"}
    res, err = rpc(url, "eth_blockNumber", [])
    h = hexint(res)
    if h is None:
        return {"g1": True, "g2": False, "reason": f"no-height:{err}"}
    blk, err = rpc(url, "eth_getBlockByNumber", ["latest", True])
    ts = hexint(blk.get("timestamp")) if isinstance(blk, dict) else None
    if ts is None:
        return {"g1": True, "g2": False, "height": h, "reason": "no-block"}
    if now - ts > max_age:
        return {"g1": True, "g2": False, "height": h, "reason": f"stale:{int(now - ts)}s"}
    g3 = False
    for back in range(lookback):
        b = blk if back == 0 else rpc(url, "eth_getBlockByNumber", [hex(h - back), True])[0]
        txs = b.get("transactions") if isinstance(b, dict) else None
        if txs and isinstance(txs[0], dict) and re.match(r"^0x[0-9a-fA-F]{64}$", str(txs[0].get("hash", ""))) \
                and re.match(r"^0x[0-9a-fA-F]{40}$", str(txs[0].get("from", ""))):
            g3 = True
            break
    return {"g1": True, "g2": True, "g3": g3, "height": h, "reason": ""}


def verify_chain(chain_id, urls, rpc, now, max_age, tolerance, max_tries=4):
    if not urls:
        return {"verdict": "NO_ENDPOINT", "endpoint": "", "height": "", "reason": "none in chainid.network"}
    first, last_reason, tried = None, "", 0
    for u in urls:
        if tried >= max_tries:
            break
        tried += 1
        p = probe(u, chain_id, rpc, now, max_age)
        if p.get("g1") and p.get("g2"):
            first = (u, p); break
        last_reason = p.get("reason", "")
    if not first:
        return {"verdict": "FAIL:" + (last_reason or "unreachable"), "endpoint": "", "height": "", "reason": last_reason}
    u, p = first
    host = urllib.parse.urlparse(u).netloc
    g4 = False
    for v in urls:
        if urllib.parse.urlparse(v).netloc == host:
            continue
        r, _ = rpc(v, "eth_chainId", [])
        if hexint(r) != chain_id:
            continue
        r, _ = rpc(v, "eth_blockNumber", [])
        h2 = hexint(r)
        if h2 is not None and abs(h2 - p["height"]) <= tolerance:
            g4 = True
            break
    verdict = "PASS" if (p["g3"] and g4) else "PARTIAL"
    missing = [n for n, ok in (("tx-parse", p["g3"]), ("cross-check", g4)) if not ok]
    return {"verdict": verdict, "endpoint": u, "height": p["height"], "reason": ",".join(missing)}


def usable(urls):
    return [u for u in urls if isinstance(u, str) and u.startswith("https://") and "{" not in u and "@" not in urllib.parse.urlparse(u).netloc]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("catalogue"); ap.add_argument("--chains-file", help="local chainid.network chains.json (else fetched)")
    ap.add_argument("--networks", default="mainnet", help="comma list of Network values (default mainnet)")
    ap.add_argument("--only", help="comma list of chain IDs (smoke test)")
    ap.add_argument("--out", default="gate4_lite_evm_results.csv"); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--max-age", type=int, default=3600); ap.add_argument("--tolerance", type=int, default=1000)
    a = ap.parse_args(argv)
    try:
        if a.chains_file:
            chains = json.load(open(a.chains_file, encoding="utf-8"))
        else:
            req = urllib.request.Request("https://chainid.network/chains.json", headers={"User-Agent": "AletheiaGate4Lite/1.0"})
            chains = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    except Exception as e:
        print(f"ERROR: cannot load chain list: {e}", file=sys.stderr); return 2
    rpcs = {c["chainId"]: usable(c.get("rpc", [])) for c in chains if isinstance(c.get("chainId"), int)}
    nets = set(a.networks.split(","))
    only = {int(x) for x in a.only.split(",")} if a.only else None
    with open(a.catalogue, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["Family"] == "evm" and r["Network"] in nets]
    jobs = []
    for r in rows:
        cid = int(r["ChainId"]) if r["ChainId"].isdigit() else None
        if cid is None or (only and cid not in only):
            continue
        jobs.append((r, cid))
    host_gate = collections.defaultdict(lambda: threading.Semaphore(4))
    def gated_rpc(url, method, params):
        with host_gate[urllib.parse.urlparse(url).netloc]:
            return http_rpc(url, method, params)
    now_fn = time.time
    out, done = [], [0]
    def work(job):
        r, cid = job
        res = verify_chain(cid, rpcs.get(cid, []), gated_rpc, now_fn(), a.max_age, a.tolerance)
        done[0] += 1
        if done[0] % 100 == 0:
            print(f"  {done[0]}/{len(jobs)}", file=sys.stderr, flush=True)
        return {"DeviceID": r["DeviceID"], "ChainName": r["ChainName"], "ChainId": cid, "Network": r["Network"],
                "Verdict": res["verdict"], "Endpoint": res["endpoint"], "Height": res["height"], "Detail": res["reason"],
                "CheckedUTC": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with cf.ThreadPoolExecutor(a.workers) as ex:
        out = list(ex.map(work, jobs))
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["DeviceID"]); w.writeheader(); w.writerows(out)
    c = collections.Counter(o["Verdict"].split(":")[0] for o in out)
    print(f"checked={len(out)} " + " ".join(f"{k}={v}" for k, v in sorted(c.items())) + f" -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
