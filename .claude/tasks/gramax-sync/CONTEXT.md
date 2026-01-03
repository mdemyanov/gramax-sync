# Project Context — gramax-sync

## Архитектура

```
gramax-sync/
├── pyproject.toml           # Конфигурация проекта (Poetry/PDM)
├── README.md
├── src/
│   └── gramax_sync/
│       ├── __init__.py
│       ├── __main__.py      # Entry point: python -m gramax_sync
│       ├── cli.py           # Click CLI commands
│       ├── config.py        # Загрузка и валидация конфигурации
│       ├── git_ops.py       # Git операции (clone, pull, commit, push)
│       ├── auth.py          # GitLab OAuth / Token management
│       ├── workspace.py     # Парсинг workspace.yaml
│       ├── models.py        # Pydantic модели данных
│       ├── exceptions.py    # Кастомные исключения
│       └── mcp/
│           ├── __init__.py
│           └── server.py    # MCP server для Claude
├── tests/
│   ├── test_workspace.py
│   ├── test_git_ops.py
│   └── fixtures/
│       └── workspace.yaml
└── .env.example
```

## Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Язык | Python | 3.10+ |
| CLI Framework | Click | >=8.1 |
| Git Operations | GitPython | >=3.1 |
| Data Validation | Pydantic | >=2.0 |
| Terminal Output | Rich | >=13.0 |
| HTTP Client | httpx | >=0.25 |
| Token Storage | keyring | >=24.0 |
| MCP Server | fastmcp (mcp) | >=1.0 |
| YAML Parsing | PyYAML | >=6.0 |

## Соглашения

### Именование
- Файлы: `snake_case.py`
- Классы: `PascalCase`
- Функции/переменные: `snake_case`
- Константы: `UPPER_SNAKE_CASE`

### Структура кода
- Модульная архитектура с чётким разделением ответственности
- CLI (cli.py) → Business Logic (workspace.py, git_ops.py) → Models (models.py)
- Все исключения наследуются от `GramaxSyncError`

## Зависимости

### Внешние
- **Click** — CLI framework, декларативное определение команд
- **GitPython** — Python-обёртка над Git, операции с репозиториями
- **Pydantic** — валидация данных, модели workspace.yaml
- **Rich** — красивый вывод в терминал, прогресс-бары
- **httpx** — HTTP-клиент для OAuth flow
- **keyring** — кроссплатформенное хранение токенов
- **fastmcp** — MCP server framework

### Внутренние зависимости
```
cli.py
├── config.py (загрузка конфигурации)
├── workspace.py (парсинг workspace.yaml)
├── git_ops.py (git операции)
└── auth.py (аутентификация)

workspace.py
└── models.py (Pydantic модели)

git_ops.py
├── models.py
└── exceptions.py

mcp/server.py
├── workspace.py
├── git_ops.py
└── config.py
```

## Модели данных

```python
class GitLabSource(BaseModel):
    type: str = "GitLab"
    url: str
    repos: list[str] = []

class Section(BaseModel):
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    catalogs: list[str] = []
    view: str = "section"

class Workspace(BaseModel):
    name: str
    source: GitLabSource
    sections: dict[str, Section]
```

## Иерархия исключений

```python
GramaxSyncError (base)
├── ConfigError        # Ошибка конфигурации
├── AuthError          # Ошибка аутентификации
├── GitError           # Ошибка Git операции
│   ├── CloneError
│   ├── PullError
│   ├── CommitError
│   └── PushError
└── WorkspaceError     # Ошибка workspace.yaml
```

## Ограничения окружения

- **macOS**: основная платформа, keyring через Keychain
- **Linux**: keyring требует `libsecret`
- **Windows**: keyring через Windows Credential Manager
- OAuth callback: localhost:8765 (проверять доступность порта)

## GitLab Source

- **Base URL:** `https://itsmf.gitlab.yandexcloud.net`
- **Repo pattern:** `/ritm-authors/{catalog_name}`
- **Default branch:** `private`
- **Auth:** GitLab Personal Access Token или OAuth

## Конфигурация

### Файл: `~/.config/gramax-sync/config.yaml`
```yaml
workspace_path: ~/Projects/ritm/workspace.yaml
workspace_dir: ~/Projects/ritm-repos
gitlab:
  base_url: https://itsmf.gitlab.yandexcloud.net
git:
  default_branch: private
  remote_name: origin
behavior:
  color_output: true
```

### Переменные окружения
```
GRAMAX_WORKSPACE_PATH
GRAMAX_WORKSPACE_DIR
GRAMAX_GITLAB_TOKEN (fallback)
```
