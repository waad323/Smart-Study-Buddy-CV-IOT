"""Eye Aspect Ratio (EAR) Mathematical Module.

Computes the Euclidean geometric ratio of the eye aperture using 2D/3D coordinates.
Formulation (Soukupova & Cech):
    EAR = (||p2 - p6|| + ||p3 - p5||) / (2.0 * ||p1 - p4||)
"""

import math
from typing import List, Sequence, Tuple

# MediaPipe FaceMesh Landmark Indices for Ocular Contours
# 6 landmarks per eye: [P1(outer), P2(upper-outer), P3(upper-inner), P4(inner), P5(lower-inner), P6(lower-outer)]
LEFT_EYE_LANDMARKS: List[int] = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS: List[int] = [362, 385, 387, 263, 373, 380]


def euclidean_distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    """Computes Euclidean 2D distance between two points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def calculate_ear(landmarks: Sequence[Sequence[float]], eye_indices: Sequence[int]) -> float:
    """Calculates the Eye Aspect Ratio (EAR) for a single eye given full facial landmarks.

    Args:
        landmarks: Complete list of (x, y) landmark coordinates.
        eye_indices: 6-element list of indices representing the eye contour.

    Returns:
        Float value representing the eye aspect ratio (typically 0.10 to 0.40).
    """
    if len(eye_indices) != 6:
        raise ValueError(f"Eye indices must contain exactly 6 points, got {len(eye_indices)}")

    try:
        pts = [landmarks[idx] for idx in eye_indices]
    except (IndexError, TypeError):
        return 0.0

    # Vertical eye distances
    dist_vertical_1 = euclidean_distance(pts[1], pts[5])  # ||P2 - P6||
    dist_vertical_2 = euclidean_distance(pts[2], pts[4])  # ||P3 - P5||

    # Horizontal eye distance
    dist_horizontal = euclidean_distance(pts[0], pts[3])  # ||P1 - P4||

    if dist_horizontal <= 1e-6:
        return 0.0

    ear = (dist_vertical_1 + dist_vertical_2) / (2.0 * dist_horizontal)
    return round(float(ear), 4)


def calculate_average_ear(
    landmarks: Sequence[Sequence[float]],
    left_indices: Sequence[int] = LEFT_EYE_LANDMARKS,
    right_indices: Sequence[int] = RIGHT_EYE_LANDMARKS,
) -> Tuple[float, float, float]:
    """Calculates EAR for both left and right eyes, and returns their mean.

    Returns:
        Tuple of (left_ear, right_ear, average_ear)
    """
    left_ear = calculate_ear(landmarks, left_indices)
    right_ear = calculate_ear(landmarks, right_indices)
    avg_ear = round((left_ear + right_ear) / 2.0, 4)
    return left_ear, right_ear, avg_ear


if __name__ == "__main__":
    # Test with synthetic open eye coordinates
    # P1: (0, 10), P2: (3, 15), P3: (7, 15), P4: (10, 10), P5: (7, 5), P6: (3, 5)
    sample_pts = [
        (0, 10), (3, 15), (7, 15), (10, 10), (7, 5), (3, 5)
    ]
    test_ear = calculate_ear(sample_pts, list(range(6)))
    print("Test EAR Calculation:", test_ear)
    assert 0.25 <= test_ear <= 1.5, "EAR should be a reasonable positive ratio"
