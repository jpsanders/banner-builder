SRC := src
TESTS := tests
ROOT_EC_FILES := $(wildcard *.yaml *.yml *.md) .github
PACKAGE := banner_builder

.PHONY: help
help:
	@echo "Available targets:"
	@grep -E "^([a-zA-Z_-]+):.*" $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":"}; {printf "    \033[36m%s\n\033[0m", $$1}'
	@echo ""
	@echo "Hints:"
	@echo "    Use '-n' to do a dry run"
	@echo "    Use '-k' to ignore failed targets and keep going"

.PHONY: init
init:
	@echo
	pip install -e .

.PHONY: init-dev
init-dev:
	@echo
	pip install -e .[dev]

.PHONY: format
format: black isort

.PHONY: isort-check
isort-check:
	@echo
	@echo --- Isort check ---
	isort --check --diff ${SRC} ${TESTS}

.PHONY: isort
isort:
	@echo
	@echo --- Isort auto format ---
	isort ${SRC} ${TESTS}

.PHONY: black-check
black-check:
	@echo
	@echo --- Black check ---
	black --check --diff ${SRC} ${TESTS}

.PHONY: black
black:
	@echo
	@echo --- Black auto format ---
	black ${SRC} ${TESTS}

.PHONY: ec
ec:
	@echo
	@echo --- Editorconfig linting checks ---
	ec ${SRC} ${TESTS} ${ROOT_EC_FILES}

.PHONY: docstyle
docstyle:
	@echo
	@echo --- Darglint docstring checks ---
	darglint -v 2 ${SRC} ${TESTS}

.PHONY: lint
lint:
	@echo
	@echo --- Flake8 linting checks ---
	flake8 ${SRC} ${TESTS}

.PHONY: mypy
mypy:
	@echo
	@echo --- Mypy type checks ---
	mypy ${SRC} ${TESTS}

.PHONY: pytest
pytest:
	@echo
	@echo --- Pytest regression and unit tests ---
	pytest --cov ${SRC}/${PACKAGE} ${TESTS}

.PHONY: bandit
bandit:
	@echo
	@echo --- Bandit security checks ---
	bandit -c pyproject.toml -f custom -r ${SRC} ${TESTS}

.PHONY: build
build: clean
	@echo
	@echo --- Build package wheel ---
	python -m build -o build/dist

# Redraw the README images from the starter config
.PHONY: examples
examples:
	@echo
	@echo --- Example banners ---
	banner-builder build --config ${SRC}/${PACKAGE}/example.toml --out docs --format png --scale 1

.PHONY: clean
clean:
	@echo
	rm -rf build/
	find ${SRC} ${TESTS} | grep -E "(\.egg-info|__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

# Run all checking tools
.PHONY: checks
checks: isort-check black-check ec docstyle lint mypy bandit pytest
