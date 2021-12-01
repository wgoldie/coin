import typing
import logging
import multiprocessing as mp
import queue
from coin.multiprocessing import mp_ctx
from coin.node_context import NodeContext
from coin.run_node import run_node
from coin.messaging import AddressedMessage
from coin.node_state import State
from coin.process import Process
import traceback


def simulate_two() -> None:
    queues: typing.List[mp.Queue[AddressedMessage]] = [mp_ctx.Queue(5), mp_ctx.Queue(5)]
    result_queues: typing.List[mp.Queue[State]] = [mp_ctx.Queue(1), mp_ctx.Queue(1)]

    ids = ["a", "b"]
    processes = [
        Process(
            target=run_node,
            kwargs={
                "ctx": NodeContext(node_id=ids[i]),
                "messages_in": queues[(i + 1) % 2],
                "messages_out": queues[i % 2],
                "result_out": result_queues[i],
                "init_peers": ids[(i + 1) % 2],
            },
        )
        for i in range(2)
    ]

    for process in processes:
        process.start()

    result = None
    while result is None:
        for i, process in enumerate(processes):
            try:
                result = result_queues[i].get(True, 0.2)
                break
            except queue.Empty:
                pass
            if process.exception:
                print(process.exception, flush=True)
                return
    for process in processes:
        process.terminate()
    print(result.best_head.ledger.balances, flush=True)


if __name__ == "__main__":
    simulate_two()
