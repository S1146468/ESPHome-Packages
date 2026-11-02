import math
import unittest
from score_recorded import score


class ScoresTest(unittest.TestCase):
    def test_signed_errors(self):
        result = score([-2, 1, 1])
        self.assertEqual(result['bias'], 0)
        self.assertAlmostEqual(result['mae'], 4/3)
        self.assertAlmostEqual(result['rmse'], math.sqrt(2))
        self.assertEqual(result['n'], 3)

    def test_empty_is_not_perfect_accuracy(self):
        self.assertEqual(score([]), {'n': 0})


if __name__ == '__main__':
    unittest.main()
