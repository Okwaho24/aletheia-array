import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import gate4_lite_evm as g
TX = {"hash": "0x" + "a" * 64, "from": "0x" + "b" * 40}
def fake(chain=1, height=1000, age=5, txs=True, peer_height=None):
    def rpc(url, method, params):
        if "dead" in url: return None, "URLError"
        if method == "eth_chainId": return hex(chain), None
        if method == "eth_blockNumber": return hex(peer_height if (peer_height is not None and "peer" in url) else height), None
        if method == "eth_getBlockByNumber": return {"timestamp": hex(NOW - age), "transactions": [TX] if txs else []}, None
    return rpc
NOW = 10_000_000
class T(unittest.TestCase):
    def v(self, urls, **k):
        return g.verify_chain(1, urls, fake(**k), NOW, 3600, 1000)
    def test_pass(self): self.assertEqual(self.v(["https://a.x", "https://peer.y"])["verdict"], "PASS")
    def test_wrong_chain(self): self.assertTrue(self.v(["https://a.x"], chain=2)["verdict"].startswith("FAIL:chainid-mismatch"))
    def test_stale(self): self.assertTrue(self.v(["https://a.x"], age=99999)["verdict"].startswith("FAIL:stale"))
    def test_no_tx_partial(self):
        r = self.v(["https://a.x", "https://peer.y"], txs=False); self.assertEqual(r["verdict"], "PARTIAL"); self.assertIn("tx-parse", r["reason"])
    def test_single_endpoint_partial(self):
        r = self.v(["https://a.x"]); self.assertEqual(r["verdict"], "PARTIAL"); self.assertIn("cross-check", r["reason"])
    def test_peer_height_off(self): self.assertEqual(self.v(["https://a.x", "https://peer.y"], peer_height=5000)["verdict"], "PARTIAL")
    def test_unreachable(self): self.assertTrue(self.v(["https://dead.x"])["verdict"].startswith("FAIL:no-handshake"))
    def test_no_endpoint(self): self.assertEqual(self.v([])["verdict"], "NO_ENDPOINT")
    def test_fallback_to_second_url(self): self.assertEqual(self.v(["https://dead.x", "https://a.x", "https://peer.y"])["verdict"], "PASS")
    def test_usable_filters_key_placeholders(self):
        self.assertEqual(g.usable(["https://a", "http://b", "https://c/${KEY}", "wss://d"]), ["https://a"])
    def test_usable_rejects_credentialed_urls(self):
        self.assertEqual(g.usable(["https://user:pw@host.example/rpc", "https://ok.example"]), ["https://ok.example"])
    def test_malformed_http_is_not_a_crash(self):
        import http.client, urllib.request
        orig = urllib.request.urlopen
        def boom(*a, **k): raise http.client.BadStatusLine("junk")
        urllib.request.urlopen = boom
        try: self.assertEqual(g.http_rpc("https://x.example", "eth_chainId", [])[0], None)
        finally: urllib.request.urlopen = orig
if __name__ == "__main__": unittest.main()
