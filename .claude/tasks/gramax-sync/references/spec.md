# gramax-sync — CLI для управления репозиториями РИТМ

## Обзор проекта

Консольный инструмент для синхронизации и управления множеством Git-репозиториев, определённых в конфигурационном файле `workspace.yaml` проекта РИТМ (Gramax).

**Целевая платформа:** macOS (primary), Linux, Windows (secondary)
**Язык:** Python 3.10+
**Лицензия:** MIT

---

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

---

## Зависимости

```toml
[project]
dependencies = [
    "click>=8.1",           # CLI framework
    "pyyaml>=6.0",          # YAML parsing
    "gitpython>=3.1",       # Git operations
    "pydantic>=2.0",        # Data validation
    "rich>=13.0",           # Beautiful terminal output
    "httpx>=0.25",          # HTTP client for OAuth
    "keyring>=24.0",        # Secure token storage
    "mcp>=1.0",             # Model Context Protocol (fastmcp)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "ruff",
    "mypy",
]

[project.scripts]
gramax-sync = "gramax_sync.cli:main"
```

---

## Конфигурация

### Файл конфигурации: `~/.config/gramax-sync/config.yaml`

```yaml
# Путь к workspace.yaml (можно переопределить через --config)
workspace_path: ~/Projects/ritm/workspace.yaml

# Корневая директория для репозиториев
workspace_dir: ~/Projects/ritm-repos

# GitLab настройки
gitlab:
  base_url: https://itsmf.gitlab.yandexcloud.net
  # токен хранится в системном keyring, не в файле

# Git defaults
git:
  default_branch: private
  remote_name: origin

# Поведение
behavior:
  parallel_operations: false  # v2: параллельное клонирование
  color_output: true
```

### Переменные окружения (приоритет над файлом)

```bash
GRAMAX_WORKSPACE_PATH=/path/to/workspace.yaml
GRAMAX_WORKSPACE_DIR=/path/to/repos
GRAMAX_GITLAB_TOKEN=glpat-xxx  # fallback если keyring недоступен
```

---

## CLI Интерфейс

### Общий формат

```bash
gramax-sync [OPTIONS] COMMAND [ARGS]
```

### Глобальные опции

```
--config, -c PATH     Путь к workspace.yaml (переопределяет конфиг)
--dir, -d PATH        Корневая директория для репозиториев
--branch, -b TEXT     Ветка по умолчанию (default: private)
--verbose, -v         Подробный вывод
--quiet, -q           Минимальный вывод
--help                Справка
```

---

### Команды

#### `gramax-sync auth`

Аутентификация в GitLab.

```bash
gramax-sync auth login     # OAuth через браузер
gramax-sync auth status    # Проверить текущий токен
gramax-sync auth logout    # Удалить сохранённый токен
```

**Флоу авторизации:**
1. Открыть браузер на странице GitLab OAuth
2. Пользователь авторизуется
3. GitLab редиректит на localhost callback
4. Токен сохраняется в системный keyring

**Fallback:** если OAuth невозможен, запросить Personal Access Token интерактивно.

---

#### `gramax-sync clone`

Клонировать все репозитории из workspace.yaml.

```bash
gramax-sync clone                    # Все репозитории
gramax-sync clone --section 1-*      # Только секции по паттерну
gramax-sync clone --catalog 1-1-*    # Только каталоги по паттерну
```

**Опции:**
```
--section PATTERN    Фильтр секций (glob pattern)
--catalog PATTERN    Фильтр каталогов (glob pattern)
--force, -f          Перезаписать существующие (rm + clone)
```

**Логика:**
1. Загрузить workspace.yaml
2. Для каждой секции создать директорию
3. Для каждого каталога в секции:
   - Сформировать URL: `{source.url}/ritm-authors/{catalog}`
   - Клонировать в `{workspace_dir}/{section_key}/{catalog}/`
   - Checkout ветки `private` (или указанной)

