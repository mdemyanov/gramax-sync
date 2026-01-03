# gramax-sync

CLI инструмент для синхронизации и управления множеством Git-репозиториев проекта РИТМ (Gramax).

## Описание

**gramax-sync** — консольный инструмент для работы с множеством Git-репозиториев, определённых в конфигурационном файле `workspace.yaml`. Инструмент позволяет выполнять массовые операции clone, pull, commit, push для всех репозиториев проекта.

## Установка

### Для использования

```bash
# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# или .venv\Scripts\activate  # Windows

# Установить проект
pip install -e .
```

### Для разработки

```bash
# Автоматическая настройка (рекомендуется)
make setup

# Или вручную:
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
pre-commit install
```

Подробнее см. [DEVELOPMENT.md](DEVELOPMENT.md)

## Использование

### Первоначальная настройка

Перед использованием необходимо выполнить первоначальную настройку:

```bash
# Интерактивная настройка
gramax-sync init

# Или с параметрами
gramax-sync init \
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

### Управление конфигурацией

```bash
# Просмотр текущей конфигурации
gramax-sync edit show

# Изменение директории для репозиториев
gramax-sync edit set-workspace-dir --workspace-dir ~/my-workspace
# или интерактивно
gramax-sync edit set-workspace-dir

# Добавление секции или каталога
gramax-sync edit add --section "1-методология" --catalog "ritm-methodology"
# или интерактивно
gramax-sync edit add

# Удаление секции или каталога
gramax-sync edit remove --section "1-методология" --catalog "ritm-methodology"

# Обновление конфигурации с сервера
gramax-sync update
```

### Работа с репозиториями

```bash
# Клонирование всех репозиториев
gramax-sync clone

# Статус всех репозиториев
gramax-sync status

# Обновление всех репозиториев
gramax-sync pull

# Коммит изменений (с автогенерацией сообщения)
gramax-sync commit

# Коммит с кастомным сообщением
gramax-sync commit -m "Update documentation"

# Коммит с фильтрацией
gramax-sync commit --section "1-*" -m "Fix typos"
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
   gramax-sync auth login --oauth --url https://itsmf.gitlab.yandexcloud.net
   ```

Подробная инструкция: [OAUTH_SETUP.md](OAUTH_SETUP.md)

#### Personal Access Token (альтернатива)

**Необходимые права токена:**
- `read_api` - чтение данных через API
- `read_repository` - чтение содержимого репозиториев
- `read_user` - получение информации о пользователе

```bash
# Войти через Personal Access Token
gramax-sync auth login --pat --url https://itsmf.gitlab.yandexcloud.net
```

**💡 Подробнее:** См. [TOKEN_PERMISSIONS.md](TOKEN_PERMISSIONS.md) для полной информации о настройке прав токена.

#### Управление аутентификацией

```bash
# Показать статус аутентификации
gramax-sync auth status

# Обновить токен
gramax-sync auth refresh

# Выйти из системы
gramax-sync auth logout --url https://itsmf.gitlab.yandexcloud.net
```

## Конфигурация

Конфигурация хранится в `~/.config/gramax-sync/config.yaml` (ранее использовался JSON формат, автоматически мигрируется) и создаётся автоматически при выполнении команды `init`.

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
- Можно изменить: `gramax-sync edit set-workspace-dir`
- Структура: `{workspace_dir}/{section}/{catalog}/`

## Разработка

### Быстрый старт

```bash
# Настроить окружение
make setup
source .venv/bin/activate

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

**Документация для разработчиков:**
- [DEVELOPMENT.md](DEVELOPMENT.md) — Руководство по разработке
- [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) — Универсальные правила архитектуры и принципы разработки

## Статус разработки

✅ **Проект готов к использованию!** — Все основные команды реализованы и протестированы

### Последние обновления (v0.1.0)

