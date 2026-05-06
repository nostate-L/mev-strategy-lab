"""Core domain types used across the engine.

Everything here is intentionally simple: dataclasses + enums, no SQLAlchemy or
pydantic dependencies inside the hot path. Higher-level services (API, persistence)
adapt these types into their own ORM/schema models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

Address = str  # 0x-prefixed hex, lowercased
Hash = str  # 0x-prefixed hex, lowercased
Wei = int


class TxStatus(StrEnum):
    """Possible final statuses of a simulated transaction."""

    SUCCESS = "success"
    REVERTED = "reverted"
    DROPPED = "dropped"  # not included in block (out of gas, low fee)
    FRONTRUN = "frontrun"  # included but slippage failed because of MEV reorder


class SwapDirection(StrEnum):
    """Token swap direction relative to a pool's canonical (token0, token1) order."""

    ZERO_FOR_ONE = "0->1"
    ONE_FOR_ZERO = "1->0"


@dataclass(frozen=True, slots=True)
class Token:
    """Minimal token descriptor used by the simulation engine."""

    address: Address
    symbol: str
    decimals: int = 18

    @property
    def unit(self) -> int:
        """One whole token in base units (wei-equivalent)."""
        return 10**self.decimals


@dataclass(frozen=True, slots=True)
class PendingTx:
    """A transaction sitting in the mempool, awaiting inclusion."""

    hash: Hash
    sender: Address
    target: Address
    value: Wei
    calldata: bytes
    gas_limit: int
    max_fee_per_gas: Wei
    max_priority_fee_per_gas: Wei
    nonce: int
    seen_at_ms: int
    # Decoded intent (optional). Strategies use these hints to recognise victim
    # swaps without running an EVM. ``intent`` is a dict like
    # ``{"kind":"swap","pool":"0x..","dir":"0->1","amount_in":1234,"min_out":...}``.
    intent: dict[str, Any] | None = None

    @property
    def effective_priority_fee(self) -> Wei:
        """Approximation: assume base_fee == 0 cap so priority == max_priority_fee."""
        return self.max_priority_fee_per_gas


@dataclass(frozen=True, slots=True)
class BlockHeader:
    """Block-level data the simulator needs."""

    number: int
    timestamp: int
    base_fee_per_gas: Wei
    gas_limit: int
    parent_hash: Hash = "0x" + "0" * 64


@dataclass(slots=True)
class ExecutionResult:
    """Result of executing one transaction inside a simulated block."""

    tx_hash: Hash
    status: TxStatus
    gas_used: int
    gas_price: Wei
    logs: list[dict[str, Any]] = field(default_factory=list)
    return_data: bytes | None = None
    revert_reason: str | None = None
    profit_wei: int = 0  # signed; only relevant for searcher-owned transactions


@dataclass(slots=True)
class Block:
    """A simulated block: header + ordered list of executed transactions."""

    header: BlockHeader
    results: list[ExecutionResult] = field(default_factory=list)
    builder_revenue_wei: int = 0
    coinbase_payment_wei: int = 0  # direct ``block.coinbase.transfer(...)`` payments

    @property
    def total_gas_used(self) -> int:
        return sum(r.gas_used for r in self.results)

    @property
    def fees_paid_wei(self) -> int:
        return sum(r.gas_used * r.gas_price for r in self.results)


@dataclass(slots=True)
class MempoolSnapshot:
    """A snapshot of the mempool at a particular wall-clock instant."""

    captured_at_ms: int
    pending: list[PendingTx]
    base_fee_per_gas_next: Wei
    block_number_next: int

    def by_sender(self, sender: Address) -> list[PendingTx]:
        return [t for t in self.pending if t.sender == sender]

    def __len__(self) -> int:  # pragma: no cover - convenience
        return len(self.pending)
