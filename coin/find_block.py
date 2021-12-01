import typing
from coin.block import OpenBlockHeader, SealedBlockHeader
from coin.node_context import NodeContext


def find_block(
    ctx: NodeContext,
    open_block_header: OpenBlockHeader,
    difficulty: int,
    *,
    reporting_interval: int = int(1e6),
    starting_nonce: int = 0,
    max_tries: int = int(1e10),
) -> typing.Optional[SealedBlockHeader]:
    if difficulty < 1:
        raise ValueError("Invalid difficulty", 0)
    target = b"0" * difficulty
    ctx.info(f"searching for block with difficulty {difficulty}")
    for i, nonce in enumerate(range(starting_nonce, starting_nonce + max_tries)):
        block_hash = open_block_header.hash(nonce)
        if block_hash.startswith(target):
            ctx.info(f"found block {block_hash.hex()}!")
            return SealedBlockHeader(
                transaction_tree_hash=open_block_header.transaction_tree_hash,
                previous_block_hash=open_block_header.previous_block_hash,
                nonce=nonce,
                block_hash=block_hash,
            )
        if i % reporting_interval == 0:
            ctx.info(f"tried {reporting_interval} nonces")
    ctx.debug(
        f"failed to find block with {difficulty} in {max_tries} tries from nonce {starting_nonce}"
    )
    return None
