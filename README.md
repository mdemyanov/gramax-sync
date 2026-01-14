# gramax-sync

CLI инструмент для синхронизации и управления множеством Git-репозиториев проекта РИТМ (Gramax).

## Описание

**gramax-sync** — консольный инструмент для работы с множеством Git-репозиториев, определённых в конфигурационном файле `workspace.yaml`. Инструмент позволяет выполнять массовые операции clone, pull, commit, push для всех репозиториев проекта.

## Требования

- **Python:** 3.10 или выше
- **Git:** установленный и настроенный
- **macOS/Linux/Windows:** поддерживаются все платформы

### Проверка требований

```bash
# Проверка версии Python
python3 --version  # Должно быть 3.10+

# Проверка Git
git --version
```

## Установка

### Установка из PyPI (рекомендуется)

[uv](https://github.com/astral-sh/uv) — современный, быстрый менеджер пакетов Python.

#### Шаг 1: Установка uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Или через Homebrew (macOS)
brew install uv

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

После установки перезапустите терминал или выполните:
```bash
source ~/.bashrc  # или ~/.zshrc для zsh
```

#### Шаг 2: Установка gramax-sync

```bash
# Установить из PyPI
uv pip install gramax-sync
```

#### Шаг 3: Проверка установки

```bash
# Проверить, что команда доступна
uv run gramax-sync --version

# Проверить справку
uv run gramax-sync --help
```

### Установка для разработки

Для разработки клонируйте репозиторий и установите в editable режиме:

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/gramax-sync.git
cd gramax-sync

# Автоматическая настройка (рекомендуется)
make setup

# Или вручную через uv:
uv venv
uv pip install -e ".[dev]"
pre-commit install
```

Подробнее см. [DEVELOPMENT.md](DEVELOPMENT.md)

### Устранение проблем установки

#### Команда не найдена после установки

```bash
# Проверьте, что пакет установлен
uv pip list | grep gramax-sync

# Переустановите если нужно
uv pip install -e .

# Проверьте работу через uv run
uv run gramax-sync --version
```

#### Ошибка "Python version not supported"

```bash
# Проверьте версию Python
python3 --version

# Если версия < 3.10, установите новую версию:
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11
```

#### Проблемы с keyring на Linux

```bash
# Установите необходимые библиотеки
sudo apt install libsecret-1-dev  # Ubuntu/Debian
sudo dnf install libsecret-devel  # Fedora
```

## Использование

> **Примечание:** Все команды в документации используют `uv run` для автоматического
> запуска в виртуальном окружении без необходимости его активации.

### Первоначальная настройка

Перед использованием необходимо выполнить первоначальную настройку:

```bash
# Интерактивная настройка
uv run gramax-sync init

# Или с параметрами
uv run gramax-sync init \
  --repo-url https://itsmf.gitlab.yandexcloud.net/ritm-authors/gramax-yaml-manager \
  --branch master \
  --catalog-branch private
```

Команда `init` выполняет:
1. Подключение к репозиторию с конфигурациями
2. Проверку доступа и наличия `workspace.yaml`
3. Авторизацию в GitLab при необходимости
4. Загрузку и отображение структуры секций и каталогов
5. Интерактивный выбор секций/каталогов для работы

**Важно:** Для репозитория конфигураций используется ветка `master` (по умолчанию), а для каталогов (репозиториев с кодом) — ветка `private`.

### Работа с репозиториями

```bash
# Клонирование всех репозиториев
uv run gramax-sync clone

# Статус всех репозиториев
uv run gramax-sync status

# Обновление всех репозиториев
uv run gramax-sync pull

# Коммит изменений (с автогенерацией сообщения)
uv run gramax-sync commit

# Коммит с кастомным сообщением
uv run gramax-sync commit -m "Update documentation"

# Отправка изменений
uv run gramax-sync push

# Полная синхронизация (pull + commit + push)
uv run gramax-sync sync

# Синхронизация с предварительным просмотром
uv run gramax-sync sync --dry-run
```

### Фильтрация по секциям и каталогам

Все команды поддерживают glob-паттерны для фильтрации:

```bash
# Работа только с секциями, начинающимися на "1-"
uv run gramax-sync status --section "1-*"
uv run gramax-sync clone --section "1-методология"

# Работа только с определёнными каталогами
uv run gramax-sync commit --catalog "ritm-*" -m "Fix typos"

# Комбинация фильтров
uv run gramax-sync pull --section "1-*" --catalog "ritm-methodology"
```

### Управление конфигурацией

```bash
# Просмотр текущей конфигурации
uv run gramax-sync edit show

# Изменение директории для репозиториев
uv run gramax-sync edit set-workspace-dir --workspace-dir ~/my-workspace
# или интерактивно
uv run gramax-sync edit set-workspace-dir

# Добавление секции или каталога
uv run gramax-sync edit add --section "1-методология" --catalog "ritm-methodology"
# или интерактивно
uv run gramax-sync edit add

# Удаление секции или каталога
uv run gramax-sync edit remove --section "1-методология" --catalog "ritm-methodology"

# Обновление конфигурации с сервера
uv run gramax-sync update
```

### Аутентификация

**📖 Подробная информация о правах токена:** [TOKEN_PERMISSIONS.md](TOKEN_PERMISSIONS.md)

#### OAuth (рекомендуется)

**⚠️ Перед использованием OAuth необходимо создать OAuth Application в GitLab!**

1. **Создайте OAuth Application:**
   - Откройте: https://itsmf.gitlab.yandexcloud.net/-/profile/applications
   - Нажмите "Add new application"
   - Name: `gramax-sync`
   - Redirect URI: `http://localhost:8765/callback`
   - Scopes: `read_api`, `read_repository`, `read_user`
   - Скопируйте Application ID

2. **Установите Application ID:**
   ```bash
   export GRAMAX_OAUTH_APPLICATION_ID="ваш_application_id"
   ```
   Или используйте автоматическую настройку: `./scripts/setup_oauth.sh`

3. **Выполните аутентификацию:**
   ```bash
   uv run gramax-sync auth login --oauth --url https://itsmf.gitlab.yandexcloud.net
   ```

Подробная инструкция: [OAUTH_SETUP.md](OAUTH_SETUP.md)

#### Personal Access Token (альтернатива)

**Необходимые права токена:**
- `read_api` - чтение данных через API
- `read_repository` - чтение содержимого репозиториев
- `read_user` - получение информации о пользователе

```bash
# Войти через Personal Access Token
uv run gramax-sync auth login --pat --url https://itsmf.gitlab.yandexcloud.net
```

**💡 Подробнее:** См. [TOKEN_PERMISSIONS.md](TOKEN_PERMISSIONS.md) для полной информации о настройке прав токена.

#### Управление аутентификацией

```bash
# Показать статус аутентификации
uv run gramax-sync auth status

# Обновить токен
uv run gramax-sync auth refresh

# Выйти из системы
uv run gramax-sync auth logout --url https://itsmf.gitlab.yandexcloud.net
```

## Конфигурация

Конфигурация хранится в `~/.config/gramax-sync/config.yaml` и создаётся автоматически при выполнении команды `init`.

Репозиторий с конфигурациями должен содержать файл `workspace.yaml`:

```yaml
workspace_dir: ~/ritm-workspace

sections:
  - name: "1-методология"
    catalogs:
      - name: "ritm-methodology"
        source:
          url: "https://gitlab.example.com"
```

**Ветки:**
- Репозиторий конфигураций: ветка `master` (по умолчанию)
- Каталоги (репозитории с кодом): ветка `private` (по умолчанию)

**Директория для репозиториев:**
- По умолчанию: `~/{name}-workspace` (где `name` — имя проекта из workspace.yaml)
- Можно изменить: `uv run gramax-sync edit set-workspace-dir`
- Структура: `{workspace_dir}/{section}/{catalog}/`

## Разработка

### Быстрый старт

```bash
# Настроить окружение
make setup

# Запустить тесты
make test

# Проверить код
make check

# Отформатировать код
make format
```

### Полезные команды

```bash
make help          # Показать все команды
make test          # Запустить тесты
make test-cov      # Тесты с покрытием
make lint          # Проверить линтерами
make format        # Отформатировать код
make type-check    # Проверить типы
make check         # Проверить всё
make clean         # Очистить временные файлы
```

## Документация

- [DEVELOPMENT.md](DEVELOPMENT.md) — Руководство по разработке
- [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) — Принципы архитектуры
- [ROADMAP.md](ROADMAP.md) — Дорожная карта развития
- [OAUTH_SETUP.md](OAUTH_SETUP.md) — Настройка OAuth
- [MCP_SETUP.md](MCP_SETUP.md) — MCP Server для Claude Desktop
- [TOKEN_PERMISSIONS.md](TOKEN_PERMISSIONS.md) — Права токенов GitLab
- [CLAUDE.md](CLAUDE.md) — Контекст для Claude Code

## MCP Server для Claude Desktop

**gramax-sync** включает MCP Server для интеграции с Claude Desktop.

**Доступные инструменты:**
- `list_repositories` — список секций и каталогов
- `get_repository_status` — статус репозиториев
- `clone_repositories` — клонирование
- `pull_repositories` — обновление
- `commit_changes` — коммит изменений
- `push_changes` — отправка изменений
- `sync_repositories` — полная синхронизация

Подробнее см. [MCP_SETUP.md](MCP_SETUP.md)

## Лицензия

MIT
