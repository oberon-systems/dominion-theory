# Developer entry points for dominion-theory. Run `make help` for the target list.

PROJECT := dominion-theory
PYTHON  ?= python3.14
VENV    ?= .venv
PORT    ?= 8000
PIP     := $(VENV)/bin/pip

# lint reads NUL-separated names with `read -d`, which dash's read lacks.
SHELL := /bin/bash

# Hook environments live in the repository, not in ~/.cache/pre-commit.
export PRE_COMMIT_HOME := $(CURDIR)/.pre-commit

.DEFAULT_GOAL := shell

.PHONY: help install lint test run watch map clean shell

help:  ## Show the available targets
	@echo "$(PROJECT)"
	@echo
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-10s %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)

# A venv made through a symlink to a standalone interpreter cannot find its
# standard library, so the interpreter is called by its resolved path.
install:  ## Create the virtualenv, install the tooling and the game, wire up the hooks
	"$$(readlink -f "$$(command -v $(PYTHON))")" -m venv --prompt $(PROJECT) $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	$(VENV)/bin/pre-commit install
	@stty sane 2> /dev/null; tput cnorm 2> /dev/null; true

# --all-files sees only what git tracks; this adds untracked files not ignored
# and drops tracked ones deleted from the tree, which hooks cannot open.
lint:  ## Run the pre-commit hooks over every file
	@git ls-files -z --cached --others --exclude-standard | \
	while IFS= read -r -d '' f; do [ -e "$$f" ] && printf '%s\0' "$$f"; done | \
	xargs -0 $(VENV)/bin/pre-commit run --files

test:  ## Run the test suite
	$(VENV)/bin/pytest -q

run:  ## Start the server on the loopback address
	$(VENV)/bin/uvicorn --factory dominion_theory.api:create_app --host 127.0.0.1 --port $(PORT)

# WATCH carries options of the client: make watch WATCH='--lang ru --step --updates 50'
watch:  ## Watch a new game on the running server, a line per update
	$(VENV)/bin/python -m dominion_theory.client watch --server http://127.0.0.1:$(PORT) $(WATCH)

map:  ## Generate a map and show it in a window
	$(VENV)/bin/python -m dominion_theory.planet.tools simple

clean:  ## Remove the virtualenv, the hook environments and the build output
	rm -rf $(VENV) .pre-commit build dist src/*.egg-info

shell:  ## Open an interactive subshell with the virtualenv activated
	@rc="$$(mktemp)"; \
	trap 'rm -f "$$rc"' EXIT; \
	cat ~/.bashrc 2> /dev/null > "$$rc" || true; \
	echo 'export PRE_COMMIT_HOME="$(PRE_COMMIT_HOME)"' >> "$$rc"; \
	echo 'source $(CURDIR)/$(VENV)/bin/activate' >> "$$rc"; \
	bash --rcfile "$$rc" -i || true
