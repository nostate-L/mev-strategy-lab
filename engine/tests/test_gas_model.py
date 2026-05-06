"""Tests for EIP-1559 base-fee dynamics."""

from __future__ import annotations

from mevlab.core.gas import GasModel, PriorityFeeQuote


def test_base_fee_constant_when_at_target():
    gm = GasModel()
    assert gm.next_base_fee(20_000_000_000, gm.target_gas_used) == 20_000_000_000


def test_base_fee_rises_when_block_full():
    gm = GasModel()
    parent_full = gm.target_gas_used * 2  # 30M / 15M target
    new_fee = gm.next_base_fee(20_000_000_000, parent_full)
    # Max change is 12.5% per block.
    assert new_fee > 20_000_000_000
    assert new_fee <= int(20_000_000_000 * 1.125) + 5


def test_base_fee_falls_when_block_empty():
    gm = GasModel()
    new_fee = gm.next_base_fee(20_000_000_000, 0)
    assert new_fee < 20_000_000_000
    assert new_fee >= int(20_000_000_000 * 0.875) - 5


def test_base_fee_floor():
    gm = GasModel()
    new_fee = gm.next_base_fee(7, 0)
    assert new_fee >= gm.minimum_base_fee


def test_priority_fee_quote_interpolates():
    q = PriorityFeeQuote(median_priority_fee=10**9, p95_priority_fee=10**10)
    assert q.quote(0.5) == 10**9
    assert q.quote(0.95) == 10**10
    middle = q.quote(0.75)
    assert 10**9 < middle < 10**10
