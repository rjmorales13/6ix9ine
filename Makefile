# Makefile for 6ix9ine Build Optimization and Release Automation

.PHONY: all build release clean test

all: build

build:
	./build.sh

release:
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. E.g., 'make release VERSION=1.0.0'"; \
		exit 1; \
	fi
	./build.sh $(VERSION)

clean:
	rm -rf build dist *.spec

test:
	.venv313/bin/pytest || .venv/bin/pytest
