.PHONY: install test test-unit test-integration

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-test.txt

test: test-unit

test-unit:
	.venv/bin/pytest test_unit.py -v

test-integration:
	.venv/bin/pytest test_integration.py -v

test-all: test-unit test-integration
