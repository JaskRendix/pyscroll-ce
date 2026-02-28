PACKAGE_NAME := pyscroll

.PHONY: build clean publish install lint fix format test all

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
