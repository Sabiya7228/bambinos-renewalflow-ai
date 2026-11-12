import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reconcile import norm, clean_amount, is_paid

class EngineTests(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(norm("Payment Status"), "payment_status")
    def test_amount(self):
        self.assertEqual(clean_amount("₹1,250.00"), 1250.00)
    def test_paid_status(self):
        self.assertTrue(is_paid("SUCCESS", ["paid", "success"]))
        self.assertFalse(is_paid("pending", ["paid", "success"]))

if __name__ == "__main__":
    unittest.main()
