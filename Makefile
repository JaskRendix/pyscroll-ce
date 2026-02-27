PACKAGE_NAME := pyscroll

.PHONY: build clean publish install lint format test

build:
	python3 -m build

clean:
	rm -rf dist/ *.egg-info

publish: build
	python3 -m twine upload --repository pypi dist/*

install:
	pip install -e .

lint:
	-python -m ruff check . --fix
	python -m ruff format .

test:
	pytest tests/
