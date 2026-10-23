.PHONY: install test build-all
install:
	python -m pip install -r requirements.txt
test:
	python -m pytest -q
build-all: test
	python -m proof.parallel_pop
	python -m proof.universe_manifest
