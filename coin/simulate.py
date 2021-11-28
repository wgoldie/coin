import logging
import multiprocessing as mp
from coin.node_context import NodeContext
from coin.run_node import run_node
import traceback

# ctx = mp.get_context('spawn')
ctx = mp

class Process(ctx.Process):
    _pconn, _cconn = mp.Pipe()

    _exception = None

    def run(self):
        try:
            ctx.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception

def simulate_two():
    queues = [mp.Queue(), mp.Queue()]

    processes = [
        Process(
            target=run_node,
            kwargs={
                'ctx': NodeContext(node_id=str(i)),
                'messages_in': queues[(i + 1) % 2],
                'messages_out': queues[i % 2]})
        for i in range(2)]

    for process in processes:
        process.start()
    for process in processes:
        process.join()
        if process.exception:
            print(process.exception)

if __name__ == "__main__":
    simulate_two()
