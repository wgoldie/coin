from __future__ import annotations
from dataclasses import dataclass, field
from coin.util import FrozenDict
from coin.merkle import dfs, LeafMerkleNode
from coin.block import SealedBlock
from coin.transaction import Transaction
from coin.node_context import NodeContext
from ecdsa import VerifyingKey
import typing


@dataclass(frozen=True)
class Ledger:
    balances: FrozenDict[bytes, int] = field(default_factory=lambda: FrozenDict())
    previous_transactions: FrozenDict[bytes, Transaction] = field(
        default_factory=lambda: FrozenDict()
    )

    def copy(self) -> Ledger:
        return Ledger(
            balances=FrozenDict(self.balances),
            previous_transactions=FrozenDict(self.previous_transactions),
        )


@dataclass(frozen=True)
class SuccessfulValidateResult:
    new_ledger: Ledger
    valid: typing.Literal[True] = True


@dataclass(frozen=True)
class FailedValidateResult:
    message: str
    valid: typing.Literal[False] = False


ValidateResult = typing.Union[SuccessfulValidateResult, FailedValidateResult]

BLOCK_REWARD = 25


def update_ledger(
    starting_ledger: Ledger,
    transaction: Transaction,
) -> ValidateResult:

    total_available = 0
    keys_to_drain = []
    if transaction.is_coinbase:
        total_available = BLOCK_REWARD
    else:
        for transaction_input in transaction.inputs:
            previous_hash = (
                transaction_input.previous_transaction_outpoint.previous_transaction_hash
            )
            if previous_hash not in starting_ledger.previous_transactions:
                return FailedValidateResult(message="Unknown previous hash")
            previous_transaction = starting_ledger.previous_transactions[previous_hash]
            previous_outpoint = previous_transaction.outputs[
                transaction_input.previous_transaction_outpoint.index
            ]
            pubkey = previous_outpoint.recipient_public_key
            total_available += starting_ledger.balances[pubkey]
            if pubkey not in keys_to_drain:
                keys_to_drain.append(pubkey)
            verifying_key = VerifyingKey.from_string(pubkey)
            signature_valid = verifying_key.verify(
                transaction_input.signature, transaction.hash_for_signature
            )
            if not signature_valid:
                return FailedValidateResult(message="Bad transaction signature")

    total_transferred = 0
    for transaction_output in transaction.outputs:
        total_transferred += transaction_output.value

    if total_available < total_transferred:
        return FailedValidateResult(
            message="Tried to transfer more than existing balance"
        )

    new_balances = dict(starting_ledger.balances)

    transfer_needed = total_transferred
    for key_to_drain in keys_to_drain:
        drain = min(total_transferred, new_balances[key_to_drain])
        new_balances[key_to_drain] -= drain
        transfer_needed -= drain
        assert transfer_needed >= 0
        assert new_balances[key_to_drain] >= 0
        if transfer_needed == 0:
            break
    assert transaction.is_coinbase or (transfer_needed == 0)

    for transaction_output in transaction.outputs:
        new_balances[transaction_output.recipient_public_key] = (
            new_balances.get(transaction_output.recipient_public_key, 0)
            + transaction_output.value
        )

    return SuccessfulValidateResult(
        new_ledger=Ledger(
            balances=FrozenDict(new_balances),
            previous_transactions=FrozenDict(
                {
                    **dict(starting_ledger.previous_transactions),
                    transaction.hash(): transaction,
                }
            ),
        )
    )


def validate_transactions(
    start_ledger: Ledger,
    block: SealedBlock,
) -> ValidateResult:
    ledger = start_ledger
    for i, node in enumerate(dfs(block.transaction_tree)):
        if not isinstance(node, LeafMerkleNode):
            continue
        transaction = node.payload
        valid = transaction.is_coinbase == (i == 0)
        if not valid:
            print("i", i, transaction.is_coinbase)
            print(transaction)
            assert False
        result = update_ledger(ledger, transaction)
        if not result.valid:
            return result
        ledger = result.new_ledger
    return SuccessfulValidateResult(new_ledger=ledger)
