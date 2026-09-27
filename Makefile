# Optional convenience layer. Python owns the recipes on every host.
PYTHON ?= python3
.PHONY: help doctor configure build test check format format-check tidy docker-check docker-sanitized simulator simulator-demo audit-build
help:
	$(PYTHON) dev.py --help
doctor configure build test check format format-check tidy audit-build:
	$(PYTHON) dev.py $@
docker-check:
	$(PYTHON) dev.py docker check
docker-sanitized:
	$(PYTHON) dev.py docker check --sanitizers
simulator:
	$(PYTHON) dev.py simulator open
simulator-demo:
	$(PYTHON) dev.py simulator demo
