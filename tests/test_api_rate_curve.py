import unittest
from types import SimpleNamespace

from modes.api.block import _rate_curve


class TestRateCurve(unittest.TestCase):
    def test_the_rate_is_the_fee_total_over_the_stake_total(self):
        parent = SimpleNamespace(height=99, statistics=[(101, 100, 0, 0, 0, 0)])
        block = SimpleNamespace(height=100, previous_block=parent)
        self.assertEqual(_rate_curve(block), [{"duration": 0, "rate": 101 / 100}])


if __name__ == "__main__":
    unittest.main()
