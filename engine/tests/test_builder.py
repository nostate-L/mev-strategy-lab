"""Tests for the block builder."""

from __future__ import annotations

from mevlab.builder.auction import BlockSpaceAuction
from mevlab.builder.builder import Bundle, FlashbotsLikeBuilder
from mevlab.core.types import BlockHeader, PendingTx


def _tx(h: str, tip: int, max_fee: int, gas_limit: int = 21_000) -> PendingTx:
    return PendingTx(
        hash=h,
        sender="0x0",
        target="0x1",
        value=0,
        calldata=b"",
        gas_limit=gas_limit,
        max_fee_per_gas=max_fee,
        max_priority_fee_per_gas=tip,
        nonce=0,
        seen_at_ms=0,
    )


def test_builder_prefers_high_revenue_bundle():
    builder = FlashbotsLikeBuilder()
    builder.submit_bundle(
        Bundle(
            transactions=[_tx("0xa", tip=1, max_fee=2)],
            coinbase_payment_wei=10**18,  # 1 ETH bribe
            label="bribe",
            expected_gas_used=21_000,
        )
    )
    builder.submit_bundle(
        Bundle(
            transactions=[_tx("0xb", tip=1, max_fee=2)],
            coinbase_payment_wei=10**16,  # 0.01 ETH bribe
            label="cheap",
            expected_gas_used=21_000,
        )
    )
    block, _ = builder.build(
        BlockHeader(number=1, timestamp=0, base_fee_per_gas=10, gas_limit=10_000_000)
    )
    # The big-bribe bundle's tx must come first.
    assert block.results[0].tx_hash == "0xa"


def test_auction_clears_at_runner_up():
    a = Bundle(
        transactions=[_tx("0xa", 1, 2)],
        coinbase_payment_wei=10**18,
        expected_gas_used=21_000,
    )
    b = Bundle(
        transactions=[_tx("0xb", 1, 2)],
        coinbase_payment_wei=5 * 10**17,
        expected_gas_used=21_000,
    )
    auction = BlockSpaceAuction(base_fee_per_gas_next=10)
    result = auction.settle([a, b])
    assert result.winner is a
    assert result.runner_up is b
    assert result.clearing_price_wei > 0


def test_builder_drops_tx_if_no_gas_left():
    builder = FlashbotsLikeBuilder(block_gas_limit=21_000)
    builder.submit_public(_tx("0xa", tip=10, max_fee=20))
    builder.submit_public(_tx("0xb", tip=11, max_fee=21))
    block, dropped = builder.build(
        BlockHeader(number=1, timestamp=0, base_fee_per_gas=5, gas_limit=21_000)
    )
    assert len(block.results) == 1
    assert len(dropped) == 1
