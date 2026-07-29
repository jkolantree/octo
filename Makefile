.PHONY: help test pages-check null-check privacy gpt gpt-check check audit build clean

help:
	@echo "test   Run the Python-only core verification profile"
	@echo "pages-check  Run the bounded Pages verification profile"
	@echo "null-check  Run the adversarial Null-Discrimination suite"
	@echo "privacy  Run the pseudonymous-publication privacy gate"
	@echo "gpt  Regenerate the repository-backed Custom GPT package"
	@echo "gpt-check  Verify the Custom GPT package is current and deterministic"
	@echo "check  Run the complete candidate verification profile"
	@echo "audit  Run the worked positive and negative examples"
	@echo "build  Build wheel and source distribution"

test:
	python scripts/verify.py core

pages-check:
	python scripts/verify.py pages

null-check:
	python scripts/run_null_discrimination.py

privacy:
	python scripts/check_privacy.py --protected-history HEAD

gpt:
	python scripts/build_gpt_package.py

gpt-check:
	python scripts/build_gpt_package.py --check
	python scripts/check_gpt_package.py

check:
	python scripts/verify.py candidate

audit:
	! python run_audit.py audit examples/claim_valid.json
	! python run_audit.py audit examples/claim_arithmetic_no_go.json
	python run_audit.py theorem examples/theorem_binomial_identity.json
	python run_audit.py audit examples/claim_polynomial_identity.json

build: check
	python scripts/build_dist.py

clean:
	python scripts/clean_build.py
