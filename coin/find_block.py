import abc
import typing
from dataclasses import dataclass
from functools import cached_property
import hashlib
from pprint import pprint
from coin.merkle import build_merkle_tree
from coin.block import OpenBlockHeader, SealedBlockHeader
from coin.transaction import SignedTransaction


def find_block(
    open_block_header: OpenBlockHeader,
    difficulty: int,
    *,
    # reporting_interval: int = 100,
    max_tries: int = int(1e10),
) -> SealedBlockHeader:
    if difficulty < 1:
        raise ValueError("Invalid difficulty", 0)
    target = b"0" * difficulty
    print("target", target)
    for nonce in range(max_tries):
        block_hash = open_block_header.hash(nonce)
        if block_hash.startswith(target):
            return SealedBlockHeader(
                transaction_tree_hash=open_block_header.transaction_tree_hash,
                previous_block_hash=open_block_header.previous_block_hash,
                nonce=nonce,
                block_hash=block_hash,
            )
    raise RuntimeError("Failed to find block")


def test_merkle() -> None:
    for i in (3, 4, 5, 10):
        print(i)
        transactions = [
            SignedTransaction(
                recipient_public_key=bytes(key),
                previous_transaction=b"",
                signature=b"",
                hash_for_signature=b"",
            )
            for j, key in enumerate(b"abcdefghijklmnopqrstuvwxyz")
            if j <= i
        ]
        tree = build_merkle_tree(transactions)
        print(tree)


if __name__ == "__main__":
    transactions = [
        SignedTransaction(
            recipient_public_key=bytes(key),
            previous_transaction=b"",
            signature=b"",
            hash_for_signature=b"",
        )
        for j, key in enumerate(b"abcdefghijklmnopqrstuvwxyz")
    ]
    tree = build_merkle_tree(transactions)
    assert tree is not None
    for difficulty in range(1, 5):
        print(f"difficulty = {difficulty}")
        open_block_header = OpenBlockHeader(
            transaction_tree_hash=tree.node_hash, previous_block_hash=b""
        )
        block = find_block(open_block_header, difficulty=difficulty)
        print(f"found {block}")
