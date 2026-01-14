# CLAUDE.md - Контекст проекта gramax-sync для Claude Code

## Обзор проекта

**gramax-sync** — CLI-инструмент для синхронизации и управления множеством Git-репозиториев проекта РИТМ (Gramax). Инструмент позволяет выполнять массовые операции clone, pull, commit, push для всех репозиториев, определённых в конфигурационном файле `workspace.yaml`.

| Характеристика | Значение |
|----------------|----------|
| Версия | 0.1.0 (MVP) |
| Статус | Готов к использованию |
| Язык | Python 3.10+ |
| Лицензия | MIT |
| Платформы | macOS (primary), Linux, Windows |

## Быстрый старт

```bash
# Настройка окружения разработки
make setup
source .venv/bin/activate

# Проверка установки
gramax-sync --help
gramax-sync --version

# Запуск тестов и проверок
make test        # Тесты с покрытием
make check       # Форматирование + линтинг + типы
make format      # Автоформатирование кода
```

## Архитектура

### Структура проекта

```
gramax-sync/
├── gramax_sync/                  # Основной код
│   ├── auth/                     # Аутентификация
│   │   ├── token_manager.py      # Управление токенами через keyring
│   │   └── oauth.py              # OAuth2 flow
│   ├── cli/                      # CLI команды (Click)
│   │   ├── __init__.py           # Регистрация команд
│   │   ├── main.py               # clone, status, pull, commit, push, sync
│   │   ├── auth.py               # login, status, logout, refresh
│   │   ├── edit.py               # show, add, remove, set-workspace-dir
│   │   ├── init.py               # Первоначальная настройка
│   │   └── update.py             # Обновление конфигурации с сервера
│   ├── config/                   # Конфигурация
│   │   ├── models.py             # Pydantic модели (LocalConfig, Workspace, Section, Catalog)
│   │   ├── local_config.py       # Класс LocalConfig с YAML-сериализацией
│   │   ├── config_manager.py     # Persistence (~/.config/gramax-sync/config.yaml)
│   │   └── parser.py             # Парсер workspace.yaml
│   ├── core/                     # Dependency Injection
│   │   ├── protocols.py          # Интерфейсы (Protocol)
│   │   └── adapters.py           # Реализации протоколов
│   ├── git/                      # Git операции
│   │   ├── operations.py         # clone, pull, commit, push
│   │   └── status.py             # Определение статуса репозитория
│   ├── gitlab/                   # GitLab API
│   │   ├── client.py             # Обёртка над python-gitlab
│   │   └── exceptions.py         # GitLab-специфичные исключения
│   ├── mcp/                      # Model Context Protocol
│   │   ├── server.py             # FastMCP сервер
│   │   └── tools.py              # 7 MCP-инструментов для Claude Desktop
│   ├── utils/                    # Утилиты
│   │   ├── logging.py            # Структурированное JSON-логирование
│   │   ├── output.py             # Rich-форматирование терминала
│   │   └── selection.py          # Интерактивный выбор секций/каталогов
│   ├── workspace/                # Управление workspace
│   │   └── manager.py            # Структура директорий
│   └── exceptions.py             # Иерархия исключений
├── tests/                        # Тесты (pytest)
├── pyproject.toml                # Конфигурация проекта
├── Makefile                      # Команды разработки
└── [документация .md]
```

### Многослойная архитектура

```
┌─────────────────────────────────────┐
│   PRESENTATION LAYER                │
│   gramax_sync/cli/                  │
│   - Click CLI команды               │
│   - Rich форматирование             │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   BUSINESS LOGIC LAYER              │
│   gramax_sync/workspace/            │
│   gramax_sync/config/               │
│   - Оркестрация операций            │
│   - Валидация данных                │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   DATA ACCESS LAYER                 │
│   gramax_sync/git/                  │
│   gramax_sync/gitlab/               │
│   gramax_sync/auth/                 │
│   - Git операции (GitPython)        │
│   - GitLab API (python-gitlab)      │
│   - Токены (keyring)                │
└─────────────────────────────────────┘
```

