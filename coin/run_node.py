from __future__ import annotations
from dataclasses import replace
from multiprocessing import Queue
import typing
import queue
from collections import defaultdict
from coin.node_context import NodeContext
import coin.messaging as messaging
from coin.listen import listen
from coin.node_state import State, Chains, StartupState, try_add_block, Mempool
from coin.genesis import GENESIS_BLOCK
from coin.block import OpenBlock, OpenBlockHeader, SealedBlock
from coin.find_block import find_block
from coin.ledger import Ledger
import coin.transaction as transaction
from coin.merkle import LeafMerkleNode, MerkleForest
from coin.mining import MiningProcessHandle, MiningProcessConfig


def build_next_block(state: State) -> OpenBlock:
    transaction_tree = state.mempool.transactions.merge()
    return OpenBlock(
        header=OpenBlockHeader(
            previous_block_hash=state.best_head.block.header.block_hash,
            transaction_tree_hash=transaction_tree.node_hash(),
        ),
        transaction_tree=transaction_tree,
    )


M = typing.TypeVar("M")


def receive_message(message_queue: Queue[M]) -> typing.Optional[M]:
    try:
        return message_queue.get(True, 0.2)
    except queue.Empty:
        return None


def run_node(
    ctx: NodeContext,
    messages_in: Queue[messaging.Message],
    messages_out: Queue[messaging.Message],
    result_out: Queue[State],
    *,
    MAX_TRIES: int = 10000,
    INIT_STARTUP_STATE: StartupState = StartupState.PEERING,
) -> None:
    ctx.info("start")
    genesis_chains = Chains(parent=None, height=1, block=GENESIS_BLOCK)
    state = State(
        best_head=genesis_chains,
        block_lookup={GENESIS_BLOCK.header.block_hash: genesis_chains},
        startup_state=INIT_STARTUP_STATE,
        mempool=Mempool(
            transactions=MerkleForest(
                trees=(
                    LeafMerkleNode(
                        payload=transaction.make_reward_transaction(ctx), height=1
                    ),
                )
            ),
            ledger=Ledger(),
        ),
        ledger=Ledger(),
    )
    difficulty = 2
    mining_process = None
    while state.best_head.height < 4:

        message: typing.Optional[messaging.Message]
        message = receive_message(messages_in)
        if message is not None:
            ctx.info(f"recv { message }")
            result = listen(ctx, state, message)
            if result is not None:
                if result.new_state is not None:
                    if (
                        result.new_state.mempool != state.mempool
                        and mining_process is not None
                    ):
                        mining_process.stop()
                        mining_process = None
                    state = result.new_state
                for response in result.responses:
                    messages_out.put(response)

        if state.startup_state == StartupState.PEERING:
            message = messaging.VersionMessage(
                payload=messaging.VersionMessage.Payload(version="0.0.0")
            )
            messages_out.put(message)
            ctx.info(f"sent { message }")
            state = replace(state, startup_state=StartupState.CONNECTING)

        if state.startup_state == StartupState.SYNCED and mining_process is None:
            next_block = build_next_block(state)
            mining_process = MiningProcessHandle(
                config=MiningProcessConfig(
                    ctx=ctx, difficulty=difficulty, next_block=next_block
                )
            )

        if mining_process is not None:
            sealed_header = receive_message(mining_process.result_queue)
            if sealed_header is not None:
                new_block = SealedBlock(
                    header=sealed_header,
                    transaction_tree=mining_process.config.next_block.transaction_tree,
                )
                state = try_add_block(ctx, state, new_block)
                assert sealed_header.block_hash in state.block_lookup
                message = messaging.BlockMessage(
                    payload=messaging.BlockMessage.Payload(block=new_block)
                )
                ctx.info(f"sent { message }")
                messages_out.put(message)
                mining_process.stop()
                mining_process = None
    result_out.put(state)
