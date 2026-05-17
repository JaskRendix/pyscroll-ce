PACKAGE_NAME := pyscroll

.PHONY: benchmark build clean publish install lint fix format test all

benchmark:
	@echo "Running all benchmarks in benchmark/"
	@for file in benchmark/*.py; do \
		echo "----------------------------------------"; \
		echo "Running $$file"; \
		python $$file; \
	done

build:
	python3 -m build

clean:
	rm -rf dist/ *.egg-info

publish: build
	python3 -m twine upload --repository pypi dist/*

install:
	pip install -e .

lint:
	ruff check .

fix:
	ruff check . --fix --unsafe-fixes

format:
	ruff format .

test:
	pytest tests/

all: fix format lint
