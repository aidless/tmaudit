.PHONY: install test demo figures repro clean

install:
	python3 -m pip install -e .

test:
	python3 -m pytest -q

# runs the shipped rulepack on the deliberately flawed sample manuscript
demo:
	python3 -m tmaudit.cli verify --paper-dir examples/sample-paper
	rm -f examples/sample-paper/verify_generic.py

figures:
	python3 scripts/make_corpus_figure.py

# one command: everything the README claims, offline
repro: install test demo figures

clean:
	rm -f examples/sample-paper/verify_generic.py figures/corpus_fire_rates.png
