from dataclasses import dataclass
from coin.util import FrozenDict
from coin.block import SealedBlock
import typing


@dataclass(frozen=True)
class Ledger:
    balances: FrozenDict[bytes, int]


def validate_block(block: SealedBlock) -> None:
    pass