**Вывод:**
```
📁 Creating workspace structure...
📂 1-ritm-strategiya-i-upravlenie-it/
  ✓ 1-1-razrabotka-strategii-it (cloned)
  ✓ 1-2-upravlenie-portfelyami-programmami (cloned)
  ✗ 1-3-praktika-planirovanie... (error: repository not found)
    └─ URL: https://itsmf.gitlab.yandexcloud.net/ritm-authors/1-3-praktika...
    └─ Error: Git returned 128

❌ Clone failed with 1 error(s). See above for details.
```

---

#### `gramax-sync pull`

Обновить репозитории (git pull).

```bash
gramax-sync pull                     # Все репозитории
gramax-sync pull --section 2-itam    # Конкретная секция
gramax-sync pull 1-1-razrabotka-strategii-it  # Конкретный каталог
```

**Опции:**
```
--section PATTERN    Фильтр секций
--rebase             Использовать rebase вместо merge
--stash              Автоматически stash/unstash при наличии изменений
```

**Вывод:**
```
🔄 Pulling updates...
📂 1-ritm-strategiya-i-upravlenie-it/
  ✓ 1-1-razrabotka-strategii-it (3 commits pulled)
  • 1-2-upravlenie-portfelyami (already up to date)
📂 2-itam/
  ✓ 2-0-foundation (1 commit pulled)

✅ Pull complete: 2 updated, 1 unchanged
```

---

#### `gramax-sync status`

Показать статус всех репозиториев.

```bash
gramax-sync status                   # Все
gramax-sync status --modified        # Только с изменениями
gramax-sync status --section 1-*     # Фильтр по секции
```

**Вывод:**
```
📊 Workspace Status

📂 1-ritm-strategiya-i-upravlenie-it/
  ✓ 1-1-razrabotka-strategii-it [private] clean
  ✎ 1-2-upravlenie-portfelyami [private] 2 modified, 1 untracked
    └─ M  docs/process.md
    └─ M  templates/form.docx
    └─ ?  notes.txt

📂 2-itam/
  ↑ 2-0-foundation [private] 1 ahead, 0 behind
  ✗ 2-1-asset-strategy [ERROR: not a git repo]

Summary: 4 repos, 1 modified, 1 ahead, 1 error
```

---

#### `gramax-sync commit`

Закоммитить изменения.

```bash
gramax-sync commit                              # Все с изменениями, автосообщение
gramax-sync commit -m "Update documentation"   # Все с изменениями, своё сообщение
gramax-sync commit 1-1-razrabotka-strategii-it -m "Fix typo"  # Конкретный
gramax-sync commit --section 2-*               # По секции
```

**Опции:**
```
--message, -m TEXT    Сообщение коммита (иначе автогенерация)
--section PATTERN     Фильтр секций
--add-all, -a         git add . перед коммитом (default: true)
--no-add              Не добавлять файлы автоматически
```

**Автогенерация сообщения:**
```
[gramax-sync] Update by {username} at {ISO datetime}

Modified files:
- docs/process.md
- templates/form.docx

Added files:
- notes.txt
```

**Вывод:**
```
📝 Committing changes...
📂 1-ritm-strategiya-i-upravlenie-it/
  ✓ 1-2-upravlenie-portfelyami (committed: 3 files)
    └─ Commit: abc1234

📂 2-itam/
  • 2-0-foundation (no changes)

✅ Committed 1 repository
```

---

#### `gramax-sync push`

Отправить изменения в remote.

```bash
gramax-sync push                     # Все с unpushed commits
gramax-sync push --section 1-*       # По секции
gramax-sync push 1-1-razrabotka-strategii-it  # Конкретный
gramax-sync push --force             # Force push (осторожно!)
```

**Опции:**
```
--section PATTERN    Фильтр секций
--force, -f          Force push
--set-upstream       Установить upstream для новых веток
```

**Вывод:**
```
🚀 Pushing changes...
📂 1-ritm-strategiya-i-upravlenie-it/
  ✓ 1-2-upravlenie-portfelyami → origin/private (1 commit)

✅ Pushed 1 repository
```

