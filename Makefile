# Developer entry points for dominion-theory. Run `make help` for the target list.

PROJECT := dominion-theory
PYTHON  ?= python3.14
VENV    ?= .venv
PORT    ?= 8000
SEEDS   ?= 1 2 3 4 5
PRESETS ?= pangea continents archipelago dune
STAMP   := $(shell date +%Y%m%d-%H%M%S)
MAPS    ?= maps/$(STAMP)
MAPPED  := tests/planet/maps.json
MAPS_TEST := tests/planet/test_maps.py
LIVES   ?= lives/$(STAMP)
LIVED   := tests/runner/lives.json
LIVES_TEST := tests/runner/test_lives.py
PIP     := $(VENV)/bin/pip
CZ      := $(VENV)/bin/cz

# lint reads NUL-separated names with `read -d`, which dash's read lacks.
SHELL := /bin/bash

# Hook environments live in the repository, not in ~/.cache/pre-commit.
export PRE_COMMIT_HOME := $(CURDIR)/.pre-commit

.DEFAULT_GOAL := shell

.PHONY: help install lint test run watch live lives map planet maps bump major release-rc release clean shell $(PRESETS:%=planet-%) $(PRESETS:%=map-%)

help:  ## Show the available targets
	@echo "$(PROJECT)"
	@echo
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  %-10s %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)
	@for preset in $(PRESETS); do \
		printf "  %-20s %s\n" "planet-$$preset" "Draw the whole planet of the preset $$preset"; \
		printf "  %-20s %s\n" "map-$$preset" "Draw the first window of the preset $$preset"; \
	done

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

# Code first: a failing test stops the run before any map is built. Then, if the planet
# changed, its reference is rewritten and the maps are drawn; then, if the band changed,
# its seeds are lived again. The tests of both references come last.
test:  ## Run the tests of the code, then redo the maps and the lives of the band where they changed
	$(VENV)/bin/pytest -q --ignore=$(MAPS_TEST) --ignore=$(LIVES_TEST)
	@$(VENV)/bin/python -m dominion_theory.planet.tools.reference $(MAPPED) \
		|| $(MAKE) --no-print-directory maps
	$(VENV)/bin/pytest -q $(MAPS_TEST)
	@$(VENV)/bin/python -m dominion_theory.runner.lives --check $(LIVED) \
		|| $(MAKE) --no-print-directory lives
	$(VENV)/bin/pytest -q $(LIVES_TEST)

run:  ## Start the server on the loopback address
	$(VENV)/bin/uvicorn --factory dominion_theory.api:create_app --host 127.0.0.1 --port $(PORT)

# WATCH carries options of the client: make watch WATCH='--lang ru --step --updates 50'
watch:  ## Watch a new game on the running server, a line per update
	$(VENV)/bin/python -m dominion_theory.client watch --server http://127.0.0.1:$(PORT) $(WATCH)

# LIVE carries options of the command: make live SEEDS='7 42' LIVE='--years 20 --set encounters.chance=0'
live:  ## Live a game with no player for every seed of SEEDS, a row per year from its counters
	@for seed in $(SEEDS); do \
		$(VENV)/bin/python -m dominion_theory.client live --seed $$seed $(LIVE) || exit 1; \
	done

lives:  ## Live the reference seeds of the band anew, rewrite their reference, the tables into LIVES/report.txt
	$(VENV)/bin/python -m dominion_theory.runner.lives $(LIVED) --out $(LIVES)

# MAP carries options of the tool: make map MAP='--seed 42 --planet --out ../alpha.png'
map:  ## Draw the first window of a seed, in a window or into a file
	$(VENV)/bin/python -m dominion_theory.planet.tools $(MAP)

planet:  ## Draw the whole planet of a seed, with the first window outlined; takes MAP as map does
	$(VENV)/bin/python -m dominion_theory.planet.tools --planet $(MAP)

# One target for every preset of PRESETS: make planet-dune, make map-pangea MAP='--seed 42'.
$(PRESETS:%=planet-%): planet-%:
	$(VENV)/bin/python -m dominion_theory.planet.tools --planet --preset $* $(MAP)

$(PRESETS:%=map-%): map-%:
	$(VENV)/bin/python -m dominion_theory.planet.tools --preset $* $(MAP)

# For tuning: make maps SEEDS='7 8' PRESETS= MAPS=maps/alpha MAP='--set planet.sea=0.5'
maps:  ## Write the planet and the first window as pictures, timed: the default and every preset of PRESETS
	@mkdir -p $(MAPS)
	@export PYGAME_HIDE_SUPPORT_PROMPT=1; for kind in default $(PRESETS); do \
		preset=; name=; \
		[ $$kind = default ] || { preset="--preset $$kind"; name="$$kind-"; }; \
		for seed in $(SEEDS); do \
			for view in planet window; do \
				[ $$view = planet ] && whole=--planet || whole=; \
				SECONDS=0; \
				$(VENV)/bin/python -m dominion_theory.planet.tools --seed $$seed $$whole $$preset \
					--out $(MAPS)/$$name$$view-$$seed.png $(MAP); \
				echo "$$name$$view of seed $$seed took $$SECONDS s"; \
			done; \
		done; \
	done 2>&1 | tee $(MAPS)/report.txt

# Versions are 0.MILESTONE.PATCH until 1.0.0: 0.1 is the band era with the console client, 0.2 the web.
# A bump shows its dry run first and asks; .cz.yaml refuses a cz bump that does not come from here.
define bump
	@$(CZ) bump --yes --changelog --dry-run $(1) && \
	read -r -p 'Bump the version as shown above? [N/y] ' answer && \
	if [ "$$answer" = y ] || [ "$$answer" = Y ]; then DT_BUMP=make $(CZ) bump --yes --changelog $(1); \
	else echo 'Nothing was bumped.'; fi
endef

bump:  ## Bump the patch of the version, write the changelog, commit and tag, after a dry run
	$(call bump,--increment PATCH)

major:  ## Bump the milestone of the version (0.1, 0.2 and on), after a dry run
	$(call bump,--increment MINOR)

# Closed until the game is ready for 1.0.0; opening it also turns major_version_zero off in .cz.yaml.
release-rc:  ## Bump to the next candidate of 1.0.0: rc0, rc1 and on (closed for now)
	@echo 'release-rc is closed until the game is ready for 1.0.0' >&2; exit 1
	$(call bump,--increment MAJOR --prerelease rc)

release:  ## Bump the major version: 1.0.0 and on (closed for now)
	@echo 'release is closed until the game is ready for 1.0.0' >&2; exit 1
	$(call bump,--increment MAJOR)

clean:  ## Remove the virtualenv, the hook environments and the build output
	rm -rf $(VENV) .pre-commit build dist src/*.egg-info

shell:  ## Open an interactive subshell with the virtualenv activated
	@rc="$$(mktemp)"; \
	trap 'rm -f "$$rc"' EXIT; \
	cat ~/.bashrc 2> /dev/null > "$$rc" || true; \
	echo 'export PRE_COMMIT_HOME="$(PRE_COMMIT_HOME)"' >> "$$rc"; \
	echo 'source $(CURDIR)/$(VENV)/bin/activate' >> "$$rc"; \
	bash --rcfile "$$rc" -i || true
