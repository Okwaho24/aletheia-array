import hashlib, json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "unit"))
import aletheia_unit as u

def bh(n, salt=""): return "0x" + hashlib.sha256(f"{salt}{n}".encode()).hexdigest()

class Chain:
    def __init__(self, chain_id=1, head=100, fork_at=None):
        self.chain_id, self.head, self.fork_at = chain_id, head, fork_at
        self.watch_tx = {}
    def block(self, n):
        parent = bh(n - 1, "fork" if self.fork_at is not None and n - 1 >= self.fork_at and n - 1 > 0 and False else "")
        if self.fork_at is not None and n == self.fork_at:
            parent = bh(n - 1, "fork")
        txs = [{"hash": bh(n * 1000 + i, "tx"), "from": "0x" + "1" * 40, "to": "0x" + "2" * 40, "value": hex(i)} for i in range(2)]
        txs += self.watch_tx.get(n, [])
        return {"number": hex(n), "hash": bh(n), "parentHash": parent, "timestamp": hex(1_700_000_000 + n), "transactions": txs}

def serve(chain):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            m, p = req["method"], req["params"]
            if m == "eth_chainId": res = hex(chain.chain_id)
            elif m == "eth_blockNumber": res = hex(chain.head)
            elif m == "eth_getBlockByNumber": res = chain.block(int(p[0], 16))
            else: res = None
            body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": res}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    s = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"

def cfg(d, eps, chain_id=1, depth=2, start=10, watch=()):
    c = {"device_id": "evm__T", "chain_id": chain_id, "endpoints": eps, "watch": list(watch), "finality_depth": depth,
         "poll_seconds": 1, "start_block": start, "output": "r.jsonl", "state": "s.json"}
    p = os.path.join(d, "c.json"); json.dump(c, open(p, "w")); return u.load_config(p)

def go(c, n=None, chain_id=1):
    return u.run(c, u.Rpc(c["endpoints"], chain_id), n, sleep=lambda s: None, log=lambda m: None)

