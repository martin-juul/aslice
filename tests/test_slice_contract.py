"""Structural slice contract checks; these do not exercise an extractor.

Run: python -m unittest discover -s tests -p test_slice_contract.py
Requires jsonschema 4.x.
"""
import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class SliceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = read_json("schematics/json/slice.schema.json")
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema)
        cls.fixture = read_json("tests/fixtures/slice.json")

    def test_descriptor_fixture(self):
        self.validator.validate(self.fixture)

    def test_manifest_fixture(self):
        schema = read_json("schematics/json/artifact-manifest.schema.json")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(
            read_json("tests/fixtures/artifact-manifest.json"))

    def test_rejects_unsupported_or_unbounded_container(self):
        for key, value in [
            ("slice_version", 2), ("archive", "zip"),
            ("compression", "gzip"), ("payload", "../payload/"),
            ("payload_entries", -1), ("payload_entries", 1000001),
            ("payload_bytes", 1099511627777), ("unknown", True),
        ]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.fixture)
                data[key] = value
                self.assertFalse(self.validator.is_valid(data))

    def test_requires_each_manifest_binding(self):
        for key in ("path", "artifact_id", "size"):
            with self.subTest(key=key):
                data = copy.deepcopy(self.fixture)
                del data["manifest"][key]
                self.assertFalse(self.validator.is_valid(data))

    def test_rejects_invalid_manifest_binding(self):
        for key, value in [
            ("path", "../manifest.json"), ("artifact_id", "sha256:1234"),
            ("size", 0), ("size", 16777217), ("unknown", True),
        ]:
            with self.subTest(key=key, value=value):
                data = copy.deepcopy(self.fixture)
                data["manifest"][key] = value
                self.assertFalse(self.validator.is_valid(data))


if __name__ == "__main__":
    unittest.main()
