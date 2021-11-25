import hashlib


def hash_byte_sets(*args: bytes) -> bytes:
    hasher = hashlib.sha256()
    for byte_set in args:
        hasher.update(byte_set)
    return hasher.digest()
