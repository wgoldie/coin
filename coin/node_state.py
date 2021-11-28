from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
import typing
from coin.block import SealedBlock
from coin.ledger import Ledger, validate_transactions
from coin.node_context import NodeContext


@dataclass
class Chains:
    parent: typing.Optional[Chains]
    height: int
    block: SealedBlock


class StartupState(str, Enum):
    PEERING = "PEERING"
    CONNECTING = "CONNECTING"
    INVENTORY = "INVENTORY"
    DATA = "DATA"
    SYNCED = "SYNCED"


@dataclass(frozen=True)
class State:
    best_head: Chains
    block_lookup: typing.Dict[bytes, Chains]
    startup_state: StartupState
    ledger: Ledger
    orphaned_blocks: typing.FrozenSet[SealedBlock] = frozenset()


def try_add_block(ctx: NodeContext, state: State, block: SealedBlock) -> State:
    if block.header.previous_block_hash not in state.block_lookup:
        return replace(state, orphaned_blocks={*state.orphaned_blocks, block})

    hashes_valid = block.validate_hashes()
    if not hashes_valid:
        ctx.warning("invalid hashes in block received")
        return state

    validate_result = validate_transactions(state.ledger, block)
    if not validate_result.valid:
        ctx.warning(f"invalid transactions in block received: {validate_result.message}")
        return state
    new_ledger = validate_result.new_ledger

    parent_chains = state.block_lookup[block.header.previous_block_hash]
    is_new_best_head = parent_chains.height >= state.best_head.height
    chains = Chains(parent=parent_chains, block=block, height=parent_chains.height + 1)

    new_orphans = set()
    newly_parented = None
    for orphan_block in state.orphaned_blocks:
        if orphan_block.header.previous_block_hash == block.header.block_hash:
            newly_parented = orphan_block
        else:
            new_orphans.add(orphan_block)

    new_state = replace(
        state,
        block_lookup={**state.block_lookup, block.header.block_hash: chains},
        best_head=chains if is_new_best_head else state.best_head,
        orphaned_blocks=frozenset(new_orphans)
        if newly_parented is not None
        else state.orphaned_blocks,
        ledger=new_ledger,
    )
    if newly_parented is not None:
        return try_add_block(ctx, state, newly_parented)
    else:
        return new_state
