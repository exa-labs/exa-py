.PHONY: test test-unit test-integration test-all

test:
	uv run pytest tests/

test-unit:
	uv run pytest tests/unit/

test-integration:
	uv run pytest tests/integration/

test-all:
	uv run pytest tests/