---

#### `gramax-sync sync`

Комбинированная команда: pull + commit + push.

```bash
gramax-sync sync                     # Полная синхронизация всех
gramax-sync sync --section 1-*       # По секции
gramax-sync sync --pull-only         # Только pull без push
```

---

### Примеры сценариев

```bash
# Первоначальная настройка
gramax-sync auth login
gramax-sync clone --config ~/Downloads/workspace.yaml --dir ~/Projects/ritm

# Ежедневная работа
gramax-sync pull                     # Получить обновления
# ... редактирование файлов ...
gramax-sync status                   # Проверить что изменилось
gramax-sync commit -m "Добавил описание процесса"
gramax-sync push

# Быстрая синхронизация
gramax-sync sync --section 1-*
```

---

## Модели данных (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional

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
    
    def get_catalog_url(self, catalog: str) -> str:
        """Формирует URL репозитория для каталога."""
        return f"{self.source.url}/ritm-authors/{catalog}"
    
    def iter_catalogs(self) -> Iterator[tuple[str, str, str]]:
        """Итерирует (section_key, catalog, url)."""
        for section_key, section in self.sections.items():
            for catalog in section.catalogs:
                yield section_key, catalog, self.get_catalog_url(catalog)
```

---

## Обработка ошибок

### Иерархия исключений

```python
class GramaxSyncError(Exception):
    """Базовое исключение."""
    pass

class ConfigError(GramaxSyncError):
    """Ошибка конфигурации."""
    pass

class AuthError(GramaxSyncError):
    """Ошибка аутентификации."""
    pass

class GitError(GramaxSyncError):
    """Ошибка Git операции."""
    def __init__(self, message: str, repo_path: str, git_output: str):
        self.repo_path = repo_path
        self.git_output = git_output
        super().__init__(message)

class WorkspaceError(GramaxSyncError):
    """Ошибка workspace.yaml."""
    pass
```

### Поведение при ошибках

**Стратегия: fail-fast с подробной диагностикой.**

```python
# При ошибке в любом репозитории:
1. Немедленно остановить выполнение
2. Вывести полную информацию об ошибке:
   - Какой репозиторий
   - Какая операция
   - Полный вывод git
   - Возможные причины и решения
3. Вернуть exit code != 0
```

**Пример вывода ошибки:**

```
❌ ERROR: Git operation failed

Repository: 1-1-razrabotka-strategii-it
Operation:  git pull origin private
Location:   /Users/max/ritm-repos/1-ritm.../1-1-razrabotka.../

Git output:
  error: Your local changes to the following files would be overwritten by merge:
    docs/process.md
  Please commit your changes or stash them before you merge.

Possible solutions:
  1. Commit your changes:  gramax-sync commit 1-1-razrabotka-strategii-it
  2. Stash changes:        cd /Users/max/ritm-repos/... && git stash
  3. Discard changes:      cd /Users/max/ritm-repos/... && git checkout -- .
  4. Use --stash flag:     gramax-sync pull --stash
