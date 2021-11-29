import typing
import traceback
from coin.multiprocessing import mp_ctx


class Process(mp_ctx.Process):  # type: ignore
    _pconn, _cconn = mp_ctx.Pipe()

    _exception: typing.Optional[Exception] = None

    def run(self) -> None:
        try:
            mp_ctx.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

    @property
    def exception(self) -> typing.Optional[Exception]:
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception
