#!/usr/bin/env python3
"""Alētheia Array(TM) EVM ingestion unit v1.0.0 (stdlib only).

Observes one EVM chain through public JSON-RPC endpoints and writes a hash-chained JSONL
record per finalized block. Fails closed.

  python3 aletheia_unit.py --config unit-config.json [--max-blocks N]
  python3 aletheia_unit.py --verify records.jsonl

Guarantees implemented here:
  * every endpoint must answer eth_chainId == configured chain_id before it is used (mismatch = banned)
  * records are filed only for blocks at least `finality_depth` behind the head
  * parent-hash continuity is enforced between consecutive filed blocks; a break halts the unit (exit 1)
  * records carry prev_record_hash/record_hash (SHA-256), so edits, deletions and reordering are detectable
  * restart-safe: atomic state file, crash-recovery of the last record, no gaps, no duplicates
NOT implemented (do not claim): signatures (AcerbE signing needs the AcerbE service), non-EVM chains,
websocket subscriptions, protection against a malicious RPC provider (single-source trust per block).
Exit codes: 0 ok, 1 fatal/verification failure, 2 usage or config error.
"""
import argparse, datetime, hashlib, json, os, re, signal, sys, time, urllib.error, urllib.parse, urllib.request

VERSION = "1.0.0"
GENESIS = "0" * 64
H64 = re.compile(r"^0x[0-9a-fA-F]{64}$")
A40 = re.compile(r"^0x[0-9a-fA-F]{40}$")


class Fatal(Exception):
    pass


