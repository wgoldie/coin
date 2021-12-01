from __future__ import annotations
import typing
from dataclasses import dataclass, InitVar, field
from enum import Enum
from ecdsa import SigningKey, VerifyingKey
from datetime import datetime


class LogType(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    DEBUG = "DEBUG"


@dataclass
class ECDSAKey:
    public_key: SigningKey
    private_key: VerifyingKey

    @staticmethod
    def generate() -> ECDSAKey:
        sk = SigningKey.generate()
        return ECDSAKey(
            public_key=sk.get_verifying_key(),
            private_key=sk,
        )

    @staticmethod
    def from_import(key_str: str) -> ECDSAKey:
        sk = SigningKey.from_string(key_str)
        return ECDSAKey(
            public_key=sk.get_verifying_key(),
            private_key=sk,
        )


@dataclass
class NodeContext:
    node_id: str
    private_key_dump: typing.Optional[str] = None
    node_key: ECDSAKey = field(init=False)
    startup_time: datetime = field(init=False)

    def __post_init__(self) -> None:
        self.startup_time = datetime.now()
        assert not hasattr(self, "node_key")
        if self.private_key_dump is not None:
            self.node_key = ECDSAKey.from_import(self.private_key_dump)
        else:
            self.info("Generating new public key...")
            self.node_key = ECDSAKey.generate()
            self.private_key_dump = self.node_key.private_key.to_string()

    def print(self, log_type: LogType, message: str) -> None:
        print(
            f"({self.node_id})\t{datetime.now() - self.startup_time}\t[{log_type.value}]\t{message}",
            flush=True,
        )

    def info(self, message: str) -> None:
        self.print(LogType.INFO, message)

    def warning(self, message: str) -> None:
        self.print(LogType.WARNING, message)

    def debug(self, message: str) -> None:
        # self.print(LogType.DEBUG, message)
        pass
