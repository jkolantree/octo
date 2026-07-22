.PHONY: help test null-check privacy gpt gpt-check check audit build clean

help:
	@echo "test   Run the complete source test suite"
	@echo "null-check  Run the adversarial Null-Discrimination suite"
	@echo "privacy  Run the pseudonymous-publication privacy gate"
	@echo "gpt  Regenerate the repository-backed Custom GPT package"
	@echo "gpt-check  Verify the Custom GPT package is current and deterministic"
	@echo "check  Run release-integrity checks"
	@echo "audit  Run the worked positive and negative examples"
	@echo "build  Build wheel and source distribution"

test:
	python scripts/run_tests.py

null-check:
	python scripts/run_null_discrimination.py

privacy:
	python scripts/check_privacy.py --protected-history HEAD

gpt:
	python scripts/build_gpt_package.py

gpt-check:
	python scripts/build_gpt_package.py --check
	python scripts/check_gpt_package.py

check: test null-check privacy gpt-check
	python scripts/check_release.py

audit:
	python run_audit.py audit examples/claim_valid.json
	! python run_audit.py audit examples/claim_arithmetic_no_go.json

build: check
	python scripts/build_dist.py

clean:
	python scripts/clean_build.py
