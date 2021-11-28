from coin.node_context import NodeContext
from dataclasses import replace
from multiprocessing import Queue
import coin.messaging as messaging
from coin.listen import listen
from coin.node_state import State, Chains, StartupState, try_add_block, Mempool
from coin.genesis import GENESIS_BLOCK
from coin.block import OpenBlockHeader, SealedBlock
from coin.find_block import find_block
from coin.ledger import Ledger
import coin.transaction as transaction
import typing
from collections import defaultdict
from coin.merkle import LeafMerkleNode, MerkleForest
import queue


def run_node(
    ctx: NodeContext,
    messages_in: "Queue[messaging.Message]",
    messages_out: "Queue[messaging.Message]",
    result_out: "Queue[State]",
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
    starting_nonces: typing.DefaultDict[OpenBlockHeader, int] = defaultdict(lambda: 0)
    difficulty = 1
    while state.best_head.height < 4:
        message: typing.Optional[messaging.Message]
        try:
            message = messages_in.get(False, 1)
        except queue.Empty:
            message = None
        if message is not None:
            ctx.info(f"msg { message }")
            result = listen(ctx, state, message)
            if result is not None:
                if result.new_state is not None:
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

        if state.startup_state == StartupState.SYNCED:
            transaction_tree = state.mempool.transactions.merge()
            next_block_header = OpenBlockHeader(
                previous_block_hash=state.best_head.block.header.block_hash,
                transaction_tree_hash=transaction_tree.node_hash(),
            )
            sealed_header = find_block(
                ctx,
                next_block_header,
                difficulty=difficulty,
                starting_nonce=starting_nonces[next_block_header],
                max_tries=MAX_TRIES,
            )

            if sealed_header is not None:
                new_block = SealedBlock(
                    header=sealed_header, transaction_tree=transaction_tree
                )
                state = try_add_block(ctx, state, new_block)
                assert sealed_header.block_hash in state.block_lookup
                messages_out.put(
                    messaging.BlockMessage(
                        payload=messaging.BlockMessage.Payload(block=new_block)
                    )
                )
            else:
                starting_nonces[next_block_header] += MAX_TRIES
    result_out.put(state)
