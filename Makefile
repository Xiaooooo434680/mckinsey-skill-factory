.PHONY: install test lint typecheck build-example evolve-example schemas clean

install:
	pip install -e '.[dev]'

test:
	pytest -q

lint:
	ruff check src tests

typecheck:
	mypy src

build-example:
	skill-factory build examples/sales-opportunity/request.yaml --output dist/base

evolve-example: build-example
	skill-factory modify dist/base/sales-opportunity-diagnosis examples/evolution/change-request.yaml --output dist/evolved

schemas:
	skill-factory schema --output schemas/skill-request.schema.json
	skill-factory evolution-schema --output schemas/change-request.schema.json

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