```

---

## MCP Server для Claude

### Конфигурация MCP

```json
{
  "mcpServers": {
    "gramax-sync": {
      "command": "python",
      "args": ["-m", "gramax_sync.mcp"],
      "env": {
        "GRAMAX_WORKSPACE_PATH": "/path/to/workspace.yaml",
        "GRAMAX_WORKSPACE_DIR": "/path/to/repos"
      }
    }
  }
}
```

### MCP Tools

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gramax-sync")

@mcp.tool()
def list_sections() -> str:
    """Показать все секции и каталоги из workspace.yaml."""
    ...

@mcp.tool()
def repo_status(section: str = None, catalog: str = None) -> str:
    """Показать git статус репозиториев.
    
    Args:
        section: Фильтр по секции (опционально)
        catalog: Конкретный каталог (опционально)
    """
    ...

@mcp.tool()
def pull_repos(section: str = None, catalog: str = None) -> str:
    """Обновить репозитории (git pull).
    
    Args:
        section: Фильтр по секции (опционально)  
        catalog: Конкретный каталог (опционально)
    """
    ...

@mcp.tool()
def commit_changes(
    message: str = None,
    section: str = None,
    catalog: str = None
) -> str:
    """Закоммитить изменения в репозиториях.
    
    Args:
        message: Сообщение коммита (автогенерация если не указано)
        section: Фильтр по секции (опционально)
        catalog: Конкретный каталог (опционально)
    """
    ...

@mcp.tool()
def push_changes(section: str = None, catalog: str = None) -> str:
    """Отправить изменения в remote (git push).
    
    Args:
        section: Фильтр по секции (опционально)
        catalog: Конкретный каталог (опционально)
    """
    ...

@mcp.tool()
def sync_all(section: str = None, message: str = None) -> str:
    """Полная синхронизация: pull → commit → push.
    
    Args:
        section: Фильтр по секции (опционально)
        message: Сообщение коммита (опционально)
    """
    ...

@mcp.tool()
def clone_repos(section: str = None) -> str:
    """Клонировать репозитории из workspace.yaml.
    
    Args:
        section: Фильтр по секции (опционально)
    """
    ...
```

---

## Тесты

### Unit Tests

```python
# tests/test_workspace.py
def test_parse_workspace():
    """Парсинг workspace.yaml."""
    
def test_catalog_url_generation():
    """Формирование URL репозитория."""
    
def test_iterate_catalogs():
    """Итерация по всем каталогам."""

# tests/test_git_ops.py
def test_clone_repository(tmp_path, mock_git):
    """Клонирование репозитория."""

def test_pull_with_changes(tmp_path, mock_git):
    """Pull с локальными изменениями."""

def test_commit_auto_message():
    """Автогенерация сообщения коммита."""

# tests/test_auth.py
def test_token_storage():
    """Сохранение и загрузка токена."""

def test_oauth_flow(mock_browser):
    """OAuth flow через браузер."""
```

---

## Чеклист реализации

### Phase 1: Core (MVP)
- [ ] Структура проекта и зависимости
- [ ] Парсинг workspace.yaml (models.py, workspace.py)
- [ ] Базовые Git операции (git_ops.py)
- [ ] CLI каркас (cli.py)
- [ ] Команда `clone`
- [ ] Команда `status`
- [ ] Команда `pull`

### Phase 2: Full CLI
- [ ] Команда `commit` с автогенерацией сообщений
- [ ] Команда `push`
- [ ] Команда `sync`
- [ ] Фильтрация по section/catalog
- [ ] Красивый вывод через Rich

### Phase 3: Auth & Config
- [ ] Конфигурационный файл
- [ ] OAuth flow через браузер
- [ ] Fallback на PAT
- [ ] Keyring интеграция

### Phase 4: MCP
- [ ] MCP server setup
- [ ] Все tools
- [ ] Тестирование с Claude

### Phase 5: Polish
- [ ] Полное покрытие тестами
- [ ] Документация (README)
- [ ] CI/CD (GitHub Actions)
- [ ] Публикация в PyPI

---

## Примечания для разработчика

1. **GitPython vs subprocess**: Используй GitPython для операций, но будь готов к fallback на subprocess для edge cases.

2. **OAuth flow**: Используй `http.server` для localhost callback. Порт 8765 по умолчанию, но проверяй доступность.

3. **Keyring**: На macOS работает через Keychain. На Linux может потребовать `libsecret`. Предусмотри fallback на файл (зашифрованный).

4. **Rich**: Используй `rich.console.Console` для всего вывода. `rich.progress` для длительных операций.

5. **Click**: Используй `@click.group()` для команд. `@click.pass_context` для передачи конфига.

6. **Тестирование Git**: Используй `pytest-git` или создавай временные bare repos в `tmp_path`.
