import csv, hashlib, json, os, sqlite3, subprocess, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); BIND = os.path.join(HERE, "..", "factory", "bind_units.py")
CAT = [["evm__Eth", "evm", "Ethereum Mainnet", "1", "mainnet"], ["evm__Sep", "evm", "Sepolia", "11155111", "testnet"],
       ["evm__Dead", "evm", "Dead Chain", "99", "mainnet"], ["evm__Part", "evm", "Partial Chain", "98", "mainnet"],
       ["sol__Main", "solana", "Solana Mainnet Beta", "mainnet-beta", "mainnet"]]
G4 = [["evm__Eth", "PASS", "https://rpc.one"], ["evm__Sep", "PASS", "https://rpc.sep"], ["evm__Dead", "FAIL:no-handshake", ""], ["evm__Part", "PARTIAL", "https://rpc.part"]]
class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); p = self.d.name
        with open(f"{p}/cat.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["DeviceID", "Family", "ChainName", "ChainId", "Network"]); w.writerows(CAT)
        with open(f"{p}/g4.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["DeviceID", "Verdict", "Endpoint"]); w.writerows(G4)
        json.dump([{"chainId": 1, "rpc": ["https://rpc.one", "https://rpc.two", "https://key.example/${KEY}", "http://insecure", "https://rpc.three"]}], open(f"{p}/chains.json", "w"))
    def tearDown(self): self.d.cleanup()
    def bind(self, dev, *extra, buyer="ORDER-1"):
        p = self.d.name
        return subprocess.run([sys.executable, "-I", BIND, "--device", dev, "--buyer-ref", buyer, "--catalogue", f"{p}/cat.csv", "--gate4", f"{p}/g4.csv",
                               "--ledger", f"{p}/l.sqlite", "--out", f"{p}/out", *extra], capture_output=True, text=True)
    def rows(self):
        p = f"{self.d.name}/l.sqlite"; return sqlite3.connect(p).execute("select device_id from allocations").fetchall() if os.path.exists(p) else []
    def test_success_builds_valid_package(self):
        r = self.bind("evm__Eth", "--chains-file", f"{self.d.name}/chains.json", "--watch", "0x" + "a" * 40); self.assertEqual(r.returncode, 0, r.stderr)
        pk = f"{self.d.name}/out/evm__Eth"; cfg = json.load(open(f"{pk}/unit-config.json"))
        self.assertEqual(cfg["endpoints"], ["https://rpc.one", "https://rpc.two", "https://rpc.three"]); self.assertEqual(cfg["chain_id"], 1)
        chk = subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=pk, capture_output=True, text=True); self.assertEqual(chk.returncode, 0, chk.stdout)
        sys.path.insert(0, os.path.join(HERE, "..", "unit")); import aletheia_unit as u; u.load_config(f"{pk}/unit-config.json")
        self.assertEqual(self.rows(), [("evm__Eth",)])
    def test_second_allocation_refused(self):
        self.assertEqual(self.bind("evm__Eth").returncode, 0); r = self.bind("evm__Eth", buyer="ORDER-2")
        self.assertEqual(r.returncode, 1); self.assertIn("already allocated", r.stderr); self.assertEqual(len(self.rows()), 1)
    def test_ledger_blocks_even_if_package_dir_removed(self):
        self.bind("evm__Eth"); import shutil; shutil.rmtree(f"{self.d.name}/out/evm__Eth")
        self.assertEqual(self.bind("evm__Eth").returncode, 1)
    def test_refusals_allocate_nothing(self):
        for dev, why in (("evm__Sep", "not mainnet"), ("evm__Dead", "FAIL"), ("sol__Main", "EVM only"), ("evm__Nope", "not in the catalogue"), ("evm__Part", "PARTIAL")):
            r = self.bind(dev); self.assertEqual(r.returncode, 1, dev); self.assertIn(why, r.stderr)
        self.assertEqual(self.rows(), [])
    def test_partial_allowed_with_flag(self): self.assertEqual(self.bind("evm__Part", "--allow-partial").returncode, 0)
    def test_missing_input_is_usage_error(self):
        r = subprocess.run([sys.executable, "-I", BIND, "--device", "x", "--buyer-ref", "y", "--catalogue", "/nope", "--gate4", "/nope", "--ledger", "/tmp/l", "--out", "/tmp/o"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
if __name__ == "__main__": unittest.main()