### Dependency Injection

Проект использует Protocol-based DI для тестируемости:

```python
# gramax_sync/core/protocols.py
class ConfigManagerProtocol(Protocol):
    def load_config(self) -> LocalConfig | None: ...
    def save_config(self, config: LocalConfig) -> None: ...

# gramax_sync/core/adapters.py
class ConfigManagerAdapter:
    # Реализация протокола
```

### Иерархия исключений

```python
GramaxSyncError (base)
├── ConfigurationError    # Ошибка конфигурации
├── GitOperationError     # Ошибка Git операции
├── AuthenticationError   # Ошибка аутентификации
├── WorkspaceError        # Ошибка workspace
└── ValidationError       # Ошибка валидации данных
```

Все исключения содержат `context: dict` для дополнительной информации.

## Принципы разработки

### Типизация

- **Строгий режим mypy** (`disallow_untyped_defs`, `strict_equality`)
- Все функции и методы имеют type hints
- Используются `Protocol` для интерфейсов
- Избегайте `Any` — используйте конкретные типы

### Форматирование

- **Black**: длина строки 100 символов
- **Ruff**: линтинг и исправление ошибок
- **isort**: сортировка импортов (через ruff)

### Тестирование

- **pytest** с coverage (минимум 80%)
- Маркеры: `unit`, `integration`, `cli`, `gitlab`, `oauth`
- Моки для внешних зависимостей через патчинг модулей

```python
# Правильный патч для CLI тестов
@patch("gramax_sync.config.config_manager.require_config")  # Патчим исходный модуль
def test_command(mock_require_config):
    ...
```

### Логирование

Структурированное JSON-логирование с фильтрацией чувствительных данных:

```python
from gramax_sync.utils.logging import StructuredLogger

logger = StructuredLogger(__name__)
logger.info("operation", user_id="123", action="clone")
```

## CLI команды

### Основные команды

```bash
gramax-sync init                     # Первоначальная настройка
gramax-sync clone                    # Клонирование всех репозиториев
gramax-sync status                   # Статус всех репозиториев
gramax-sync pull                     # Обновление репозиториев
gramax-sync commit [-m "message"]    # Коммит изменений
gramax-sync push [--force]           # Push изменений
gramax-sync sync [--dry-run]         # pull + commit + push
```

### Фильтрация

Все команды поддерживают glob-паттерны:

```bash
gramax-sync status --section "1-*"
gramax-sync commit --catalog "ritm-*" -m "Update"
```

### Управление конфигурацией

```bash
gramax-sync edit show                       # Показать конфигурацию
gramax-sync edit add --section X --catalog Y
gramax-sync edit remove --section X
gramax-sync edit set-workspace-dir          # Изменить директорию
gramax-sync update                          # Обновить с сервера
```

### Аутентификация

```bash
gramax-sync auth login --oauth              # OAuth через браузер
gramax-sync auth login --pat                # Personal Access Token
gramax-sync auth status                     # Проверить токен
gramax-sync auth refresh                    # Обновить токен
gramax-sync auth logout                     # Удалить токен
```

## Конфигурация

### Локальная конфигурация

Файл: `~/.config/gramax-sync/config.yaml`

```yaml
repo_url: https://gitlab.example.com/repo
config_branch: master      # Ветка для workspace.yaml
catalog_branch: private    # Ветка для репозиториев
base_url: https://gitlab.example.com
workspace_dir: ~/ritm-workspace
sections:
  - name: section-name
    catalogs:
      - name: catalog-name
        source:
          url: https://gitlab.example.com/catalog
```

### Переменные окружения

```bash
GRAMAX_OAUTH_APPLICATION_ID  # OAuth Application ID для аутентификации
```

## Рекомендации для аудита

### Безопасность

1. **Хранение токенов** ([auth/token_manager.py](gramax_sync/auth/token_manager.py))
   - Токены хранятся в системном keyring
   - Проверить fallback на небезопасное хранение
   - Фильтрация токенов в логах

