import unittest
from fractions import Fraction

from bsc_audit.exact import Matrix, rational


class ExactMatrixTests(unittest.TestCase):
    def test_float_rejected(self):
        with self.assertRaises(TypeError):
            rational(0.5)

    def test_rank_and_product(self):
        matrix = Matrix.from_nested([[1, "1/2"], [2, 1]])
        self.assertEqual(matrix.rank(), 1)
        self.assertEqual((matrix @ Matrix.identity(2)).rows, matrix.rows)

    def test_empty_matrix_shape(self):
        self.assertEqual(Matrix.zero(0, 3).shape, (0, 3))

    def test_resource_limits_fail_closed(self):
        with self.assertRaises(ValueError):
            Matrix.zero(129, 1)
        with self.assertRaises(ValueError):
            rational("1" * 257)
        with self.assertRaises(ValueError):
            rational("0.5")


if __name__ == "__main__":
    unittest.main()
