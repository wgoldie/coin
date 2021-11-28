from dataclasses import dataclass
from enum import Enum
import typing
from coin.block import SealedBlock
from coin.transaction import Transaction


class MessageType(str, Enum):
    VERSION = "VERSION"
    VERSION_ACK = "VERSION_ACK"
    GET_BLOCKS = "GET_BLOCKS"
    INVENTORY = "INVENTORY"
    GET_DATA = "GET_DATA"
    BLOCK = "BLOCK"
    TRANSACTION = "TRANSACTION"


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


@dataclass
class TransactionMessage(Message):
    @dataclass
    class Payload:
        transaction: Transaction

    payload: Payload
    message_type: typing.Literal[MessageType.TRANSACTION] = MessageType.TRANSACTION
