import typing
import logging
import multiprocessing as mp
from coin.node_context import NodeContext
from coin.run_node import run_node
from coin.messaging import Message
from coin.node_state import State
import traceback

# ctx = mp.get_context('spawn')
ctx = mp


class Process(ctx.Process):
    _pconn, _cconn = mp.Pipe()

    _exception: typing.Optional[Exception] = None

    def run(self) -> None:
        try:
            ctx.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

    @property
    def exception(self) -> typing.Optional[Exception]:
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception


def simulate_two() -> None:
    queues: typing.List[mp.Queue[Message]] = [mp.Queue(), mp.Queue()]
    result_queues: typing.List[mp.Queue[State]] = [mp.Queue(), mp.Queue()]

    processes = [
        Process(
            target=run_node,
            kwargs={
                "ctx": NodeContext(node_id=str(i)),
                "messages_in": queues[(i + 1) % 2],
                "messages_out": queues[i % 2],
                "result_out": result_queues[i],
            },
        )
        for i in range(2)
    ]

    for process in processes:
        process.start()
    results = []
    for i, process in enumerate(processes):
        results.append(result_queues[i].get())
        process.join()
        if process.exception:
            print(process.exception)
    for result in results:
        print(result.ledger.balances)


if __name__ == "__main__":
    simulate_two()
