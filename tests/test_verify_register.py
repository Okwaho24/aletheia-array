import csv, os, subprocess, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "verify_register.py")
HDR = ["DeviceID", "Family", "ChainName", "ChainId", "Network"]

def run(rows, *args, header=HDR):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "c.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
        return subprocess.run([sys.executable, "-I", SCRIPT, p, *args], capture_output=True, text=True)

class T(unittest.TestCase):
    def test_ok_and_expect_match(self):
        r = run([["a", "evm", "Ethereum Mainnet", "1", "mainnet"], ["b", "evm", "Sepolia", "11155111", "testnet"]],
                "--expect", "2,1,1,0,1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr); self.assertIn("MATCH", r.stdout)
    def test_expect_mismatch_fails(self):
        r = run([["a", "evm", "Ethereum Mainnet", "1", "mainnet"]], "--expect", "2,1,0,0,1")
        self.assertEqual(r.returncode, 1)
    def test_duplicate_id_fails(self):
        r = run([["a", "evm", "X", "1", "mainnet"], ["a", "evm", "Y", "2", "mainnet"]])
        self.assertEqual(r.returncode, 1); self.assertIn("duplicate", r.stdout)
    def test_empty_id_fails(self):
        self.assertEqual(run([["", "evm", "X", "1", "mainnet"]]).returncode, 1)
    def test_unknown_network_fails(self):
        self.assertEqual(run([["a", "evm", "X", "1", "devnet"]]).returncode, 1)
    def test_missing_column_is_usage_error(self):
        r = run([["a", "evm", "X", "1"]], header=HDR[:4]); self.assertEqual(r.returncode, 2)
    def test_missing_file(self):
        r = subprocess.run([sys.executable, "-I", SCRIPT, "/nonexistent.csv"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
    def test_suspect_flagging(self):
        r = run([["a", "evm", "Kiln", "1", "mainnet"], ["b", "solana", "Solana Mainnet Beta", "2", "mainnet"],
                 ["c", "evm", "Ethereum Mainnet", "3", "mainnet"]])
        self.assertIn("strong=1 weak=1", r.stdout)
    def test_bad_expect_arg(self):
        self.assertEqual(run([["a", "evm", "X", "1", "mainnet"]], "--expect", "1,2").returncode, 2)

REAL = os.environ.get("ALETHEIA_CATALOGUE")
@unittest.skipUnless(REAL and os.path.exists(REAL), "set ALETHEIA_CATALOGUE to run")
class Real(unittest.TestCase):
    def test_published_headline(self):
        r = subprocess.run([sys.executable, "-I", SCRIPT, REAL, "--expect", "1695,1598,93,4,23"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

if __name__ == "__main__":
    unittest.main()
