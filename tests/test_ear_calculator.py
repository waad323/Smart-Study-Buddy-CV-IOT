"""Unit tests for Eye Aspect Ratio (EAR) mathematical calculations."""

import unittest
from src.vision.ear_calculator import calculate_average_ear, calculate_ear, euclidean_distance


class TestEARCalculator(unittest.TestCase):

    def test_euclidean_distance(self):
        p1 = (0.0, 0.0)
        p2 = (3.0, 4.0)
        dist = euclidean_distance(p1, p2)
        self.assertAlmostEqual(dist, 5.0)

    def test_calculate_ear_open_eye(self):
        # Open eye geometry: vertical opening is wide (~10 units), horizontal length is 20 units
        open_eye_pts = [
            (0.0, 10.0),    # P1 (outer corner)
            (6.0, 16.0),    # P2 (upper outer)
            (14.0, 16.0),   # P3 (upper inner)
            (20.0, 10.0),   # P4 (inner corner)
            (14.0, 4.0),    # P5 (lower inner)
            (6.0, 4.0),     # P6 (lower outer)
        ]
        ear = calculate_ear(open_eye_pts, list(range(6)))
        # dist(P2, P6) = 12.0, dist(P3, P5) = 12.0, dist(P1, P4) = 20.0
        # EAR = (12 + 12) / (2 * 20) = 24 / 40 = 0.60
        self.assertAlmostEqual(ear, 0.60, places=2)

    def test_calculate_ear_closed_eye(self):
        # Closed eye geometry: vertical aperture is near 0 (~1.5 units)
        closed_eye_pts = [
            (0.0, 10.0),
            (6.0, 10.5),
            (14.0, 10.5),
            (20.0, 10.0),
            (14.0, 9.5),
            (6.0, 9.5),
        ]
        ear = calculate_ear(closed_eye_pts, list(range(6)))
        # dist(P2, P6) = 1.0, dist(P3, P5) = 1.0, dist(P1, P4) = 20.0
        # EAR = (1 + 1) / 40 = 0.05
        self.assertAlmostEqual(ear, 0.05, places=2)
        self.assertLess(ear, 0.15)

    def test_zero_division_guard(self):
        # P1 and P4 identical
        collapsed_pts = [(5.0, 5.0)] * 6
        ear = calculate_ear(collapsed_pts, list(range(6)))
        self.assertEqual(ear, 0.0)

    def test_invalid_indices_length(self):
        with self.assertRaises(ValueError):
            calculate_ear([(0, 0)] * 5, [0, 1, 2, 3, 4])


if __name__ == '__main__':
    unittest.main()