class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.chain = Chain(); self.srv, self.url = serve(self.chain)
    def tearDown(self): self.srv.shutdown(); self.d.cleanup()
    def test_happy_path_and_verify(self):
        c = cfg(self.d.name, [self.url]); self.assertEqual(go(c, 20), 20)
        self.assertEqual(u.verify_file(c["output"]), 20)
        nums = [json.loads(l)["block_number"] for l in open(c["output"])]; self.assertEqual(nums, list(range(10, 30)))
    def test_only_finalized_blocks_filed(self):
        c = cfg(self.d.name, [self.url], depth=5, start=95)
        calls = {"n": 0}
        def sl(s):
            calls["n"] += 1
            if calls["n"] > 1: raise KeyboardInterrupt
        try: u.run(c, u.Rpc(c["endpoints"], 1), None, sleep=sl, log=lambda m: None)
        except KeyboardInterrupt: pass
        nums = [json.loads(l)["block_number"] for l in open(c["output"])]; self.assertEqual(nums, [95])
    def test_wrong_chain_refused(self):
        c = cfg(self.d.name, [self.url], chain_id=2)
        with self.assertRaises(u.Fatal): go(c, 1, chain_id=2)
        self.assertFalse(os.path.exists(c["output"]))
    def test_failover_from_dead_endpoint(self):
        c = cfg(self.d.name, ["http://127.0.0.1:1", self.url]); self.assertEqual(go(c, 5), 5)
    def test_no_reachable_endpoint_is_fatal(self):
        c = cfg(self.d.name, ["http://127.0.0.1:1"])
        with self.assertRaises(u.Fatal): go(c, 1)
    def test_watch_filter(self):
        a = "0x" + "a" * 40; self.chain.watch_tx[12] = [{"hash": bh(1, "w"), "from": a.upper().replace("0X", "0x"), "to": "0x" + "3" * 40, "value": "0x10"}]
        c = cfg(self.d.name, [self.url], watch=[a]); go(c, 5)
        recs = [json.loads(l) for l in open(c["output"])]
        self.assertEqual([len(r["matches"]) for r in recs], [0, 0, 1, 0, 0]); self.assertEqual(recs[2]["matches"][0]["value_wei"], "16")
    def test_resume_no_gaps_no_dupes(self):
        c = cfg(self.d.name, [self.url]); go(c, 7); go(c, 8)
        nums = [json.loads(l)["block_number"] for l in open(c["output"])]; self.assertEqual(nums, list(range(10, 25)))
        self.assertEqual(u.verify_file(c["output"]), 15)
    def test_crash_between_append_and_state_recovers(self):
        c = cfg(self.d.name, [self.url]); go(c, 3)
        st = json.load(open(c["state"])); st.update(seq=2, last_hash=json.loads(open(c["output"]).readlines()[1])["record_hash"],
                                                  last_block_number=11, last_block_hash=bh(11), next_block=12); json.dump(st, open(c["state"], "w"))
        go(c, 2); nums = [json.loads(l)["block_number"] for l in open(c["output"])]; self.assertEqual(nums, [10, 11, 12, 13, 14])
        self.assertEqual(u.verify_file(c["output"]), 5)
    def test_state_output_mismatch_is_fatal(self):
        c = cfg(self.d.name, [self.url]); go(c, 3); open(c["output"], "w").close()
        with self.assertRaises(u.Fatal): go(c, 1)
    def test_continuity_break_halts_and_files_nothing_more(self):
        self.chain.fork_at = 15; c = cfg(self.d.name, [self.url])
        with self.assertRaises(u.Fatal) as e: go(c, 20)
        self.assertIn("continuity break at block 15", str(e.exception))
        nums = [json.loads(l)["block_number"] for l in open(c["output"])]; self.assertEqual(nums, list(range(10, 15)))
    def test_tamper_detected(self):
        c = cfg(self.d.name, [self.url]); go(c, 5); lines = open(c["output"]).read().splitlines()
        r = json.loads(lines[2]); r["tx_count"] = 999; lines[2] = u.canonical(r); open(c["output"], "w").write("\n".join(lines) + "\n")
        with self.assertRaises(u.Fatal): u.verify_file(c["output"])
    def test_deleted_record_detected(self):
        c = cfg(self.d.name, [self.url]); go(c, 5); lines = open(c["output"]).read().splitlines(); del lines[2]
        open(c["output"], "w").write("\n".join(lines) + "\n")
        with self.assertRaises(u.Fatal): u.verify_file(c["output"])
    def test_config_validation(self):
        bad = [{"device_id": "x", "chain_id": 0, "endpoints": ["https://a"]}, {"device_id": "x", "chain_id": 1, "endpoints": ["http://evil.example"]},
               {"device_id": "x", "chain_id": 1, "endpoints": ["https://a"], "watch": ["nope"]}, {"chain_id": 1, "endpoints": ["https://a"]},
               {"device_id": "x", "chain_id": 1, "endpoints": ["https://a"], "finality_depth": -1}]
        for i, b in enumerate(bad):
            p = os.path.join(self.d.name, f"b{i}.json"); json.dump(b, open(p, "w"))
            with self.assertRaises(ValueError, msg=str(b)): u.load_config(p)
    def test_cli_exit_codes(self):
        c = cfg(self.d.name, [self.url]); go(c, 3); S = os.path.join(HERE, "..", "unit", "aletheia_unit.py")
        ok = subprocess.run([sys.executable, "-I", S, "--verify", c["output"]], capture_output=True, text=True); self.assertEqual(ok.returncode, 0, ok.stderr)
        lines = open(c["output"]).read().splitlines(); r = json.loads(lines[1]); r["seq"] = 7; lines[1] = u.canonical(r); open(c["output"], "w").write("\n".join(lines) + "\n")
        self.assertEqual(subprocess.run([sys.executable, "-I", S, "--verify", c["output"]], capture_output=True, text=True).returncode, 1)
        self.assertEqual(subprocess.run([sys.executable, "-I", S, "--config", "/nope.json"], capture_output=True, text=True).returncode, 2)
if __name__ == "__main__": unittest.main()
