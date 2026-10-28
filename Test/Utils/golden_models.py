# ============================================================================
# File: Test/Utils/golden_models.py
# Description: 4x4 sample matrices for the GPU matmul check.
# ============================================================================

import numpy as np


def matrix_a():
    """Return the 4x4 uint8 sample for the left-hand matrix."""
    return np.array(
        [
            [1, 2, 0, 1],
            [0, 1, 1, 2],
            [2, 0, 1, 1],
            [1, 1, 2, 0],
        ],
        dtype=np.uint8,
    )


def matrix_b():
    """Return the 4x4 uint8 sample for the right-hand matrix."""
    return np.array(
        [
            [1, 0, 2, 1],
            [2, 1, 0, 1],
            [1, 2, 1, 0],
            [0, 1, 1, 2],
        ],
        dtype=np.uint8,
    )


def matrix_c():
    """Return C = A @ B as uint8, matching the GPU's 8-bit multiply and add."""
    product = matrix_a().astype(np.uint16) @ matrix_b().astype(np.uint16)
    if int(product.max()) > 255:
        raise ValueError("sample product does not fit in 8 bits")
    return product.astype(np.uint8)
