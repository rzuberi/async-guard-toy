PYTHON ?= python3

.PHONY: run test

run:
	$(PYTHON) scripts/run_all.py

test:
	$(PYTHON) -m pytest
