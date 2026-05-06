"""Gas pricing model.

Implements EIP-1559 base-fee dynamics and a simple priority-fee auction.
We don't model the elasticity-multiplier per-network exactly; we expose the
constants so callers can configure them per chain (mainnet vs L2s).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GasModel:
    """EIP-1559 parameters used to roll the base fee forward."""

    target_gas_used: int = 15_000_000  # 15M target on mainnet (30M cap)
    max_change_denominator: int = 8  # 12.5% per-block ceiling
    minimum_base_fee: int = 7  # wei

    def next_base_fee(self, parent_base_fee: int, parent_gas_used: int) -> int:
        """Compute the base fee of the next block from the parent stats.

        Mirrors the formula from EIP-1559 §"Base Fee Calculation".
        """
        if parent_gas_used == self.target_gas_used:
            return parent_base_fee

        if parent_gas_used > self.target_gas_used:
            delta = parent_gas_used - self.target_gas_used
            base_fee_delta = max(
                parent_base_fee * delta // self.target_gas_used // self.max_change_denominator,
                1,
            )
            return parent_base_fee + base_fee_delta

        delta = self.target_gas_used - parent_gas_used
        base_fee_delta = (
            parent_base_fee * delta // self.target_gas_used // self.max_change_denominator
        )
        return max(self.minimum_base_fee, parent_base_fee - base_fee_delta)


@dataclass(frozen=True, slots=True)
class PriorityFeeQuote:
    """Recommendation for a priority (tip) fee given recent inclusion stats.

    The model assumes an exponential CDF of priority fees in recent blocks and
    inverts it for the requested ``confidence`` (0..1). Real production code
    would maintain a histogram per recent block; here we work from precomputed
    summary stats so callers can plug in any data source.
    """

    median_priority_fee: int
    p95_priority_fee: int

    def quote(self, confidence: float) -> int:
        """Quote a tip in wei for a desired inclusion confidence."""
        if not 0 < confidence < 1:
            raise ValueError("confidence must be strictly between 0 and 1")
        # Linear interpolation between median (~50%) and p95.
        if confidence <= 0.5:
            return self.median_priority_fee
        if confidence >= 0.95:
            return self.p95_priority_fee
        slope = (self.p95_priority_fee - self.median_priority_fee) / (0.95 - 0.5)
        tip = self.median_priority_fee + slope * (confidence - 0.5)
        return int(tip)


__all__ = ["GasModel", "PriorityFeeQuote"]