class Transient(Exception):
    pass


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def record_hash(rec):
    body = {k: v for k, v in rec.items() if k != "record_hash"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def valid_endpoint(u):
    p = urllib.parse.urlparse(u)
    return (p.scheme == "https" and bool(p.netloc)) or (p.scheme == "http" and p.hostname in ("127.0.0.1", "localhost"))


def load_config(path):
    try:
        c = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read config: {e}")
    if not isinstance(c.get("device_id"), str) or not c["device_id"]:
        raise ValueError("device_id required")
    if not isinstance(c.get("chain_id"), int) or isinstance(c["chain_id"], bool) or c["chain_id"] <= 0:
        raise ValueError("chain_id must be a positive integer")
    eps = c.get("endpoints")
    if not isinstance(eps, list) or not eps or not all(isinstance(e, str) and valid_endpoint(e) for e in eps):
        raise ValueError("endpoints must be a non-empty list of https URLs")
    watch = c.get("watch", [])
    if not isinstance(watch, list) or not all(isinstance(a, str) and A40.match(a) for a in watch):
        raise ValueError("watch must be a list of 0x-prefixed 20-byte addresses")
    c["watch"] = sorted({a.lower() for a in watch})
    depth = c.get("finality_depth", 12)
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
        raise ValueError("finality_depth must be an integer >= 0")
    c["finality_depth"] = depth
    poll = c.get("poll_seconds", 6)
    if not isinstance(poll, (int, float)) or isinstance(poll, bool) or poll <= 0:
        raise ValueError("poll_seconds must be > 0")
    c["poll_seconds"] = poll
    sb = c.get("start_block")
    if sb is not None and (not isinstance(sb, int) or isinstance(sb, bool) or sb < 0):
        raise ValueError("start_block must be null or an integer >= 0")
    base = os.path.dirname(os.path.abspath(path))
    for k, d in (("output", "records.jsonl"), ("state", "state.json")):
        v = c.get(k, d)
        c[k] = v if os.path.isabs(v) else os.path.join(base, v)
    return c


def http_call(url, method, params, timeout=10):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": f"AletheiaUnit/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Transient(f"{type(e).__name__}")
    if not isinstance(d, dict) or d.get("error") or d.get("result") is None:
        raise Transient("rpc-error")
    return d["result"]


def hx(v):
    if not isinstance(v, str) or not re.match(r"^0x[0-9a-fA-F]+$", v):
        raise Transient("bad-hex")
    return int(v, 16)


class Rpc:
    """Endpoint pool with failover. An endpoint is used only after eth_chainId matches."""

    def __init__(self, endpoints, chain_id, call=http_call):
        self.eps, self.chain_id, self.call = list(endpoints), chain_id, call
        self.ok, self.banned, self.cur = set(), set(), 0

    def _verified(self, u):
        if u in self.ok:
            return True
        cid = hx(self.call(u, "eth_chainId", []))
        if cid != self.chain_id:
            self.banned.add(u)
            return False
        self.ok.add(u)
        return True

    def request(self, method, params):
        n = len(self.eps)
        for k in range(n):
            u = self.eps[(self.cur + k) % n]
            if u in self.banned:
                continue
            try:
                if not self._verified(u):
                    continue
                res = self.call(u, method, params)
                self.cur = (self.cur + k) % n
                return res
            except Transient:
                continue
        if len(self.banned) == n:
            raise Fatal("every endpoint reports a different chain id (wrong network); refusing to run")
        raise Transient("all endpoints failed")

    def startup(self):
        if not any(self._safe_verify(u) for u in self.eps):
            if len(self.banned) == len(self.eps):
                raise Fatal("every endpoint reports a different chain id (wrong network); refusing to run")
            raise Fatal("no reachable endpoint passed the chain-id handshake")

    def _safe_verify(self, u):
        try:
            return self._verified(u)
        except Transient:
            return False

    def head(self):
        return hx(self.request("eth_blockNumber", []))

    def block(self, n):
        b = self.request("eth_getBlockByNumber", [hex(n), True])
        if not isinstance(b, dict):
            raise Transient("no-block")
        return b


def load_state(path):
    if not os.path.exists(path):
        return {"next_block": None, "last_hash": GENESIS, "seq": 0, "last_block_hash": None, "last_block_number": None}
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        raise Fatal(f"state file unreadable: {path}")


def save_state(path, st):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def last_record(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 65536))
        lines = [l for l in f.read().decode("utf-8", "replace").splitlines() if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except ValueError:
        raise Fatal("output file ends with a corrupt record; refusing to continue")


def recover(st, out_path):
    """Reconcile state with the output tail (crash between append and state write)."""
    rec = last_record(out_path)
    if rec is None:
        if st["seq"] != 0:
            raise Fatal("state says records exist but output file is empty or missing")
        return st
    if rec["seq"] == st["seq"] and rec["record_hash"] == st["last_hash"]:
        return st
    if rec["seq"] == st["seq"] + 1 and rec["prev_record_hash"] == st["last_hash"] and record_hash(rec) == rec["record_hash"]:
        st.update(seq=rec["seq"], last_hash=rec["record_hash"], last_block_hash=rec["block_hash"],
                  last_block_number=rec["block_number"], next_block=rec["block_number"] + 1)
        return st
    raise Fatal("state and output disagree; refusing to continue (restore the pair from backup)")


def build_record(cfg, st, blk):
    for k in ("hash", "parentHash"):
        if not isinstance(blk.get(k), str) or not H64.match(blk[k]):
            raise Transient(f"bad-{k}")
    num, ts = hx(blk.get("number")), hx(blk.get("timestamp"))
    txs = blk.get("transactions")
    if not isinstance(txs, list):
        raise Transient("bad-transactions")
    watch = set(cfg["watch"])
    matches = []
    for t in txs:
        if not isinstance(t, dict):
            raise Transient("bad-tx")
        fr, to = str(t.get("from", "")).lower(), str(t.get("to") or "").lower()
        if watch and (fr in watch or to in watch):
            matches.append({"hash": t.get("hash"), "from": fr, "to": to or None, "value_wei": str(hx(t.get("value", "0x0")))})
    rec = {"v": 1, "seq": st["seq"] + 1, "device_id": cfg["device_id"], "chain_id": cfg["chain_id"], "block_number": num,
           "block_hash": blk["hash"].lower(), "parent_hash": blk["parentHash"].lower(), "block_time": ts,
           "tx_count": len(txs), "matches": matches, "observed_at": utc(), "prev_record_hash": st["last_hash"]}
    rec["record_hash"] = record_hash(rec)
    return rec


def run(cfg, rpc, max_blocks=None, sleep=time.sleep, stop=lambda: False, log=print):
    rpc.startup()
    st = recover(load_state(cfg["state"]), cfg["output"])
    depth, filed, backoff = cfg["finality_depth"], 0, 1
    nxt = st["next_block"]
    while not stop():
        try:
            head = rpc.head()
            if nxt is None:
                nxt = cfg["start_block"] if cfg["start_block"] is not None else max(0, head - depth)
            backoff = 1
            while nxt <= head - depth and not stop():
                blk = rpc.block(nxt)
                if hx(blk.get("number")) != nxt:
                    raise Transient("block-number-mismatch")
                if st["last_block_number"] == nxt - 1 and st["last_block_hash"] and blk.get("parentHash", "").lower() != st["last_block_hash"]:
                    raise Fatal(f"continuity break at block {nxt}: parentHash does not match filed block {nxt - 1} "
                                f"(reorg deeper than finality_depth={depth} or inconsistent endpoint); nothing further filed")
                rec = build_record(cfg, st, blk)
                with open(cfg["output"], "a", encoding="utf-8") as f:
                    f.write(canonical(rec) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                st.update(seq=rec["seq"], last_hash=rec["record_hash"], last_block_hash=rec["block_hash"], last_block_number=nxt, next_block=nxt + 1)
                save_state(cfg["state"], st)
                nxt += 1
                filed += 1
                if max_blocks is not None and filed >= max_blocks:
                    return filed
            sleep(cfg["poll_seconds"])
        except Transient as e:
            log(f"[{utc()}] transient: {e}; retry in {backoff}s")
            sleep(backoff)
            backoff = min(backoff * 2, 60)
    return filed


def verify_file(path):
    prev, seq, last_num, last_hash, n = GENESIS, 0, None, None, 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                raise Fatal(f"line {i}: not valid JSON")
            if r.get("seq") != seq + 1:
                raise Fatal(f"line {i}: sequence break (expected {seq + 1}, got {r.get('seq')})")
            if r.get("prev_record_hash") != prev:
                raise Fatal(f"line {i}: prev_record_hash does not match previous record")
            if record_hash(r) != r.get("record_hash"):
                raise Fatal(f"line {i}: record_hash mismatch (record was altered)")
            if last_num is not None:
                if r["block_number"] != last_num + 1:
                    raise Fatal(f"line {i}: block gap ({last_num} -> {r['block_number']})")
                if r["parent_hash"] != last_hash:
                    raise Fatal(f"line {i}: parent_hash does not match previous block_hash")
            prev, seq, last_num, last_hash, n = r["record_hash"], seq + 1, r["block_number"], r["block_hash"], n + 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config")
    ap.add_argument("--verify", metavar="FILE")
    ap.add_argument("--max-blocks", type=int)
    a = ap.parse_args(argv)
    try:
        if a.verify:
            print(f"OK: {verify_file(a.verify)} records, hash chain and block continuity intact")
            return 0
        if not a.config:
            ap.error("--config or --verify required")
        cfg = load_config(a.config)
    except ValueError as e:
        print(f"CONFIG ERROR: {e}", file=sys.stderr)
        return 2
    except Fatal as e:
        print(f"VERIFY FAILED: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    flag = {"stop": False}
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, lambda *_: flag.update(stop=True))
    try:
        n = run(cfg, Rpc(cfg["endpoints"], cfg["chain_id"]), a.max_blocks, stop=lambda: flag["stop"])
    except Fatal as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 1
    print(f"filed {n} records -> {cfg['output']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
