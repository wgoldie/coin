from coin.node_context import NodeContext
from multiprocessing import Queue
from coin.messaging import Message
from coin.listen import listen
from coin.node import State, Chains, StartupState, try_add_block
from coin.genesis import GENESIS_BLOCK
from coin.block import OpenBlockHeader, SealedBlock
from coin.find_block import find_block
import typing
from collections import defaultdict


def run_node(
    ctx: NodeContext, messages_in: Queue[Message], messages_out: Queue[Message]
) -> None:
    genesis_chains = Chains(parent=None, height=1, block=GENESIS_BLOCK)
    state = State(
        best_head=genesis_chains,
        block_lookup={GENESIS_BLOCK.header.block_hash: genesis_chains},
        startup_state=StartupState.CONNECTING,
    )
    starting_nonces: typing.DefaultDict[OpenBlockHeader, int] = defaultdict(lambda: 0)
    difficulty = 1
    while True:
        message = messages_in.get(False, 1)
        if message is not None:
            result = listen(ctx, state, message)
            if result is not None:
                if result.new_state is not None:
                    state = result.new_state
                for response in result.responses:
                    messages_out.put(response)

        next_block_header = OpenBlockHeader(
            previous_block_hash=state.best_head.block.header.block_hash,
            transaction_tree_hash=b"abc",
        )
        sealed_header = find_block(
            ctx,
            next_block_header,
            difficulty=difficulty,
            starting_nonce=starting_nonces[next_block_header],
            max_tries=100,
        )

        if sealed_header is not None:
            state = try_add_block(state, SealedBlock(header=sealed_header))
            assert sealed_header.block_hash in state.block_lookup
            # TODO broadcast block


if __name__ == "__main__":
    run_node(ctx=NodeContext(node_id="a"), messages_in=Queue(), messages_out=Queue())
