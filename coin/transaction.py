import abc
import typing
from dataclasses import dataclass
from functools import cached_property
from coin.util import hash_byte_sets
from coin.node_context import NodeContext


@dataclass(frozen=True)
class TransactionOutpoint:
    previous_transaction_hash: bytes
    index: int

    @cached_property
    def hash_parts(self) -> typing.Tuple[bytes, ...]:
        return (
            self.previous_transaction_hash,
            self.index.to_bytes(32, byteorder='big'),
        )


@dataclass(frozen=True)
class TransactionInput:
    previous_transaction_outpoint: TransactionOutpoint
    signature: bytes

    @cached_property
    def hash_parts(self) -> typing.Tuple[bytes, ...]:
        return self.previous_transaction_outpoint.hash_parts + (self.signature,)


@dataclass(frozen=True)
class TransactionOutput:
    value: int
    recipient_public_key: bytes

    @cached_property
    def hash_parts(self) -> typing.Tuple[bytes, ...]:
        return (
            self.value.to_bytes(32, byteorder='big'),
            self.recipient_public_key,
        )


@dataclass(frozen=True)
class Transaction:
    inputs: typing.Tuple[TransactionInput]
    outputs: typing.Tuple[TransactionOutput]

    @property
    def is_coinbase(self) -> bool:
        return (
            len(self.inputs) == 1
            and self.inputs[0].previous_transaction_outpoint.previous_transaction_hash
            == b""
        )

    @cached_property
    def _inputs_hash_parts(self) -> typing.Tuple[bytes, ...]:
        return tuple(
            hash_part for input in self.inputs for hash_part in input.hash_parts
        )

    @cached_property
    def _outputs_hash_parts(self) -> typing.Tuple[bytes, ...]:
        return tuple(
            hash_part for output in self.outputs for hash_part in output.hash_parts
        )

    @cached_property
    def hash_for_signature(self) -> bytes:
        return hash_byte_sets(*self._outputs_hash_parts)

    def hash(self) -> bytes:
        return hash_byte_sets(*(self._inputs_hash_parts + self._outputs_hash_parts))


def make_reward_transaction(ctx: NodeContext) -> Transaction:
    return Transaction(
        inputs=(
            TransactionInput(
                previous_transaction_outpoint=TransactionOutpoint(
                    previous_transaction_hash=b"",
                    index=0,
                ),
                signature=b"",
            ),
        ),
        outputs=(
            TransactionOutput(
                value=1,
                recipient_public_key=ctx.node_key.public_key.to_string(),
            ),
        ),
    )
