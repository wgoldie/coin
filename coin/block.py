import abc
import typing
from dataclasses import dataclass
from functools import cached_property
import hashlib
from coin.merkle import build_merkle_tree


@dataclass(frozen=True)
class BlockHeader:
    transaction_tree_hash: bytes
    previous_block_hash: bytes


class OpenBlockHeader(BlockHeader):
    hasher: typing.Optional["hashlib._Hash"] = None

    def hash(self, nonce: int) -> bytes:
        if self.hasher is None:
            self.hasher = hashlib.sha256()
            self.hasher.update(self.transaction_tree_hash)
            self.hasher.update(self.previous_block_hash)
        hasher = self.hasher.copy()
        hasher.update(bytes(nonce))
        return hasher.digest()


@dataclass(frozen=True)
class SealedBlockHeader(BlockHeader):
    nonce: int
    block_hash: bytes
