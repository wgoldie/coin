from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
import typing
from coin.block import SealedBlock


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
    orphaned_blocks: typing.FrozenSet[SealedBlock] = frozenset()


def try_add_block(state: State, block: SealedBlock) -> State:
    if block.header.previous_block_hash not in state.block_lookup:
        return replace(state, orphaned_blocks={*state.orphaned_blocks, block})

    valid = (
        block.validate()
    )  # TODO pass some slice of state here and validate transactions
    if not valid:
        print("invalid block received")
        return state
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
    )
    if newly_parented is not None:
        return try_add_block(state, newly_parented)
    else:
        return new_state
