# 🛠️ Руководство разработчика

Полное руководство по работе с проектом `gramax-sync` в режиме разработки.

## 📋 Содержание

- [Быстрый старт](#быстрый-старт)
- [Настройка окружения](#настройка-окружения)
- [Структура проекта](#структура-проекта)
- [Рабочий процесс](#рабочий-процесс)
- [Тестирование](#тестирование)
- [Отладка](#отладка)
- [Полезные команды](#полезные-команды)
- [Решение проблем](#решение-проблем)

---

## 🚀 Быстрый старт

### Минимальная настройка (5 минут)

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd gramax-sync

# 2. Настроить окружение
make setup

# 3. Активировать окружение
source .venv/bin/activate  # macOS/Linux
# или
.venv\Scripts\activate      # Windows

# 4. Проверить установку
gramax-sync --help
make test
```

### Проверка готовности

```bash
# Проверить, что всё работает
make check          # Проверка кода
make test           # Запуск тестов
gramax-sync --help  # Проверка CLI
```

---

## ⚙️ Настройка окружения

### Вариант 1: Использование Makefile (рекомендуется)

```bash
# Полная настройка проекта
make setup

# Это выполнит:
# - Создание виртуального окружения .venv
# - Установку всех зависимостей (включая dev)
# - Настройку pre-commit hooks
```

### Вариант 2: Ручная настройка

```bash
# 1. Создать виртуальное окружение
python3 -m venv .venv

# 2. Активировать окружение
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# 3. Обновить pip
pip install --upgrade pip setuptools wheel

# 4. Установить зависимости для разработки
pip install -e ".[dev]"

# 5. Установить pre-commit hooks
pip install pre-commit
pre-commit install
```

### Вариант 3: Использование uv (если установлен)

```bash
# Установить uv (если не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Настроить проект
uv sync

# Активировать окружение
source .venv/bin/activate

# Запустить команды через uv
uv run pytest
uv run gramax-sync --help
```

### Переменные окружения для тестов

Для запуска тестов необходимо установить OAuth Application ID:

```bash
# Установить переменную окружения
export GRAMAX_OAUTH_APPLICATION_ID="ваш_application_id"

# Или добавить в ~/.bashrc / ~/.zshrc для постоянного использования
echo 'export GRAMAX_OAUTH_APPLICATION_ID="ваш_application_id"' >> ~/.zshrc
```

**Примечание:** Для интеграционных тестов может потребоваться также `GRAMAX_OAUTH_APPLICATION_SECRET`.

### Использование pyenv (опционально)

Если вы используете `pyenv` для управления версиями Python:

```bash
# Установить Python 3.10+ (если не установлен)
pyenv install 3.10.13

# Установить версию для проекта
pyenv local 3.10.13

# Файл .python-version уже создан в проекте
```

---

## 📁 Структура проекта

```
gramax-sync/
├── gramax_sync/              # Основной код проекта
│   ├── __init__.py          # Точка входа CLI
│   ├── cli/                 # CLI команды
│   │   ├── __init__.py      # Регистрация команд
│   │   ├── main.py          # Основные команды (status, clone, pull, commit, push, sync)
│   │   ├── auth.py          # Команды аутентификации
│   │   ├── edit.py          # Редактирование конфигурации
│   │   ├── init.py          # Первоначальная настройка
│   │   └── update.py        # Обновление конфигурации
│   ├── config/              # Управление конфигурацией
│   │   ├── config_manager.py
│   │   ├── local_config.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── git/                 # Работа с Git
│   │   ├── operations.py    # Операции (clone, pull, commit, push)
│   │   └── status.py        # Проверка статуса репозиториев
│   ├── gitlab/              # Интеграция с GitLab
│   │   ├── client.py
│   │   └── exceptions.py
│   ├── workspace/           # Управление workspace
│   │   └── manager.py
│   ├── auth/                # Аутентификация
│   │   ├── oauth.py
│   │   └── token_manager.py
│   ├── utils/               # Утилиты
│   │   ├── output.py
│   │   └── selection.py
│   └── mcp/                 # MCP Server
│       ├── server.py
│       └── tools.py
├── tests/                   # Тесты
│   ├── conftest.py          # Pytest конфигурация и фикстуры
│   ├── test_cli/            # Тесты CLI команд
│   ├── test_config/         # Тесты конфигурации
│   ├── test_git/            # Тесты Git операций
│   ├── test_gitlab/         # Тесты GitLab интеграции
│   ├── test_auth/           # Тесты аутентификации
│   ├── test_workspace/      # Тесты workspace
│   └── test_utils/          # Тесты утилит
├── assets/                   # Примеры и ресурсы
├── scripts/                  # Вспомогательные скрипты
├── pyproject.toml           # Конфигурация проекта и зависимости
├── Makefile                 # Удобные команды для разработки
├── .pre-commit-config.yaml  # Pre-commit hooks
└── .python-version          # Версия Python для pyenv
```

### Архитектура CLI

После рефакторинга (Фаза 1) структура CLI упрощена:

- **`gramax_sync/cli/main.py`** — основные команды (`status`, `clone`, `pull`, `commit`, `push`, `sync`)
- **`gramax_sync/cli/__init__.py`** — регистрация всех команд в главную группу `cli`
- **`gramax_sync/__init__.py`** — прямой импорт `cli` (без динамической загрузки)

**Важно:** Функции в `cli/main.py` импортируются через модули для возможности патчинга в тестах:

```python
# В cli/main.py
import gramax_sync.config.config_manager as config_manager_module
require_config = config_manager_module.require_config
```

---

## 🔄 Рабочий процесс

### Ежедневная работа

1. **Активировать окружение:**
   ```bash
   source .venv/bin/activate
   ```

2. **Создать ветку для новой функции:**
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Внести изменения в код**

4. **Проверить код перед коммитом:**
   ```bash
   make check  # Форматирование, линтинг, типы
   ```

5. **Запустить тесты:**
   ```bash
   make test
   ```

6. **Закоммитить изменения:**
   ```bash
   git add .
   git commit -m "Описание изменений"
   ```
   
   Pre-commit hooks автоматически проверят код перед коммитом.

### Работа с CLI командами

#### Тестирование CLI локально

```bash
# Установить проект в режиме разработки
pip install -e .

# Проверить команду
gramax-sync --help
gramax-sync status --help

# Запустить команду (требует конфигурации)
gramax-sync init
gramax-sync status
```

#### Отладка CLI команд

```bash
# Запуск с отладкой
python -m gramax_sync.cli.main status

# Или через прямой вызов
python -c "from gramax_sync.cli.main import main_group; main_group(['status'])"
```

---

## 🧪 Тестирование

### Быстрый запуск

```bash
# Все тесты
make test

# Тесты с покрытием
make test-cov

# Быстрые тесты (без coverage)
make test-fast
```

### Типы тестов

Проект использует маркеры pytest для категоризации:

- **`unit`** — Unit тесты (быстрые, с мокированием)
- **`integration`** — Интеграционные тесты (требуют реальных сервисов)
- **`cli`** — Тесты CLI команд
- **`gitlab`** — Тесты, требующие GitLab сервер
- **`oauth`** — Тесты OAuth аутентификации

### Запуск конкретных тестов

```bash
# Все тесты
pytest tests/

# Только unit тесты
pytest tests/ -m "not integration"

# Только CLI тесты
pytest tests/ -m "cli"

# Конкретный тест
pytest tests/test_cli/test_commands.py::test_cli_status_command

# Тесты с подробным выводом
pytest tests/ -v

# Тесты с остановкой на первой ошибке
pytest tests/ -x
```

### Написание тестов для CLI команд

#### Пример: Тест команды с патчами

```python
from unittest.mock import patch
from click.testing import CliRunner
from gramax_sync import cli
import gramax_sync.cli.main

# Важно: импортировать cli.main для обновления функций
from tests.test_cli.test_commands import update_cli_main_functions

@patch("gramax_sync.config.config_manager.require_config")
@patch("gramax_sync.workspace.manager.list_repositories")
@patch("gramax_sync.git.status.get_repository_status")
def test_my_command(mock_get_status, mock_list_repos, mock_require_config):
    """Тест команды с мокированием."""
    # Настройка моков
    mock_require_config.return_value = create_test_config()
    mock_list_repos.return_value = [("section1", "catalog1", Path("/tmp/repo"))]
    mock_get_status.return_value = "clean"
    
    # Важно: обновить ссылки на функции в cli.main
    update_cli_main_functions()
    
    # Запуск команды
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    
    # Проверка результата
    assert result.exit_code == 0
    mock_get_status.assert_called()
```

#### Важные моменты при тестировании CLI

1. **Патчи должны указывать на исходные модули:**
   ```python
   # ✅ Правильно
   @patch("gramax_sync.config.config_manager.require_config")
   
   # ❌ Неправильно
   @patch("gramax_sync.cli.main.require_config")
   ```

2. **Обновление ссылок в cli.main:**
   ```python
   # После настройки моков вызвать
   update_cli_main_functions()
   ```

3. **Установка return_value для моков:**
   ```python
   # Для функций, возвращающих значения
   mock_push.return_value = 1  # Количество коммитов
   mock_commit.return_value = "abc1234"  # Хеш коммита
   mock_get_status.return_value = "modified"  # Статус репозитория
   ```

4. **Использование side_effect для последовательности значений:**
   ```python
   # Для функций, вызываемых несколько раз
   mock_get_status.side_effect = ["ahead", "ahead", "ahead"]
   ```

### Покрытие кода

```bash
# Генерация отчёта о покрытии
make test-cov

# Просмотр HTML отчёта
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Целевое покрытие:** минимум 80% для новых функций.

### Интеграционные тесты

Интеграционные тесты требуют реального GitLab сервера:

```bash
# Установить переменные окружения
export TEST_GITLAB_URL="https://itsmf.gitlab.yandexcloud.net"
export GRAMAX_OAUTH_APPLICATION_ID="ваш_id"

# Запустить интеграционные тесты
pytest tests/ -m "integration"
```

---

## 🐛 Отладка

### Отладка CLI команд

#### Вариант 1: Использование print/debug

```python
# В коде команды
import logging
logging.basicConfig(level=logging.DEBUG)

# Или через rich
from rich.console import Console
console = Console()
console.print("[debug] Значение переменной:", variable)
```

#### Вариант 2: Использование pdb

```python
# В коде команды
import pdb; pdb.set_trace()

# Или через breakpoint() (Python 3.7+)
breakpoint()
```

#### Вариант 3: Запуск через Python

```bash
# Прямой запуск модуля
python -m gramax_sync.cli.main status

# С отладчиком
python -m pdb -m gramax_sync.cli.main status
```

### Отладка тестов

```bash
# Запуск с отладчиком
pytest tests/test_cli/test_commands.py::test_cli_status_command --pdb

# Запуск с остановкой на первой ошибке
pytest tests/ -x --pdb

# Запуск с подробным выводом
pytest tests/ -vv
```

### Логирование

```python
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("Отладочное сообщение")
```

---

## 📚 Полезные команды

### Makefile команды

```bash
make help          # Показать все доступные команды
make setup         # Настроить проект с нуля
make install-dev   # Установить зависимости для разработки
make test          # Запустить тесты
make test-cov      # Тесты с покрытием
make test-fast     # Быстрые тесты (без coverage)
make lint          # Проверить код линтерами
make format        # Отформатировать код
make format-check  # Проверить форматирование (без изменений)
make type-check    # Проверить типы
make check         # Проверить всё (формат, линт, типы)
make clean         # Очистить временные файлы
make clean-all     # Очистить всё включая .venv
make ci            # Запустить все проверки (для CI)
```

### Pytest команды

```bash
# Базовые команды
pytest                    # Все тесты
pytest -v                 # Подробный вывод
pytest -x                 # Остановка на первой ошибке
pytest -k "test_name"     # Запуск тестов по имени
pytest --pdb              # Запуск отладчика при ошибке

# С покрытием
pytest --cov=gramax_sync --cov-report=html
pytest --cov=gramax_sync --cov-report=term-missing

# Фильтрация тестов
pytest -m "unit"          # Только unit тесты
pytest -m "not integration"  # Без интеграционных
pytest tests/test_cli/    # Только CLI тесты
```

### Pre-commit команды

```bash
# Запуск hooks вручную
pre-commit run --all-files

# Запуск конкретного hook
pre-commit run black --all-files
pre-commit run ruff --all-files

# Обновление hooks
pre-commit autoupdate
```

---

## 🔧 Решение проблем

### Проблемы с виртуальным окружением

**Симптом:** Ошибки импорта или неверная версия Python.

**Решение:**
```bash
# Удалить старое окружение
rm -rf .venv

# Создать заново
make setup
```

### Проблемы с зависимостями

**Симптом:** `ModuleNotFoundError` или конфликты версий.

**Решение:**
```bash
# Обновить pip
pip install --upgrade pip

# Переустановить зависимости
pip install -e ".[dev]"

# Или через uv
uv sync
```

### Проблемы с тестами

**Симптом:** `ValueError: GRAMAX_OAUTH_APPLICATION_ID не установлен!`

**Решение:**
```bash
# Установить переменную окружения
export GRAMAX_OAUTH_APPLICATION_ID="ваш_application_id"

# Или запустить тесты с переменной
GRAMAX_OAUTH_APPLICATION_ID=test pytest tests/
```

**Симптом:** Тесты не находят патченые функции.

**Решение:**
- Убедитесь, что патчи указывают на исходные модули:
  ```python
  @patch("gramax_sync.config.config_manager.require_config")  # ✅
  # Не @patch("gramax_sync.cli.main.require_config")  # ❌
  ```
- Вызовите `update_cli_main_functions()` после настройки моков.

### Проблемы с pre-commit

**Симптом:** Pre-commit hooks не работают или падают.

**Решение:**
```bash
# Обновить hooks
pre-commit autoupdate

# Запустить вручную
pre-commit run --all-files

# Переустановить hooks
pre-commit uninstall
pre-commit install
```

### Проблемы с импортами

**Симптом:** `ImportError` при запуске CLI или тестов.

**Решение:**
```bash
# Проверить установку проекта
pip list | grep gramax-sync

# Переустановить в режиме разработки
pip install -e .

# Проверить импорты
python -c "from gramax_sync import cli; print('OK')"
```

### Проблемы с типами (mypy)

**Симптом:** Ошибки типизации при запуске `make type-check`.

**Решение:**
```bash
# Запустить mypy с подробным выводом
mypy gramax_sync --show-error-codes

# Игнорировать конкретные ошибки (временно)
# В pyproject.toml добавить в [tool.mypy.overrides]
```

### Проблемы с форматированием

**Симптом:** Black или ruff находят ошибки форматирования.

**Решение:**
```bash
# Автоматически исправить
make format

# Или вручную
black gramax_sync tests
ruff check --fix gramax_sync tests
```

---

## 📖 Дополнительные ресурсы

### Документация проекта

- [README.md](README.md) — Общее описание проекта
- [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) — Универсальные правила архитектуры и принципы разработки
- [REFACTORING_PLAN.md](REFACTORING_PLAN.md) — План рефакторинга
- [TESTING.md](TESTING.md) — Подробное руководство по тестированию
- [OAUTH_SETUP.md](OAUTH_SETUP.md) — Настройка OAuth
- [MCP_SETUP.md](MCP_SETUP.md) — Настройка MCP Server

### Внешние ресурсы

- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Click Documentation](https://click.palletsprojects.com/)
- [black Documentation](https://black.readthedocs.io/)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pre-commit Documentation](https://pre-commit.com/)

---

## ✅ Чеклист перед коммитом

Перед коммитом убедитесь, что:

- [ ] Код отформатирован (`make format`)
- [ ] Линтеры проходят (`make lint`)
- [ ] Типы проверены (`make type-check`)
- [ ] Тесты проходят (`make test`)
- [ ] Новый код покрыт тестами
- [ ] Документация обновлена (если нужно)
- [ ] Pre-commit hooks проходят

---

## 🎯 Требования к коду

### Типизация

- Все публичные функции и классы должны иметь type hints
- Используйте `mypy` для проверки типов
- Избегайте `Any` без необходимости

### Форматирование

- Используйте `black` для форматирования (длина строки: 100)
- Используйте `ruff` для линтинга
- Следуйте PEP 8

### Тестирование

- Покрытие тестами должно быть минимум 80%
- Пишите unit тесты для всех функций
- Добавляйте integration тесты для сложных сценариев
- Используйте моки для внешних зависимостей

### Документация

- Все публичные функции и классы должны иметь docstrings
- Используйте Google или NumPy стиль docstrings
- Обновляйте документацию при изменении API

---

**Удачной разработки! 🚀**
