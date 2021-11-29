from __future__ import annotations
from dataclasses import dataclass, field
import typing
from multiprocessing import Queue
from coin.multiprocessing import mp_ctx
from coin.process import Process
from coin.node_context import NodeContext
from coin.block import OpenBlock, SealedBlockHeader
from coin.find_block import find_block


@dataclass(frozen=True)
class MiningProcessConfig:
    ctx: NodeContext
    difficulty: int
    next_block: OpenBlock


def run_mining(
    config: MiningProcessConfig, result_queue: Queue[SealedBlockHeader]
) -> None:
    while True:
        block = find_block(
            ctx=config.ctx,
            open_block_header=config.next_block.header,
            difficulty=config.difficulty,
        )
        if block is not None:
            result_queue.put(block)
            break


@dataclass
class MiningProcessHandle:
    config: MiningProcessConfig
    process: Process = field(init=False)
    result_queue: Queue[SealedBlockHeader] = field(init=False)
    terminated: bool = False

    def __post_init__(self) -> None:
        self.config.ctx.info("Starting mining process...")
        self.result_queue = mp_ctx.Queue(2)
        self.process = Process(
            target=run_mining,
            kwargs={"config": self.config, "result_queue": self.result_queue},
        )
        self.process.start()

    def stop(self) -> None:
        self.process.join()
        self.terminated = True
        if self.process.exception:
            self.config.ctx.warning(str(self.process.exception))

    def terminate(self) -> None:
        self.process.terminate()
        self.terminated = True