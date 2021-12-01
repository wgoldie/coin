# peering
## upon startup, scan hardcoded addresses as well as a list of cached addresses from previous runs
## open connections with those that respond in a timely manner
## get further peer addresses from current peers
## send out an online message every 30 min

import typing
from dataclasses import dataclass, replace, field
from coin.block import SealedBlock
from coin.node_context import NodeContext
from enum import Enum
import coin.messaging as messaging
from coin.node_state import (
    State,
    StartupState,
    Chains,
    try_add_block,
    try_add_transaction,
)


@dataclass(frozen=True)
class ListenResult:
    new_state: typing.Optional[State] = None
    responses: typing.Tuple[messaging.Message, ...] = tuple()
    addressed: typing.Tuple[messaging.AddressedMessage, ...] = tuple()


def find_inventory(head: Chains, header_hash: bytes) -> typing.Optional[Chains]:
    if head.block.header.block_hash == header_hash:
        return head
    elif head.parent is not None:
        return find_inventory(head.parent, header_hash)
    else:
        return None


def accumulate_inventories(
    init_head: Chains,
    stopping_hash: typing.Optional[bytes],
    *,
    MAX_INVENTORIES: int = 500,
) -> typing.Tuple[bytes, ...]:
    inventories = []
    current_head: typing.Optional[Chains] = init_head
    for i in range(MAX_INVENTORIES):
        if current_head is None:
            break
        if current_head.block.header.block_hash == stopping_hash:
            break
        inventories.append(current_head.block.header.block_hash)
        current_head = current_head.parent
    return tuple(inventories)


# block download
## self chooses a peer and send getblocks with genesis block hash
## peer sends back 500 block inventories (ids) start with the genesis block
## self sends the peer getdata with 128 inventories starting just after the genesis block
## peer sends 128 block messages with the requested blocks
## self validates these blocks and sends another getblocks with list of 20 header hashes
## peer checks its "best" (?) chain for each of these hashes, starting from the highest height, and sends back 500 blocks starting from the first matcha
## if no match is found it sends 500 starting from the genesis block
## repeat until self has the tip of peer's blockchain


def log_wrong_state(
    ctx: NodeContext, message_type: messaging.MessageType, actual_state: StartupState
) -> None:
    ctx.info(
        f"Got {message_type.value} message while in {actual_state.value}, ignoring"
    )


def listen(
    ctx: NodeContext,
    state: State,
    message: messaging.Message,
) -> typing.Optional[ListenResult]:
    if isinstance(message, messaging.VersionAckMessage):

        if state.startup_state != StartupState.CONNECTING:
            log_wrong_state(ctx, message.message_type, state.startup_state)
            return None

        return ListenResult(
            new_state=replace(state, startup_state=StartupState.INVENTORY),
            responses=(
                messaging.GetBlocksMessage(
                    payload=messaging.GetBlocksMessage.Payload(
                        header_hashes=(state.best_head.block.header.block_hash,),
                        stopping_hash=None,
                    )
                ),
                messaging.GetAddrMessage(),
            ),
        )

    elif isinstance(message, messaging.VersionMessage):

        return ListenResult(responses=(messaging.VersionAckMessage(),))

    elif isinstance(message, messaging.GetBlocksMessage):

        for header_hash in message.payload.header_hashes:
            shared_block = None
            shared_block = find_inventory(state.best_head, header_hash)
            if shared_block is not None:
                break

        if shared_block is None:
            ctx.info("Failed to find shared block")
            return None

        inventories = accumulate_inventories(
            shared_block, message.payload.stopping_hash
        )

        return ListenResult(
            responses=(
                messaging.InventoryMessage(
                    payload=messaging.InventoryMessage.Payload(
                        header_hashes=inventories
                    )
                ),
            )
        )

    elif isinstance(message, messaging.InventoryMessage):

        if state.startup_state != StartupState.INVENTORY:
            log_wrong_state(ctx, message.message_type, state.startup_state)
            return None

        needed_blocks = [
            header_hash
            for header_hash in message.payload.header_hashes
            if header_hash not in state.block_lookup
        ]
        if len(needed_blocks) == 0:
            return ListenResult(
                new_state=replace(state, startup_state=StartupState.SYNCED),
            )
        else:
            return ListenResult(
                new_state=replace(state, startup_state=StartupState.DATA),
                responses=(
                    messaging.GetDataMessage(
                        payload=messaging.GetDataMessage.Payload(
                            objects_requested=tuple(needed_blocks)
                        )
                    ),
                ),
            )

    elif isinstance(message, messaging.GetDataMessage):

        blocks_to_send = []
        for header_hash in message.payload.objects_requested:
            block = state.block_lookup.get(header_hash)
            if block is not None:
                blocks_to_send.append(block.block)

        return ListenResult(
            responses=(
                tuple(
                    messaging.BlockMessage(
                        payload=messaging.BlockMessage.Payload(block=block)
                    )
                    for block in blocks_to_send
                )
            )
        )

    elif isinstance(message, messaging.BlockMessage):
        if message.payload.block.header.block_hash in state.block_lookup:
            ctx.info(
                f"Got block {message.payload.block.header.block_hash!r} already in storage"
            )
            return None

        return ListenResult(new_state=try_add_block(ctx, state, message.payload.block))

    elif isinstance(message, messaging.TransactionMessage):
        new_mempool = try_add_transaction(state.mempool, message.payload.transaction)
        return ListenResult(new_state=replace(state, mempool=new_mempool))
    elif isinstance(message, messaging.GetAddrMessage):
        return ListenResult(
            responses=(
                messaging.AddrMessage(
                    payload=(
                        messaging.AddrMessage.Payload(addresses=tuple(state.peers))
                    )
                ),
            ),
        )
    elif isinstance(message, messaging.AddrMessage):
        ctx.info(f"PEERS A: {message.payload}")
        peers = set()
        for new_peer in message.payload.addresses:
            if new_peer not in state.peers and new_peer != ctx.node_id:
                peers.add(new_peer)
        if len(peers) == 0:
            return ListenResult()
        new_peers = {*state.peers, *peers}
        ctx.info(f"PEERS: {new_peers}")
        return ListenResult(
            new_state=replace(state, peers=frozenset(new_peers)),
            addressed=tuple(
                messaging.AddressedMessage(
                    message=messaging.GetAddrMessage(),
                    sender_address=ctx.node_id,
                    recipient_address=peer,
                )
                for peer in new_peers
            ),
        )
    else:
        raise ValueError("Unhandled message type", message)
