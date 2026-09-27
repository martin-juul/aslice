"""Acceptance reports backed by reviewed records in tests/requirements."""
from .requirements import ROOT, evaluate


def report():
    return evaluate(ROOT)
