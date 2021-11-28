# peering
## upon startup, scan hardcoded addresses as well as a list of cached addresses from previous runs
## open connections with those that respond in a timely manner
## get further peer addresses from current peers
## send out an online message every 30 min

import typing
from dataclasses import dataclass, replace
from coin.block import SealedBlock
from enum import Enum

@dataclass
class Chains:
    block: SealedBlock
    validated: bool
    child_chains: typing.Tuple[Chains]

class MessageType(str, Enum):
    VERSION = 'VERSION'
    VERSION_ACK = 'VERSION_ACK'
    GET_BLOCKS = 'GET_BLOCKS'
    INVENTORY = 'INVENTORY'
    GET_DATA = 'GET_DATA'
    BLOCK = 'BLOCK'


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
        header_hashes: typing.Tuple[bytes]

    payload: Payload
    message_type: typing.Literal[MessageType.INVENTORY] = MessageType.INVENTORY


@dataclass
class GetDataMessage(Message):
    @dataclass
    class Payload:
        objects_requested: typing.Tuple[bytes]

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
    PEERING = 'PEERING'
    CONNECTING = 'CONNECTING'
    INVENTORY = 'INVENTORY'
    DATA = 'DATA'
    SYNCED = 'SYNCED'


@dataclass(frozen=True)
class State:
    chains: Chains
    block_lookup: typing.Dict[bytes, SealedBlock]
    startup_state: StartupState


@dataclass(frozen=True)
class ListenResult:
    new_state: typing.Optional[State] = None
    responses: typing.Tuple[Message, ...] = tuple()


# block download
## self chooses a peer and send getblocks with genesis block hash
## peer sends back 500 block inventories (ids) start with the genesis block
## self sends the peer getdata with 128 inventories starting just after the genesis block
## peer sends 128 block messages with the requested blocks
## self validates these blocks and sends another getblocks with list of 20 header hashes  
## peer checks its "best" (?) chain for each of these hashes, starting from the highest height, and sends back 500 blocks starting from the first matcha
## if no match is found it sends 500 starting from the genesis block
## repeat until self has the tip of peer's blockchain

def listen(state: State, message: Message) -> typing.Optional[ListenResult]:
    if isinstance(message, VersionAckMessage):
        if state.startup_state == StartupState.CONNECTING:
            return ListenResult(new_state=replace(state, startup_state=StartupState.INVENTORY))
        else:
            return None
    elif isinstance(message, VersionMessage):
        if state.startup_state == StartupState.SYNCED:
            return ListenResult(responses=(VersionAckMessage(),))
        else:
            return None
        pass
    elif isinstance(message, GetBlocksMessage):
        if state.startup_state == StartupState.SYNCED:
            return ListenResult(responses=(InventoryMessage(),))
        else:
            return None
        pass
    elif isinstance(message, InventoryMessage):
        if state.startup_state == StartupState.INVENTORY:
            return ListenResult(new_state=replace(state, startup_state=StartupState.DATA), responses=(GetDataMessage(),))
        else:
            return None
        pass
    elif isinstance(message, GetDataMessage):
        if state.startup_state == StartupState.SYNCED:
            blocks_to_send = []
            for header_hash in message.payload.objects_requested:
                block = state.block_lookup.get(header_hash)
                if block is not None:
                    blocks_to_send.append(block)

            return ListenResult(responses=(tuple(BlockMessage(payload=BlockMessage.Payload(block=block)) for block in blocks_to_send)))
        else:
            return None
        pass
    elif isinstance(message, BlockMessage):
        if state.startup_state == StartupState.DATA:
            return ListenResult(new_state=replace(state, startup_state=StartupState.SYNCED))
            # fork here
        else:
            return None
        pass
    else:
        raise ValueError("Unhandled message type", message)
