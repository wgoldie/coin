import abc
import typing
from dataclasses import dataclass
from functools import cached_property
from coin.util import hash_byte_sets


@dataclass(frozen=True)
class Transaction:
    recipient_public_key: bytes
    previous_transaction: bytes

    def compute_hash_for_signature(self) -> bytes:
        return hash_byte_sets(self.recipient_public_key, self.previous_transaction)


@dataclass(frozen=True)
class SignedTransaction(Transaction):
    hash_for_signature: bytes
    signature: bytes

    @cached_property
    def hash(self) -> bytes:
        return hash_byte_sets(
            self.recipient_public_key,
            self.previous_transaction,
            self.hash_for_signature,
            self.signature,
        )
