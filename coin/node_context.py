from dataclasses import dataclass
from enum import Enum


class LogType(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"


@dataclass
class NodeContext:
    node_id: str

    def print(self, log_type: LogType, message: str) -> None:
        print(f"({self.node_id})\t[{log_type.value}]\t{message}", flush=True)

    def info(self, message: str) -> None:
        self.print(LogType.INFO, message)

    def warning(self, message: str) -> None:
        self.print(LogType.WARNING, message)
