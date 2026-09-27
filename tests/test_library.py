"""Compatibility discovery for the relocated archive tests."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "library_archive_tests",
    Path(__file__).resolve().parents[1] / "docs/library/.harness/tests/test_archive.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
LibraryTests = module.LibraryTests

if __name__ == '__main__':
    import unittest
    unittest.main()
