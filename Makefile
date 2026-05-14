.PHONY: help dev test lint format typecheck all clean run sim deploy-prep

PYTHON ?= python3.12
VENV   ?= .venv

help:
	@echo "NeoMakerViGate — Maker Việt × Dế Foundation"
	@echo ""
	@echo "  make dev          Tạo venv + cài deps (macOS)"
	@echo "  make run          Chạy app với webcam thật"
	@echo "  make sim          Chạy app với VisionSimulator (không cần webcam)"
	@echo "  make test         pytest unit + integration"
	@echo "  make lint         ruff check"
	@echo "  make format       ruff format"
	@echo "  make typecheck    mypy strict"
	@echo "  make all          format + lint + typecheck + test"
	@echo "  make clean        Xóa caches"
	@echo "  make deploy-prep  Tạo tarball cho NEO One"

dev:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"
	@echo ""
	@echo "Done. Activate: source $(VENV)/bin/activate"

run:
	$(VENV)/bin/python -m neo_makervigate

sim:
	NEO_MAKERVIGATE_VISION=simulator $(VENV)/bin/python -m neo_makervigate

test:
	$(VENV)/bin/pytest tests/unit tests/integration -v

lint:
	$(VENV)/bin/ruff check src tests

format:
	$(VENV)/bin/ruff format src tests
	$(VENV)/bin/ruff check --fix src tests

typecheck:
	$(VENV)/bin/mypy src

all: format lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

deploy-prep:
	@echo "Tạo tarball cho NEO One..."
	tar --exclude='.venv' --exclude='__pycache__' --exclude='.git' \
	    --exclude='models/qwen/*.gguf' --exclude='models/whisper' --exclude='models/piper' \
	    --exclude='.pytest_cache' --exclude='.mypy_cache' --exclude='.ruff_cache' \
	    -czf neo-makervigate-$$(date +%Y%m%d).tar.gz .
	@ls -lh neo-makervigate-*.tar.gz | tail -1
