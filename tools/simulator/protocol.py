"""Bounded version 1 framing shared by the harness and simulator."""
import json
import struct

MAX_FRAME = 1024 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def receive(connection):
    def exact(size):
        result = bytearray()
        while len(result) < size:
            part = connection.recv(size - len(result))
            if not part:
                raise EOFError("connection closed")
            result.extend(part)
        return bytes(result)
    length, = struct.unpack("!I", exact(4))
    if not 0 < length <= MAX_FRAME:
        raise ValueError("invalid frame length")
    value = json.loads(exact(length).decode("utf-8"), object_pairs_hook=unique_object,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > 64:
            raise ValueError("JSON nesting exceeds limit")
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    if not isinstance(value, dict):
        raise ValueError("frame must be an object")
    return value


def send(connection, value):
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()
    if not 0 < len(payload) <= MAX_FRAME:
        raise ValueError("response exceeds frame limit")
    connection.sendall(struct.pack("!I", len(payload)) + payload)
