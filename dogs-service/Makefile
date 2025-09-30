.PHONY: help build deploy local-start local-stop setup-local test-unit test-integration fmt lint clean

SHELL := /bin/bash
PROJECT_ROOT := $(shell pwd)
SAM_FLAGS :=
PYTEST := python -m pytest

help:
	@echo "Usage:"
	@echo "  make build            # sam build"
	@echo "  make deploy           # sam deploy --guided (first time) or sam deploy"
	@echo "  make local-start      # start sam local API"
	@echo "  make setup-local      # setup local resources (LocalStack)"
	@echo "  make test-unit        # run unit tests"
	@echo "  make test-integration # run integration tests"

build:
	sam build $(SAM_FLAGS)

deploy:
	sam deploy $(SAM_FLAGS)

local-start:
	sam local start-api --skip-pull-image

local-stop:
	@echo "Stop the local server with Ctrl-C or kill the process"

setup-local:
	./scripts/setup_local.sh

test-unit:
	$(PYTEST) tests/unit -q

test-integration:
	$(PYTEST) tests/integration -q

fmt:
	black .

lint:
	flake8 .

clean:
	rm -rf .aws-sam build