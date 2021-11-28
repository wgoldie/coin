# peering
## upon startup, scan hardcoded addresses as well as a list of cached addresses from previous runs
## open connections with those that respond in a timely manner
## get further peer addresses from current peers
## send out an online message every 30 min

import typing
from dataclasses import dataclass, replace, field
from coin.block import SealedBlock
from enum import Enum


@dataclass
class Chains:
    parent: Chains
    height: int
    block: SealedBlock


class MessageType(str, Enum):
    VERSION = "VERSION"
    VERSION_ACK = "VERSION_ACK"
    GET_BLOCKS = "GET_BLOCKS"
    INVENTORY = "INVENTORY"
    GET_DATA = "GET_DATA"
    BLOCK = "BLOCK"


class Message:
    message_type: MessageType


@dataclass
class VersionMessage(Message):
    @dataclass
    class Payload:
        version: str

    payload: Payload
    message_type: typing.Literal[MessageType.VERSION] = MessageType.VERSION


@dataclass
class VersionAckMessage(Message):
    message_type: typing.Literal[MessageType.VERSION_ACK] = MessageType.VERSION_ACK


@dataclass
class GetBlocksMessage(Message):
    @dataclass
    class Payload:
        header_hashes: typing.Tuple[bytes]
        stopping_hash: typing.Optional[bytes]

    payload: Payload
    message_type: typing.Literal[MessageType.GET_BLOCKS] = MessageType.GET_BLOCKS


@dataclass
class InventoryMessage(Message):
    @dataclass
    class Payload:
        header_hashes: typing.Tuple[bytes, ...]

    payload: Payload
    message_type: typing.Literal[MessageType.INVENTORY] = MessageType.INVENTORY


@dataclass
class GetDataMessage(Message):
    @dataclass
    class Payload:
        objects_requested: typing.Tuple[bytes, ...]

    payload: Payload
    message_type: typing.Literal[MessageType.GET_DATA] = MessageType.GET_DATA


@dataclass
class BlockMessage(Message):
    @dataclass
    class Payload:
        block: SealedBlock

    payload: Payload
    message_type: typing.Literal[MessageType.BLOCK] = MessageType.BLOCK


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
    orphaned_blocks: typing.Set[SealedBlock]


@dataclass(frozen=True)
class ListenResult:
    new_state: typing.Optional[State] = None
    responses: typing.Tuple[Message, ...] = tuple()


def find_inventory(head: Chains, header_hash: bytes) -> Chains:
    if head.block.header.block_hash == header_hash:
        return head
    elif head.parent is not None:
        return find_inventory(head.parent, header_hash)
    else:
        return None

def accumulate_inventories(
    head: Chains, stopping_hash: typing.Optional[bytes], *, MAX_INVENTORIES=500
) -> typing.Tuple[bytes, ...]:
    inventories = []
    for i in range(MAX_INVENTORIES):
        if head.block.header.block_hash == stopping_hash:
            break
        inventories.append(head.block.header.block_hash)
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

def try_add_block(state: State, block: SealedBlock) -> State:
    if block.header.previous_block_hash not in state.block_lookup:
        return replace(state, orphaned_blocks={*state.orphaned_blocks, block})

    valid = block.validate() # TODO pass some slice of state here and validate transactions
    if not valid:
        print('invalid block received')
        return state
    parent_chains = state.block_lookup[block.header.block_hash]
    is_new_best_head = parent_chains.height >= state.best_head.height
    chains = Chains(
        parent=parent_chains,
        block=block,
        height=parent_chains.height+1
    )

    new_orphans = set()
    newly_parented = None
    for orphan_block in state.orphaned_blocks:
        if orphan_block.header.previous_block_hash == block.header.block_hash:
            newly_parented = orphan_block
        else:
            new_orphans.add(orphan_block)

    new_state = replace(
        state,
        block_lookup={**state.block_lookup, block.header.previous_block_hash: block},
        best_head=chains if is_new_best_head else state.best_head,
        orphaned_blocks=new_orphans if newly_parented is not None else state.orphaned_blocks,
    )
    if newly_parented is not None:
        return try_add_block(state, newly_parented)
    else:
        return new_state



def listen(state: State, message: Message) -> typing.Optional[ListenResult]:
    if isinstance(message, VersionAckMessage):

        if state.startup_state == StartupState.CONNECTING:
            return ListenResult(
                new_state=replace(state, startup_state=StartupState.INVENTORY),
            )
        else:
            return None
    elif isinstance(message, VersionMessage):
        if state.startup_state == StartupState.SYNCED:
            return ListenResult(responses=(VersionAckMessage(),))
        else:
            return None
    elif isinstance(message, GetBlocksMessage):
        if state.startup_state == StartupState.SYNCED:
            for header_hash in message.payload.header_hashes:
                shared_block = None
                shared_block = find_inventory(state.best_head, header_hash)
                if shared_block is not None:
                    break
            if shared_block is not None:
                inventories = accumulate_inventories(shared_block, message.payload.stopping_hash)
                return ListenResult(
                    responses=(InventoryMessage(payload=InventoryMessage.Payload(header_hashes=inventories)),
               ))
            else:
                print('Failed to find shared block')
                return None
        else:
            return None
    elif isinstance(message, InventoryMessage):
        if state.startup_state == StartupState.INVENTORY:
            needed_blocks = [
                header_hash
                for header_hash in message.payload.header_hashes
                if header_hash not in state.block_lookup]
            return ListenResult(
                new_state=replace(state, startup_state=StartupState.DATA),
                responses=(GetDataMessage(payload=GetDataMessage.Payload(objects_requested=tuple(needed_blocks))),),
            )
        else:
            return None
    elif isinstance(message, GetDataMessage):
        if state.startup_state == StartupState.SYNCED:
            blocks_to_send = []
            for header_hash in message.payload.objects_requested:
                block = state.block_lookup.get(header_hash)
                if block is not None:
                    blocks_to_send.append(block.block)

            return ListenResult(
                responses=(
                    tuple(
                        BlockMessage(payload=BlockMessage.Payload(block=block))
                        for block in blocks_to_send
                    )
                )
            )
        else:
            return None
        pass
    elif isinstance(message, BlockMessage):
        if state.startup_state == StartupState.DATA:
            if message.payload.block.header.block_hash in state.block_lookup:
                return None

            return ListenResult(
                new_state=try_add_block(state, message.payload.block)
            )

        else:
            return None
        pass
    else:
        raise ValueError("Unhandled message type", message)
