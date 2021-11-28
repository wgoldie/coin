from dataclasses import dataclass, field
from coin.util import FrozenDict
from coin.merkle import dfs
from coin.block import SealedBlock
from coin.transaction import Transaction
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
    if not transaction.is_coinbase:
        total_available = BLOCK_REWARD
    else:
        for transaction_input in transaction.inputs:
            previous_hash = (
                transaction_input.previous_transaction_outpoint.previous_transaction_hash
            )
            if previous_hash not in starting_ledger.previous_transactions:
                return FailedValidateResult(message="Unknown prevous hash")
            previous_transaction = starting_ledger.previous_transactions[previous_hash]
            previous_outpoint = previous_transaction.outputs[
                transaction_input.previous_transaction_outpoint.index
            ]
            pubkey = previous_outpoint.recipient_public_key
            total_available += starting_ledger.balances[pubkey]
            if pubkey not in keys_to_drain:
                keys_to_drain.append(pubkey)
            # TODO check signature

    total_transferred = 0
    for transaction_output in transaction.outputs:
        total_transferred += transaction_output.value

    if total_available < total_transferred:
        return FailedValidateResult(
            message="Tried to transfer more than existing balance"
        )

    new_ledger = starting_ledger.copy()

    transfer_needed = total_transferred
    for key_to_drain in keys_to_drain:
        drain = min(total_transferred, new_ledger.balances[key_to_drain])
        new_ledger.balances[key_to_drain] -= drain
        transfer_needed -= drain
        assert transfer_needed >= 0
        assert new_ledger.balances[key_to_drain] >= 0
        if transfer_needed == 0:
            break
    assert transfer_needed == 0

    for transaction_output in transaction.outputs:
        new_ledger.balances[
            transaction_output.recipient_public_key
        ] += transaction_output.value

    return SuccessfulValidateResult(new_ledger=new_ledger)


def validate_transactions(start_ledger: Ledger, block: SealedBlock) -> ValidateResult:
    ledger = start_ledger
    for i, node in enumerate(dfs(block.transaction_tree)):
        transaction = node.payload
        assert transaction.is_coinbase == (i == 0)
        result = update_ledger(ledger, transaction)
        if not result.valid:
            return result
        ledger = result.new_ledger
    return SuccessfulValidateResult(new_ledger=ledger)
