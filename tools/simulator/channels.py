"""Volatile inherited byte streams, independent of application message formats."""
import re

from .model import Refusal


class Channels:
    maximum_transfer = 16384
    maximum_capacity = 65536
    maximum_pairs = 128

    def __init__(self):
        self.endpoints = {}
        self.next_endpoint = 1

    def inherit(self, first, second, capacity=65536):
        if (not all(isinstance(owner, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", owner)
                    for owner in (first, second)) or first == second
                or type(capacity) is not int or not 1 <= capacity <= self.maximum_capacity):
            raise ValueError("invalid inherited channel configuration")
        if len(self.endpoints) >= self.maximum_pairs * 2:
            raise ValueError("inherited channel limit reached")
        left, right = str(self.next_endpoint), str(self.next_endpoint + 1)
        self.next_endpoint += 2
        for endpoint, peer, owner in ((left, right, first), (right, left, second)):
            self.endpoints[endpoint] = {
                "owner": owner, "peer": peer, "capacity": capacity,
                "buffer": bytearray(), "open": True,
            }
        return left, right

    def close(self, endpoint):
        node = self.endpoints[endpoint]
        node["open"] = False
        node["buffer"].clear()
        peer = node["peer"]
        if not self.endpoints[peer]["open"]:
            del self.endpoints[endpoint]
            del self.endpoints[peer]

    def process_exited(self, owner):
        for endpoint, node in list(self.endpoints.items()):
            if node["owner"] == owner and node["open"]:
                self.close(endpoint)

    def power_loss(self):
        # Counters are not reset: stale endpoints never alias a later pair.
        self.endpoints.clear()

    def execute(self, identity, operation, args):
        expected = {"send": {"endpoint", "hex"}, "receive": {"endpoint", "length"},
                    "close": {"endpoint"}, "observe": {"endpoint"}}
        if operation not in expected:
            raise Refusal("unsupported", "channel operation is not modeled")
        if set(args) != expected[operation] or not isinstance(args.get("endpoint"), str):
            raise Refusal("arguments", "invalid channel arguments")
        endpoint = args["endpoint"]
        node = self.endpoints.get(endpoint)
        if node is None or node["owner"] != identity or not node["open"]:
            raise Refusal("handle", "invalid or foreign channel endpoint")
        peer = self.endpoints[node["peer"]]
        if operation == "observe":
            return {"owner": identity, "peer": peer["owner"], "peer_open": peer["open"]}, []
        if operation == "close":
            self.close(endpoint)
            return None, [{"operation": "channel.close", "endpoint": endpoint}]
        if operation == "send":
            data = args["hex"]
            if (not isinstance(data, str) or len(data) > self.maximum_transfer * 2
                    or len(data) % 2 or not re.fullmatch(r"[0-9a-f]*", data)):
                raise Refusal("arguments", "invalid or oversized channel write")
            if not peer["open"]:
                raise Refusal("broken-pipe", "channel peer has exited or closed")
            count = min(len(data) // 2, peer["capacity"] - len(peer["buffer"]))
            if data and count == 0:
                raise Refusal("would-block", "channel buffer is full")
            peer["buffer"].extend(bytes.fromhex(data[:count * 2]))
            return {"written": count}, [{"operation": "channel.send", "endpoint": endpoint,
                                         "bytes": count}]
        length = args["length"]
        if type(length) is not int or not 1 <= length <= self.maximum_transfer:
            raise Refusal("arguments", "invalid or oversized channel read")
        if not node["buffer"] and peer["open"]:
            raise Refusal("would-block", "channel buffer is empty")
        data = bytes(node["buffer"][:length])
        del node["buffer"][:length]
        return {"hex": data.hex(), "eof": not data and not peer["open"]}, [
            {"operation": "channel.receive", "endpoint": endpoint, "bytes": len(data)}]
