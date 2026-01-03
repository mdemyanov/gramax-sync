.PHONY: help install install-dev test test-cov lint format type-check clean venv setup

help: ## Показать справку по командам
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Создать виртуальное окружение
	python3 -m venv .venv
	@echo "Виртуальное окружение создано. Активируйте его: source .venv/bin/activate"

setup: venv ## Настроить проект (venv + установка зависимостей)
	.venv/bin/pip install --upgrade pip setuptools wheel
	.venv/bin/pip install -e ".[dev]"
	@echo "Проект настроен! Активируйте окружение: source .venv/bin/activate"

install: ## Установить проект в production режиме
	pip install -e .

install-dev: ## Установить проект в режиме разработки
	pip install -e ".[dev]"
	pip install pre-commit
	pre-commit install

test: ## Запустить тесты
	pytest

test-cov: ## Запустить тесты с покрытием
	pytest --cov=gramax_sync --cov-report=html --cov-report=term-missing

test-fast: ## Запустить быстрые тесты (без coverage)
	pytest --no-cov

lint: ## Проверить код линтерами
	ruff check gramax_sync tests
	mypy gramax_sync

format: ## Отформатировать код
	black gramax_sync tests
	ruff check --fix gramax_sync tests

format-check: ## Проверить форматирование (без изменений)
	black --check gramax_sync tests
	ruff check gramax_sync tests

type-check: ## Проверить типы
	mypy gramax_sync

check: format-check lint type-check ## Проверить всё (форматирование, линт, типы)

clean: ## Очистить временные файлы
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -r {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
	@echo "Временные файлы очищены"

clean-all: clean ## Очистить всё включая виртуальное окружение
	rm -rf .venv
	@echo "Виртуальное окружение удалено"

ci: ## Запустить все проверки (для CI)
	pytest --cov=gramax_sync --cov-report=xml --cov-report=term
	black --check gramax_sync tests
	ruff check gramax_sync tests
	mypy gramax_sync

