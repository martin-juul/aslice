"""Compatibility entrypoints for the documentation library harness."""

import importlib
import importlib.util
from pathlib import Path
import sys


def _backend(name):
    package = "_aslice_library_backend"
    if package not in sys.modules:
        directory = Path(__file__).resolve().parents[2] / "docs/library/.harness/backend"
        spec = importlib.util.spec_from_file_location(
            package, directory / "__init__.py",
            submodule_search_locations=[str(directory)],
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[package] = module
        spec.loader.exec_module(module)
    return importlib.import_module(f"{package}.{name}")
