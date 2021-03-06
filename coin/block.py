import typing
from dataclasses import dataclass
from coin.transaction import Transaction
from coin.merkle import MerkleNode
import hashlib


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
        hasher.update(nonce.to_bytes(32, byteorder="big"))
        return hasher.digest()


@dataclass(frozen=True)
class Block:
    transaction_tree: MerkleNode[Transaction]


@dataclass(frozen=True)
class OpenBlock(Block):
    header: OpenBlockHeader


@dataclass(frozen=True)
class SealedBlockHeader(BlockHeader):
    nonce: int
    block_hash: bytes


@dataclass(frozen=True)
class SealedBlock(Block):
    header: SealedBlockHeader

    def validate_hashes(self) -> bool:
        if not self.transaction_tree.node_hash() == self.header.transaction_tree_hash:
            return False
        open_header = OpenBlockHeader(
            transaction_tree_hash=self.header.transaction_tree_hash,
            previous_block_hash=self.header.previous_block_hash,
        )
        if open_header.hash(nonce=self.header.nonce) == self.header.block_hash:
            return True
        else:
            return False

    def __repr__(self) -> str:
        return f"SealedBlock(block_hash={self.header.block_hash.hex()}, ...)"
