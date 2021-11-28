import hashlib
import typing


def hash_byte_sets(*args: bytes) -> bytes:
    hasher = hashlib.sha256()
    for byte_set in args:
        hasher.update(byte_set)
    return hasher.digest()


K = typing.TypeVar("K", bound=typing.Hashable)
V = typing.TypeVar("V")


class FrozenDict(typing.Dict[K, V], typing.Generic[K, V]):
    pass
