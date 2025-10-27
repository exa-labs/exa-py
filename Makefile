.PHONY: test test-unit test-integration help

help:
	@echo "Available commands:"
	@echo "  make test              - Run all tests (unit + integration)"
	@echo "  make test-unit         - Run only unit tests (no API key needed)"
	@echo "  make test-integration  - Run only integration tests (requires EXA_API_KEY)"

# Run all tests
test:
	uv run pytest tests/

# Run only unit tests (no API key needed, fast)
test-unit:
	uv run pytest tests/unit/ -v

# Run only integration tests (requires EXA_API_KEY)
test-integration:
	uv run pytest tests/integration/ -v

