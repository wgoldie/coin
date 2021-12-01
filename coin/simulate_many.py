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
    result_queues: typing.List[mp.Queue[State]] = [mp_ctx.Queue(1), mp_ctx.Queue(1)]
    processes = {}
    messages_in = {}
    messages_out = {}
    result_out = {}
    PIDS = ["a", "b", "c", "d", "e"]
    for i, pid in enumerate(PIDS):
        messages_in[pid] = mp_ctx.Queue()
        messages_out[pid] = mp_ctx.Queue()
        result_out[pid] = mp_ctx.Queue()
        processes[pid] = Process(
            target=run_node,
            kwargs={
                "ctx": NodeContext(node_id=pid),
                "messages_in": messages_in[pid],
                "messages_out": messages_out[pid],
                "result_out": result_out[pid],
                "init_peers": {PIDS[(i + 1) % len(PIDS)]},
            },
        )

    for process in processes.values():
        process.start()

    result = None
    while result is None:

        for pid, out_queue in messages_out.items():
            try:
                message = out_queue.get(True, 0.2)
                assert message.sender_address == pid
                messages_in[message.recipient_address].put(message)
            except queue.Empty:
                pass

        for pid, result_queue in result_out.items():
            try:
                result = result_queue.get(False)
                break
            except queue.Empty:
                pass

    for process in processes:
        process.terminate()

    print(result.best_head.ledger.balances, flush=True)


if __name__ == "__main__":
    simulate_two()
