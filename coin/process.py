from __future__ import annotations
import typing
import traceback
import queue
from coin.multiprocessing import mp_ctx
from coin.node_context import NodeContext
from multiprocessing import Queue

M = typing.TypeVar("M")


def receive_queue_messages(
    ctx: NodeContext, message_queue: Queue[M]
) -> typing.Optional[M]:
    try:
        message = message_queue.get(True, 0.1)
        ctx.info(f"recv {message}")
        return message
    except queue.Empty:
        return None


def send_queue_message(ctx: NodeContext, message_queue: Queue[M], message: M) -> None:
    message_queue.put(message)
    ctx.info(f"sent { str(message) }")


class Process(mp_ctx.Process):  # type: ignore
    _pconn, _cconn = mp_ctx.Pipe()

    _exception: typing.Optional[Exception] = None

    def run(self) -> None:
        try:
            mp_ctx.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            print(tb, flush=True)
            self._cconn.send((e, tb))

    @property
    def exception(self) -> typing.Optional[Exception]:
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception
