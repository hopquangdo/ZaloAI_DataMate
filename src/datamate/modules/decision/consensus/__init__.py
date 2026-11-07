"""Bỏ phiếu giữa nhiều lần sinh / nhiều đường giải: chỉ trả lời khi đủ đồng thuận."""

from datamate.modules.decision.consensus.consensus import signature, vote
from datamate.modules.decision.consensus.settings import ConsensusSettings

__all__ = ["ConsensusSettings", "signature", "vote"]
