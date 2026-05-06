"""Synthetic mempool traffic generator.

This is the most useful primitive for unit tests and reproducible benchmarks:
it lets us drive the simulator with thousands of swap-shaped transactions
without depending on a chain RPC or recorded data.

The traffic model is intentionally simple but lifelike:
    - Inter-arrival times are exponentially distributed (Poisson process).
    - Swap sizes follow a log-normal distribution (heavy tail).
    - Priority fees are drawn from a mixture of two exponentials (regular vs
      MEV searchers willing to pay much more).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from mevlab.core.types import MempoolSnapshot, PendingTx
from mevlab.pools.base import BasePool


@dataclass(slots=True, frozen=True)
class TrafficProfile:
    """High-level knobs for synthetic mempool generation."""

    avg_swaps_per_block: float = 30.0
    swap_size_log_mean: float = 16.0  # ~ln(8.9M wei) ≈ small swap
    swap_size_log_std: float = 1.5
    base_priority_fee_wei: int = 1_000_000_000  # 1 gwei
    searcher_fraction: float = 0.05
    searcher_priority_multiplier: float = 25.0
    swap_gas_limit: int = 200_000


class SyntheticMempoolGenerator:
    """Generate sequences of :class:`MempoolSnapshot`."""

    def __init__(
        self,
        pools: list[BasePool],
        profile: TrafficProfile | None = None,
        *,
        seed: int | None = None,
    ) -> None:
        if not pools:
            raise ValueError("at least one pool is required")
        self.pools = pools
        self.profile = profile or TrafficProfile()
        self.rng = random.Random(seed)
        self._tx_counter = 0
        self._sender_counter = 0

    # ------------------------------------------------------------ helpers

    def _new_address(self, prefix: str) -> str:
        self._sender_counter += 1
        return f"0x{prefix}{self._sender_counter:040x}"[:42]

    def _new_tx_hash(self) -> str:
        self._tx_counter += 1
        return "0x" + f"{self._tx_counter:064x}"

    def _draw_swap_size(self) -> int:
        # log-normal in raw token base units
        log_amount = self.rng.gauss(self.profile.swap_size_log_mean, self.profile.swap_size_log_std)
        return max(1, int(2.71828 ** min(log_amount, 50)))

    def _draw_priority_fee(self) -> int:
        if self.rng.random() < self.profile.searcher_fraction:
            return int(
                self.profile.base_priority_fee_wei
                * self.profile.searcher_priority_multiplier
                * (1 + self.rng.expovariate(1.0))
            )
        return int(self.profile.base_priority_fee_wei * (0.5 + self.rng.expovariate(1.0)))

    # ------------------------------------------------------------ public

    def generate_snapshot(
        self,
        *,
        block_number_next: int,
        base_fee_per_gas_next: int,
        captured_at_ms: int,
    ) -> MempoolSnapshot:
        """Generate one snapshot."""
        n = max(1, int(self.rng.expovariate(1 / self.profile.avg_swaps_per_block)))
        pending: list[PendingTx] = []
        for _ in range(n):
            pool = self.rng.choice(self.pools)
            direction = self.rng.choice(["0->1", "1->0"])
            amount = self._draw_swap_size()
            tip = self._draw_priority_fee()
            sender = self._new_address("a")
            tx = PendingTx(
                hash=self._new_tx_hash(),
                sender=sender,
                target=pool.address,
                value=0,
                calldata=b"",
                gas_limit=self.profile.swap_gas_limit,
                max_fee_per_gas=base_fee_per_gas_next + tip,
                max_priority_fee_per_gas=tip,
                nonce=0,
                seen_at_ms=captured_at_ms - self.rng.randint(0, 1500),
                intent={
                    "kind": "swap",
                    "pool": pool.address,
                    "dir": direction,
                    "amount_in": amount,
                    "min_out": 0,
                },
            )
            pending.append(tx)

        return MempoolSnapshot(
            captured_at_ms=captured_at_ms,
            pending=pending,
            base_fee_per_gas_next=base_fee_per_gas_next,
            block_number_next=block_number_next,
        )

    def stream(
        self,
        *,
        starting_block: int = 1,
        starting_base_fee: int = 20_000_000_000,
        starting_time_ms: int = 0,
        block_time_ms: int = 12_000,
        n_blocks: int = 100,
    ) -> list[MempoolSnapshot]:
        """Generate a sequence of ``n_blocks`` snapshots."""
        out: list[MempoolSnapshot] = []
        base_fee = starting_base_fee
        for i in range(n_blocks):
            snap = self.generate_snapshot(
                block_number_next=starting_block + i,
                base_fee_per_gas_next=base_fee,
                captured_at_ms=starting_time_ms + i * block_time_ms,
            )
            out.append(snap)
            # Random walk on base fee in [-12.5%, +12.5%].
            delta = self.rng.uniform(-0.125, 0.125)
            base_fee = max(7, int(base_fee * (1 + delta)))
        return out


__all__ = ["SyntheticMempoolGenerator", "TrafficProfile"]
