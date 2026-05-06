"""Tests for ``mevlab.core.numeric``."""

from __future__ import annotations

import math

import pytest

from mevlab.core.numeric import (
    MAX_UINT256,
    Q96,
    fix_q96_to_float,
    float_to_q96,
    isqrt256,
    mul_div,
    mul_div_round_up,
)


def test_mul_div_basic():
    assert mul_div(6, 7, 3) == 14
    assert mul_div(0, 1, 1) == 0
    assert mul_div(1, 1, 2) == 0  # truncation


def test_mul_div_round_up_only_rounds_when_remainder():
    assert mul_div_round_up(6, 7, 3) == 14
    assert mul_div_round_up(1, 1, 2) == 1
    assert mul_div_round_up(7, 7, 7) == 7  # exact


def test_mul_div_zero_denominator():
    with pytest.raises(ZeroDivisionError):
        mul_div(1, 1, 0)


def test_mul_div_handles_huge_uint256():
    # Inputs at the upper end of uint256 must not overflow Python ints.
    assert mul_div(MAX_UINT256, MAX_UINT256, MAX_UINT256) == MAX_UINT256


def test_isqrt256_matches_math_isqrt():
    for v in [0, 1, 4, 9, 10, 999_983, 10**40, 2**255]:
        assert isqrt256(v) == math.isqrt(v)


def test_isqrt256_overflow():
    with pytest.raises(OverflowError):
        isqrt256(MAX_UINT256 + 1)


def test_q96_round_trip():
    p = 1234.567890
    q = float_to_q96(p)
    p2 = fix_q96_to_float(q)
    assert abs(p2 - p) < 1e-10
    assert q == int(p * Q96)
