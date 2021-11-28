import coin.block as block
from coin.merkle import NullMerkleNode

GENESIS_TRANSACTION_TREE = NullMerkleNode()

GENESIS_HEADER = block.OpenBlockHeader(
    transaction_tree_hash=GENESIS_TRANSACTION_TREE.node_hash(),
    previous_block_hash=b"",
)

GENESIS_NONCE = 99

GENESIS_HASH = GENESIS_HEADER.hash(nonce=GENESIS_NONCE)

GENESIS_BLOCK = block.SealedBlock(
    header=block.SealedBlockHeader(
        transaction_tree_hash=GENESIS_HEADER.transaction_tree_hash,
        previous_block_hash=GENESIS_HEADER.previous_block_hash,
        nonce=GENESIS_NONCE,
        block_hash=GENESIS_HASH,
    ),
    transaction_tree=GENESIS_TRANSACTION_TREE,
)

assert GENESIS_BLOCK.validate()
