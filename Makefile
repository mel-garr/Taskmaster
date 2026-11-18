
.PHONY: all run test clean

PYTHON = python3

all: run

run:
	$(PYTHON) -m src.main

test:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