2. **Валидация URL** ([gitlab/client.py](gramax_sync/gitlab/client.py))
   - Проверка URL перед операциями
   - Защита от URL injection

3. **Git операции** ([git/operations.py](gramax_sync/git/operations.py))
   - Проверка путей перед операциями
   - Обработка конфликтов

### Качество кода

1. **Типизация** — запустить `make type-check` и исправить ошибки
2. **Тесты** — проверить покрытие критических путей
3. **Edge cases** — пустые конфигурации, несуществующие пути, сетевые ошибки

### Производительность

1. **Последовательные операции** — все Git-операции выполняются последовательно
2. **Потенциал для asyncio** — clone/pull могут выполняться параллельно

## Направления развития

### Приоритетные

- [ ] **Параллельное выполнение** операций через asyncio/ThreadPoolExecutor
- [ ] **Улучшение обработки конфликтов** при pull (auto-stash, merge strategies)
- [ ] **CI/CD pipeline** (GitHub Actions)
- [ ] **Публикация в PyPI**

### Желательные

- [ ] Расширение MCP tools (resource listing, file editing)
- [ ] Поддержка GitHub/Bitbucket (абстракция над GitLab-specific кодом)
- [ ] Dry-run режим для всех команд
- [ ] Интерактивный режим выбора файлов для commit
- [ ] Webhooks для автоматической синхронизации

### Технический долг

- [ ] Унифицировать обработку ошибок в CLI командах
- [ ] Добавить retry logic для сетевых операций
- [ ] Улучшить покрытие тестами MCP модуля

## Критические файлы

Файлы для приоритетного изучения при работе с проектом:

| Файл | Описание |
|------|----------|
| [gramax_sync/cli/main.py](gramax_sync/cli/main.py) | Основные CLI команды |
| [gramax_sync/config/models.py](gramax_sync/config/models.py) | Pydantic модели данных |
| [gramax_sync/git/operations.py](gramax_sync/git/operations.py) | Git операции |
| [gramax_sync/gitlab/client.py](gramax_sync/gitlab/client.py) | GitLab API клиент |
| [gramax_sync/core/protocols.py](gramax_sync/core/protocols.py) | DI интерфейсы |
| [gramax_sync/exceptions.py](gramax_sync/exceptions.py) | Иерархия исключений |
| [gramax_sync/mcp/tools.py](gramax_sync/mcp/tools.py) | MCP инструменты |
| [pyproject.toml](pyproject.toml) | Конфигурация проекта |

## Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| click | >=8.1.0 | CLI framework |
| gitpython | >=3.1.0 | Git операции |
| rich | >=13.0.0 | Терминальный вывод |
| pydantic | >=2.0.0 | Валидация данных |
| pyyaml | >=6.0 | YAML парсинг |
| python-gitlab | >=4.0.0 | GitLab API |
| keyring | >=24.0.0 | Хранение токенов |
| fastmcp | >=0.9.0 | MCP сервер |

## Команды разработки

```bash
make setup       # Настроить проект с нуля
make test        # Запустить тесты с покрытием
make test-fast   # Быстрые тесты без coverage
make check       # Проверить форматирование, линтинг, типы
make format      # Автоформатирование кода
make type-check  # Проверка типов (mypy)
make lint        # Линтинг (ruff)
make clean       # Очистить временные файлы
make ci          # Полная проверка для CI
```

## Дополнительная документация

- [README.md](README.md) — Пользовательская документация
- [DEVELOPMENT.md](DEVELOPMENT.md) — Руководство разработчика
- [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) — Принципы архитектуры
- [OAUTH_SETUP.md](OAUTH_SETUP.md) — Настройка OAuth
- [MCP_SETUP.md](MCP_SETUP.md) — Настройка MCP для Claude Desktop
- [TOKEN_PERMISSIONS.md](TOKEN_PERMISSIONS.md) — Права токенов GitLab