- ✅ **Адаптация модели данных** под реальную структуру workspace.yaml (словарь sections, поддержка null значений)
- ✅ **Автоматическая аутентификация** при клонировании репозиториев (токен добавляется в URL)
- ✅ **Исправление пагинации** при получении дерева репозиториев (получение всех элементов)
- ✅ **Команда изменения workspace_dir**: `gramax-sync edit set-workspace-dir`
- ✅ **Улучшенная обработка ошибок** GitLab API (fallback на прямые HTTP запросы)
- ✅ **Правильная передача URL** в python-gitlab (базовый URL + путь проекта)
- ✅ **Обновление токена** в GitLabClient после сохранения

### Этап 1.1: Настройка проекта и инфраструктуры ✅ ЗАВЕРШЁН

### Этап 1.1: Настройка проекта и инфраструктуры ✅ ЗАВЕРШЁН

- [x] Структура проекта и модули
- [x] Конфигурация проекта (pyproject.toml)
- [x] Виртуальное окружение и зависимости
- [x] Инструменты разработки (black, ruff, mypy)
- [x] Pre-commit hooks
- [x] Тесты инфраструктуры (16 тестов, 100% покрытие)
- [x] Документация по разработке

### Этап 1.2: Customer Map и первоначальная настройка ✅ ЗАВЕРШЁН

- [x] Документ Customer Map с описанием пользовательского пути
- [x] Модуль для работы с GitLab API (проверка доступа, получение файлов)
- [x] Парсер workspace.yaml (из файла и из строки)
- [x] Модуль аутентификации (управление токенами через keyring)
- [x] Интерактивный выбор секций/каталогов
- [x] Команда `init` для первоначальной настройки
- [x] Поддержка разных веток (main для конфигов, private для каталогов)
- [x] Команда `edit` для редактирования локальной конфигурации
- [x] Команда `update` для обновления конфигурации с сервера
- [x] Управление локальной конфигурацией (LocalConfig, ConfigManager)
- [x] Миграция конфигурации с JSON на YAML формат

### Этап 1.3: Команды работы с репозиториями ✅ ЗАВЕРШЁН

- [x] Команда `clone` — клонирование репозиториев
- [x] Команда `status` — статус репозиториев
- [x] Команда `pull` — обновление репозиториев

### Этап 2.1: Команда commit ✅ ЗАВЕРШЁН

- [x] Команда `commit` — массовый commit изменений
- [x] Автогенерация сообщений коммитов
- [x] Поддержка кастомных сообщений через `-m`
- [x] Фильтрация по `--section` и `--catalog`

### Этап 2.2: Команда push ✅ ЗАВЕРШЁН

- [x] Команда `push` — отправка изменений в remote
- [x] Поддержка force push с подтверждением
- [x] Установка upstream для новых веток
- [x] Фильтрация по `--section` и `--catalog`

### Этап 2.3: Команда sync ✅ ЗАВЕРШЁН

- [x] Команда `sync` — полная синхронизация (pull + commit + push)
- [x] Dry-run режим для предварительного просмотра
- [x] Условная логика (операции только при необходимости)
- [x] Фильтрация по `--section` и `--catalog`

### Этап 3.1: OAuth аутентификация ✅ ЗАВЕРШЁН

- [x] OAuth аутентификация через браузер
- [x] Команда `auth login` (OAuth и PAT)
- [x] Команда `auth status` — статус аутентификации
- [x] Команда `auth logout` — выход из системы
- [x] Команда `auth refresh` — обновление токена
- [x] Проверка валидности токенов

### Этап 3.3: Расширенная конфигурация

- [ ] Расширение LocalConfig новыми полями
- [ ] Команда `config` для управления конфигурацией
- [ ] Поддержка переменных окружения

### Этап 4: MCP Server для Claude Desktop ✅ ЗАВЕРШЁН

- [x] Базовая структура MCP сервера на базе fastmcp
- [x] 7 MCP инструментов для работы с репозиториями
- [x] Интеграция с существующим кодом
- [x] Документация по настройке

**Доступные MCP инструменты:**
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

