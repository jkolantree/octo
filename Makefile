.PHONY: help test check audit build clean

help:
	@echo "test   Run the complete source test suite"
	@echo "check  Run release-integrity checks"
	@echo "audit  Run the worked positive and negative examples"
	@echo "build  Build wheel and source distribution"

test:
	python scripts/run_tests.py

check: test
	python scripts/check_release.py

audit:
	python run_audit.py audit examples/claim_valid.json
	! python run_audit.py audit examples/claim_arithmetic_no_go.json

build: check
	python scripts/build_dist.py

clean:
	python scripts/clean_build.py
